#!/usr/bin/env python3
"""Read-only BigQuery data-quality probes (minimal query cost). Legacy-schema aware."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobs_pipeline.incremental_sync import DEFAULT_PROJECT_ID, _table_ref


def _run(client: Any, sql: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in client.query(sql).result():
        rows.append(dict(row.items()))
    return rows


def _table_columns(client: Any, project_id: str, table: str) -> set[str]:
    dest = _table_ref(project_id, table)
    parts = dest.split(".")
    dataset = parts[1] if len(parts) >= 3 else "jobs"
    tbl = parts[2] if len(parts) >= 3 else "events"
    sql = f"""
        SELECT column_name
        FROM `{project_id}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{tbl}'
    """
    return {str(r["column_name"]) for r in _run(client, sql)}


def build_checks(project_id: str, columns: set[str]) -> list[dict[str, Any]]:
    dest = _table_ref(project_id, "jobs.events")
    checks: list[dict[str, Any]] = []

    dup_sql = f"""
        SELECT COUNT(*) AS total, COUNT(DISTINCT event_id) AS distinct_ids
        FROM `{dest}`
    """
    checks.append({"id": "duplicate_event_id", "sql": dup_sql, "kind": "dup"})

    if "event_type" in columns:
        checks.append(
            {
                "id": "unknown_event_type_count",
                "sql": f"""
                    SELECT COUNTIF(event_type NOT IN (
                      'found','draft_created','applied','reply','interview',
                      'reject','offer','withdrawn','closed'
                    )) AS bad
                    FROM `{dest}`
                """,
                "kind": "threshold",
                "threshold": 0,
            }
        )
    else:
        checks.append(
            {
                "id": "schema_legacy",
                "status": "warn",
                "value": "missing event_type",
                "message": "Run infra/10_bq.sh for canonical schema",
            }
        )

    if "ts" in columns and "exported_at" in columns:
        checks.append(
            {
                "id": "freshness_hours_since_export",
                "sql": f"""
                    SELECT TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(exported_at), HOUR) AS hours
                    FROM `{dest}`
                """,
                "kind": "threshold_max",
                "threshold": 48,
            }
        )

    checks.append(
        {
            "id": "row_count",
            "sql": f"SELECT COUNT(*) AS n FROM `{dest}`",
            "kind": "info",
        }
    )
    if "job_id" in columns:
        checks.append(
            {
                "id": "distinct_jobs",
                "sql": f"SELECT COUNT(DISTINCT job_id) AS n FROM `{dest}` WHERE job_id IS NOT NULL",
                "kind": "info",
            }
        )
    return checks


def evaluate(checks: list[dict[str, Any]], client: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for chk in checks:
        if chk.get("status"):
            out.append({"check_name": chk["id"], "status": chk["status"], "value": chk.get("value"), "detail": chk.get("message")})
            continue
        rows = _run(client, chk["sql"])
        row = rows[0] if rows else {}
        kind = chk["kind"]
        name = chk["id"]
        if kind == "dup":
            total = int(row.get("total") or 0)
            distinct = int(row.get("distinct_ids") or 0)
            value = total - distinct
            status = "fail" if value > 0 else "ok"
            out.append({"check_name": name, "value": value, "threshold": 0, "status": status, "total_rows": total})
        elif kind == "threshold":
            value = int(row.get("bad") or 0)
            th = chk["threshold"]
            out.append({"check_name": name, "value": value, "threshold": th, "status": "fail" if value > th else "ok"})
        elif kind == "threshold_max":
            value = row.get("hours")
            value = int(value) if value is not None else None
            th = chk["threshold"]
            status = "ok" if value is None else ("fail" if value > th else "ok")
            out.append({"check_name": name, "value": value, "threshold": th, "status": status})
        else:
            out.append({"check_name": name, "value": row.get("n"), "status": "info"})
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run read-only BQ DQ checks")
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID", DEFAULT_PROJECT_ID))
    parser.add_argument("--out", default=None, help="Write JSON report path")
    args = parser.parse_args(argv)

    try:
        from google.cloud import bigquery
    except ImportError:
        print(json.dumps({"ok": False, "error": "google-cloud-bigquery not installed"}))
        sys.exit(2)

    client = bigquery.Client(project=args.project)
    cols = _table_columns(client, args.project, "jobs.events")
    checks = build_checks(args.project, cols)
    results = evaluate(checks, client)
    report = {"ok": True, "project_id": args.project, "columns": sorted(cols), "checks": results}
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
