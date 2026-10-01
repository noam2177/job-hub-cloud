from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

from jobs_pipeline.bq_exporter import DEFAULT_TABLE, Exporter
from jobs_pipeline.events import derive_events, load_jobs, load_outcomes

DEFAULT_PROJECT_ID = "noam-job-hub-123"


class QueryClient(Protocol):
    def query(self, sql: str, job_config: Any = None) -> Any: ...


def default_ledger_path() -> Path:
    explicit = os.environ.get("JOBHUB_LEDGER_JOBS")
    if explicit:
        return Path(explicit)
    bus = os.environ.get("CAREER_DRIVE_BUS_DIR")
    if bus:
        return Path(bus) / "ledger" / "jobs.json"
    legacy = Path(r"G:\האחסון שלי\Job_serch_Spark\ledger\jobs.json")
    if legacy.is_file():
        return legacy
    return Path("ledger") / "jobs.json"


def event_fingerprint(event: dict[str, Any]) -> str:
    payload = {
        "event_id": event.get("event_id"),
        "job_id": event.get("job_id"),
        "event_type": event.get("event_type"),
        "ts": event.get("ts"),
        "cv_version": event.get("cv_version"),
        "title_family": event.get("title_family"),
        "keywords": event.get("keywords"),
        "source_type": event.get("source_type"),
        "payload": event.get("payload"),
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _table_ref(project_id: str, table: str = DEFAULT_TABLE) -> str:
    if table.startswith(f"{project_id}."):
        return table
    if "." in table:
        return f"{project_id}.{table}"
    return f"{project_id}.{table}"


def _dedup_view_ref(project_id: str, table: str = DEFAULT_TABLE) -> str:
    base = _table_ref(project_id, table)
    if base.endswith("_dedup"):
        return base
    if base.endswith(".events"):
        return f"{base}_dedup"
    return f"{base}_dedup"


def fetch_existing_event_ids(client: QueryClient, project_id: str, table: str = DEFAULT_TABLE) -> set[str]:
    dest = _table_ref(project_id, table)
    sql = f"SELECT DISTINCT event_id FROM `{dest}` WHERE event_id IS NOT NULL"
    return {str(row.event_id) for row in client.query(sql).result() if row.event_id}


def fetch_existing_job_event_types(
    client: QueryClient, project_id: str, table: str = DEFAULT_TABLE
) -> set[tuple[str, str]]:
    """Fallback dedupe when legacy loads used non-canonical event_id strings."""
    dest = _table_ref(project_id, table)
    view = _dedup_view_ref(project_id, table)
    sql_variants = (
        f"""
        SELECT DISTINCT job_id, event_type
        FROM `{view}`
        WHERE job_id IS NOT NULL AND event_type IS NOT NULL
        """,
        f"""
        SELECT DISTINCT job_id, event_type
        FROM `{dest}`
        WHERE job_id IS NOT NULL AND event_type IS NOT NULL
        """,
    )
    last_exc: Exception | None = None
    for sql in sql_variants:
        try:
            out: set[tuple[str, str]] = set()
            for row in client.query(sql).result():
                if row.job_id and row.event_type:
                    out.add((str(row.job_id), str(row.event_type)))
            return out
        except Exception as exc:
            last_exc = exc
    # Legacy flat loads (company/title/status) — treat each job_id as an implicit "found" row.
    legacy_sql = f"SELECT DISTINCT job_id FROM `{dest}` WHERE job_id IS NOT NULL"
    try:
        out = set()
        for row in client.query(legacy_sql).result():
            if row.job_id:
                out.add((str(row.job_id), "found"))
        return out
    except Exception as exc:
        last_exc = exc
    raise last_exc or RuntimeError("could not read job_id/event_type from BigQuery")


def event_logical_key(event: dict[str, Any]) -> tuple[str, str]:
    return (str(event.get("job_id") or ""), str(event.get("event_type") or ""))


def _row_to_event(row: Any) -> dict[str, Any]:
    payload = row.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    elif payload is None:
        payload = {}
    keywords = list(row.keywords) if getattr(row, "keywords", None) is not None else []
    ts = row.ts
    if ts is not None and hasattr(ts, "isoformat"):
        ts = ts.isoformat().replace("+00:00", "Z")
    return {
        "event_id": row.event_id,
        "job_id": row.job_id,
        "event_type": row.event_type,
        "ts": ts,
        "cv_version": row.cv_version,
        "title_family": row.title_family,
        "keywords": keywords,
        "source_type": row.source_type,
        "payload": payload if isinstance(payload, dict) else {},
        "exported_at": None,
    }


def fetch_bq_fingerprints(
    client: QueryClient,
    project_id: str,
    event_ids: set[str],
    *,
    table: str = DEFAULT_TABLE,
) -> dict[str, str]:
    if not event_ids:
        return {}
    view = _dedup_view_ref(project_id, table)
    from google.cloud import bigquery

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", sorted(event_ids))]
    )
    sql = f"""
        SELECT event_id, job_id, event_type, ts, cv_version, title_family, keywords, source_type, payload
        FROM `{view}`
        WHERE event_id IN UNNEST(@ids)
    """
    out: dict[str, str] = {}
    for row in client.query(sql, job_config=job_config).result():
        if not row.event_id:
            continue
        out[str(row.event_id)] = event_fingerprint(_row_to_event(row))
    return out


def select_events_to_append(
    derived: list[dict[str, Any]],
    *,
    bq_event_ids: set[str],
    bq_fingerprints: dict[str, str],
    local_fingerprints: dict[str, str],
    bq_job_event_types: set[tuple[str, str]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    to_append: list[dict[str, Any]] = []
    stats = {
        "derived_total": len(derived),
        "already_in_bq": 0,
        "unchanged": 0,
        "new": 0,
        "updated": 0,
        "skipped_logical_duplicate": 0,
    }
    local = dict(local_fingerprints)
    logical = bq_job_event_types or set()
    for event in derived:
        eid = str(event.get("event_id") or "")
        if not eid:
            continue
        fp = event_fingerprint(event)
        log_key = event_logical_key(event)
        if eid not in bq_event_ids and log_key in logical and log_key[0]:
            stats["skipped_logical_duplicate"] += 1
            local[eid] = fp
            continue
        in_bq = eid in bq_event_ids
        bq_fp = bq_fingerprints.get(eid)
        local_fp = local.get(eid)
        if not in_bq:
            stats["new"] += 1
            to_append.append(event)
            local[eid] = fp
            continue
        if bq_fp is not None:
            if bq_fp == fp:
                stats["unchanged"] += 1
            else:
                stats["updated"] += 1
                to_append.append(event)
            local[eid] = fp
            continue
        if local_fp == fp:
            stats["already_in_bq"] += 1
            local[eid] = fp
            continue
        if local_fp is not None and local_fp != fp:
            stats["updated"] += 1
            to_append.append(event)
            local[eid] = fp
            continue
        stats["already_in_bq"] += 1
        local[eid] = fp
    return to_append, {"stats": stats, "fingerprints": local}


def run_incremental_sync(
    jobs_path: Path,
    state: dict[str, Any],
    *,
    outcomes_path: Path | None,
    project_id: str,
    table: str = DEFAULT_TABLE,
    client: QueryClient | None,
    apply: bool,
    preview_bq: bool = False,
) -> dict[str, Any]:
    from jobs_pipeline.backfill import build_report, refuse_foreign_ledger

    refuse_foreign_ledger(jobs_path)
    jobs = load_jobs(jobs_path)
    outcomes = load_outcomes(outcomes_path) if outcomes_path else []
    events, new_state = derive_events(jobs, outcomes, state)
    report = build_report(jobs, events)
    report["event_count"] = len(events)
    report["project_id"] = project_id
    report["table"] = _table_ref(project_id, table)

    local_fps: dict[str, str] = {}
    raw_fps = state.get("exported_fingerprints")
    if isinstance(raw_fps, dict):
        local_fps = {str(k): str(v) for k, v in raw_fps.items()}

    bq_ids: set[str] = set()
    bq_fps: dict[str, str] = {}
    bq_logical: set[tuple[str, str]] = set()
    catalog_client = client if (apply or preview_bq) else None
    if catalog_client is not None:
        bq_ids = fetch_existing_event_ids(catalog_client, project_id, table)
        bq_logical = fetch_existing_job_event_types(catalog_client, project_id, table)
        report["bq_distinct_event_ids"] = len(bq_ids)
        report["bq_distinct_job_event_types"] = len(bq_logical)
        if bq_logical and all(et == "found" for _, et in bq_logical) and len(bq_logical) == len(bq_ids):
            report["bq_schema_note"] = (
                "legacy_or_found_only: apply canonical events only after ddl_events.sql schema is active"
            )
        if apply:
            overlap = {str(e.get("event_id")) for e in events if e.get("event_id")} & bq_ids
            bq_fps = fetch_bq_fingerprints(catalog_client, project_id, overlap, table=table)
    elif apply:
        raise RuntimeError("BigQuery client is required for --apply")

    to_append, selection = select_events_to_append(
        events,
        bq_event_ids=bq_ids,
        bq_fingerprints=bq_fps,
        local_fingerprints=local_fps,
        bq_job_event_types=bq_logical if catalog_client else None,
    )
    report["incremental"] = selection["stats"]
    report["rows_to_append"] = len(to_append)

    if not apply:
        report["dry_run"] = True
        return report

    exporter = Exporter(client=client, project_id=project_id, table=table)
    load_report = exporter.export(to_append, dry_run=False)
    new_state["exported_fingerprints"] = selection["fingerprints"]
    report["export"] = load_report
    report["dry_run"] = False
    report["_state"] = new_state
    return report
