from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jobs_pipeline.title_family import TITLE_FAMILIES, classify_title

EVENT_TYPES = frozenset(
    {
        "found",
        "draft_created",
        "applied",
        "reply",
        "interview",
        "reject",
        "offer",
        "withdrawn",
        "closed",
    }
)
OUTCOME_TYPES = frozenset({"interview", "reject", "offer", "withdrawn"})
APPLIED_STATUSES = frozenset({"submitted", "sent", "email_sent", "form_submitted"})
FOUND_TS_KEYS = ("created_at_utc", "found_at_utc", "added_at_utc")
APPLIED_TS_KEYS = ("sent_at_utc", "form_submitted_at_utc", "email_sent_at_utc")
PAYLOAD_KEYS = frozenset(
    {"company", "title", "location", "application_type", "source_host", "match_score", "origin"}
)
CV_PATTERN = re.compile(r"^cv-\d{8}-[a-z_]+$", re.I)
KEYWORD_VOCAB = frozenset(
    {
        "sql",
        "python",
        "ml",
        "nlp",
        "rag",
        "bi",
        "looker",
        "bigquery",
        "gcp",
        "aws",
        "spark",
        "excel",
        "tableau",
        "pandas",
        "dbt",
        "etl",
        "kafka",
        "docker",
        "kubernetes",
        "terraform",
        "java",
        "scala",
        "react",
        "typescript",
    }
)


def load_jobs(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        return []
    return [j for j in jobs if isinstance(j, dict)]


def load_outcomes(csv_path: str | Path) -> list[dict[str, str]]:
    p = Path(csv_path)
    if not p.is_file():
        return []
    rows: list[dict[str, str]] = []
    try:
        with p.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                et = (row.get("event_type") or "").strip()
                if et not in OUTCOME_TYPES:
                    continue
                job_id = (row.get("job_id") or "").strip()
                ts = (row.get("ts") or "").strip()
                if job_id and ts:
                    rows.append({"job_id": job_id, "event_type": et, "ts": ts})
    except OSError:
        return []
    return rows


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def _ts_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_id(job_id: str, event_type: str, ts: str) -> str:
    payload = f"{job_id}|{event_type}|{ts}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _state_key(job_id: str, status: str) -> str:
    return f"{job_id}|{status}"


def _first_seen(state: dict[str, Any], job_id: str, bucket: str, now: datetime) -> str:
    fs = state.setdefault("first_seen", {})
    key = _state_key(job_id, bucket)
    if key not in fs:
        fs[key] = _ts_iso(now)
    return fs[key]


def _cv_basename(job: dict[str, Any]) -> str | None:
    for key in ("cv_basename", "cv_pdf", "cv_docx", "cv_path"):
        val = job.get(key)
        if val:
            return Path(str(val)).name
    return None


def cv_version_for(job: dict[str, Any], title_family: str) -> str | None:
    base = _cv_basename(job)
    if not base:
        return None
    if CV_PATTERN.match(base):
        return base.lower()
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:8]
    return f"cv-{digest}"


def _source_host(job: dict[str, Any]) -> str | None:
    url = job.get("source_url") or job.get("url")
    if not url:
        return None
    try:
        host = urlparse(str(url)).hostname
    except ValueError:
        return None
    return host.lower() if host else None


def _source_type(job: dict[str, Any]) -> str:
    raw = str(job.get("source_type") or job.get("mime") or "text").lower()
    if "pdf" in raw:
        return "pdf"
    if raw in {"image", "image/png", "image/jpeg", "image/webp"} or raw.startswith("image/"):
        return "image"
    return "text"


def keywords_from_title(title: str | None) -> list[str]:
    if not title:
        return []
    tokens = re.findall(r"[a-zA-Z+#.]{2,}", title.lower())
    seen: list[str] = []
    for tok in tokens:
        norm = tok.replace(".", "")
        if norm in KEYWORD_VOCAB and norm not in seen:
            seen.append(norm)
        if len(seen) >= 12:
            break
    return seen


def build_payload(job: dict[str, Any]) -> dict[str, Any]:
    title = str(job.get("title") or "")[:160]
    out: dict[str, Any] = {}
    if job.get("company"):
        out["company"] = str(job["company"])[:160]
    if title:
        out["title"] = title
    if job.get("location"):
        out["location"] = str(job["location"])[:160]
    if job.get("application_type"):
        out["application_type"] = str(job["application_type"])[:64]
    host = _source_host(job)
    if host:
        out["source_host"] = host
    if job.get("match_score") is not None:
        out["match_score"] = job["match_score"]
    if job.get("origin"):
        out["origin"] = str(job["origin"])[:64]
    return {k: v for k, v in out.items() if k in PAYLOAD_KEYS}


def _job_context(
    job: dict[str, Any],
    title_fallback: Callable[[str], str] | None,
) -> dict[str, Any]:
    title = str(job.get("title") or "")
    family = classify_title(title, title_fallback)
    if family not in TITLE_FAMILIES:
        family = "other"
    return {
        "title_family": family,
        "cv_version": cv_version_for(job, family),
        "keywords": keywords_from_title(title),
        "source_type": _source_type(job),
        "payload": build_payload(job),
    }


def _pick_ts(job: dict[str, Any], keys: tuple[str, ...]) -> datetime | None:
    for key in keys:
        dt = _parse_ts(job.get(key))
        if dt:
            return dt
    return None


def derive_events(
    jobs: list[dict[str, Any]],
    outcomes: list[dict[str, str]],
    state: dict[str, Any] | None,
    now: datetime | None = None,
    *,
    title_fallback: Callable[[str], str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    st: dict[str, Any] = dict(state or {})
    st.setdefault("first_seen", {})
    clock = now or datetime.now(timezone.utc).replace(microsecond=0)
    events: list[dict[str, Any]] = []
    jobs_by_id = {str(j.get("job_id") or j.get("id") or ""): j for j in jobs if j.get("job_id") or j.get("id")}

    def emit(job: dict[str, Any], event_type: str, ts: datetime) -> None:
        job_id = str(job.get("job_id") or job.get("id") or "")
        if not job_id or event_type not in EVENT_TYPES:
            return
        ts_s = _ts_iso(ts)
        ctx = _job_context(job, title_fallback)
        events.append(
            {
                "event_id": _event_id(job_id, event_type, ts_s),
                "job_id": job_id,
                "event_type": event_type,
                "ts": ts_s,
                "cv_version": ctx["cv_version"],
                "title_family": ctx["title_family"],
                "keywords": ctx["keywords"],
                "source_type": ctx["source_type"],
                "payload": ctx["payload"],
                "exported_at": None,
            }
        )

    for job in jobs:
        job_id = str(job.get("job_id") or job.get("id") or "")
        if not job_id:
            continue
        ctx = _job_context(job, title_fallback)

        found_dt = _pick_ts(job, FOUND_TS_KEYS)
        if found_dt is None:
            found_dt = _parse_ts(_first_seen(st, job_id, "found", clock))
        emit(job, "found", found_dt or clock)

        draft_ts = _parse_ts(job.get("draft_created_at_utc"))
        if draft_ts:
            emit(job, "draft_created", draft_ts)

        status = str(job.get("status") or "").lower()
        applied_dt = _pick_ts(job, APPLIED_TS_KEYS)
        if applied_dt is None and status in APPLIED_STATUSES:
            applied_dt = _parse_ts(_first_seen(st, job_id, "applied", clock))
        if applied_dt:
            emit(job, "applied", applied_dt)

        reply_dt = _parse_ts(job.get("reply_seen_at_utc"))
        if reply_dt:
            emit(job, "reply", reply_dt)

        if status == "closed":
            closed_dt = _parse_ts(_first_seen(st, job_id, "closed", clock))
            emit(job, "closed", closed_dt or clock)

        _ = ctx

    for row in outcomes:
        job = jobs_by_id.get(row["job_id"], {"job_id": row["job_id"], "title": ""})
        ts = _parse_ts(row["ts"])
        if ts:
            emit(job, row["event_type"], ts)

    return events, st
