from __future__ import annotations

from pathlib import Path

from jobs_pipeline.local_insights import aggregate_ledger

FIXTURE = Path(__file__).parent / "fixtures" / "jobs_synthetic.json"


def test_aggregate_ledger_counts() -> None:
    stats = aggregate_ledger(FIXTURE)
    assert stats["jobs_total"] == 8
    assert stats["applied_count"] >= 1
    assert "by_title_family" in stats
    assert sum(stats["by_status"].values()) == 8
