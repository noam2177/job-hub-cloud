from __future__ import annotations

from scripts.bq_dq_local import build_checks


def test_build_checks_legacy_columns() -> None:
    checks = build_checks("noam-job-hub-123", {"event_id", "job_id", "company", "title"})
    ids = {c["id"] for c in checks if "id" in c}
    assert "schema_legacy" in ids or any(c.get("id") == "schema_legacy" for c in checks)
    assert "duplicate_event_id" in ids


def test_build_checks_canonical_columns() -> None:
    cols = {"event_id", "job_id", "event_type", "ts", "exported_at"}
    checks = build_checks("p", cols)
    ids = [c.get("id") for c in checks]
    assert "unknown_event_type_count" in ids
    assert "freshness_hours_since_export" in ids
