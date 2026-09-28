from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from jobs_pipeline.events import derive_events, load_jobs, load_outcomes
from jobs_pipeline.title_family import TITLE_FAMILIES, classify_title

FIXTURE = Path(__file__).parent / "fixtures" / "jobs_synthetic.json"
FORBIDDEN_SNIPPETS = (
    "secret notes",
    "full posting body",
    "hr@example.com",
    "do not leak",
    "reply_from",
    "job_text",
    "submit_note",
)


def _serialize(events: list[dict]) -> str:
    return json.dumps(events, ensure_ascii=False)


def test_load_jobs_missing() -> None:
    assert load_jobs("/nonexistent/jobs.json") == []


def test_allow_list_no_sensitive_leak() -> None:
    jobs = load_jobs(FIXTURE)
    events, _ = derive_events(jobs, [], {})
    blob = _serialize(events)
    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in blob
    assert "@" not in blob
    for ev in events:
        assert set(ev.get("payload") or {}).issubset(
            {"company", "title", "location", "application_type", "source_host", "match_score", "origin"}
        )
        assert "notes" not in ev
        assert "source_url" not in json.dumps(ev.get("payload") or {})


def test_deterministic_event_ids() -> None:
    jobs = load_jobs(FIXTURE)
    e1, s1 = derive_events(jobs, [], {})
    e2, s2 = derive_events(jobs, [], s1)
    assert [x["event_id"] for x in e1] == [x["event_id"] for x in e2]


def test_first_seen_stable_applied_without_ts() -> None:
    jobs = [
        {
            "job_id": "link-x1",
            "title": "Data Analyst",
            "status": "submitted",
            "created_at_utc": "2025-02-01T10:00:00Z",
        }
    ]
    fixed = datetime(2025, 2, 1, 12, 0, tzinfo=timezone.utc)
    e1, st = derive_events(jobs, [], {}, now=fixed)
    e2, _ = derive_events(jobs, [], st, now=datetime(2025, 3, 1, tzinfo=timezone.utc))
    applied1 = [e for e in e1 if e["event_type"] == "applied"][0]
    applied2 = [e for e in e2 if e["event_type"] == "applied"][0]
    assert applied1["ts"] == applied2["ts"] == "2025-02-01T12:00:00Z"


def test_outcomes_parsing(tmp_path: Path) -> None:
    csv_path = tmp_path / "outcomes.csv"
    csv_path.write_text(
        "job_id,event_type,ts\nlink-aaa,interview,2025-01-22T10:00:00Z\nlink-aaa,invalid,2025-01-22T11:00:00Z\n",
        encoding="utf-8",
    )
    rows = load_outcomes(csv_path)
    assert len(rows) == 1 and rows[0]["event_type"] == "interview"


def test_title_family_closed_list() -> None:
    jobs = load_jobs(FIXTURE)
    events, _ = derive_events(jobs, [], {})
    for ev in events:
        assert ev["title_family"] in TITLE_FAMILIES


def test_title_fallback_injection() -> None:
    assert classify_title("Mystery Role XYZ", lambda _t: "software_engineer") == "software_engineer"
    assert classify_title("Mystery Role XYZ") == "other"


def test_source_host_not_full_url() -> None:
    jobs = load_jobs(FIXTURE)
    events, _ = derive_events(jobs, [], {})
    for ev in events:
        host = (ev.get("payload") or {}).get("source_host")
        if host:
            assert "://" not in host and "/" not in host
