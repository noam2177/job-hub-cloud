from __future__ import annotations

import json
from pathlib import Path

from jobs_pipeline.backfill import build_report, run_backfill

FIXTURE = Path(__file__).parent / "fixtures" / "jobs_synthetic.json"


def test_backfill_reconciliation_dry_run(tmp_path: Path) -> None:
    report = run_backfill(FIXTURE, None, tmp_path / "export_state.json", apply=False)
    assert report["jobs_in_ledger"] == 8
    assert report["jobs_with_found_event"] == 8
    assert report["reconciled"] is True
    assert report["dry_run"] is True
    assert report["events_by_type"].get("found") == 8


def test_backfill_json_stdout_shape(capsys) -> None:
    from jobs_pipeline.backfill import main

    main(["--jobs", str(FIXTURE)])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "events_by_type" in data


def test_build_report_dropped() -> None:
    jobs = [{"job_id": "a"}, {"job_id": "b"}]
    events = [{"job_id": "a", "event_type": "found", "event_id": "1"}]
    report = build_report(jobs, events)
    assert report["reconciled"] is False
    assert report["dropped_rows"][0]["reason"] == "missing_found_event"


def test_refuses_seeker_and_red_ledgers(tmp_path: Path) -> None:
    import pytest

    from jobs_pipeline.backfill import ForeignLedger, refuse_foreign_ledger

    for bad in ("dashboard/data/seekers/omer/jobs.json", "real_inputs/jobs.json", "ledger/search_hits.json"):
        with pytest.raises(ForeignLedger):
            refuse_foreign_ledger(tmp_path / bad)
    refuse_foreign_ledger(tmp_path / "ledger" / "jobs.json")
