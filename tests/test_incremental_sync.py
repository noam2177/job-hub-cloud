from __future__ import annotations

from pathlib import Path
from typing import Any

from jobs_pipeline.incremental_sync import (
    event_fingerprint,
    run_incremental_sync,
    select_events_to_append,
)

FIXTURE = Path(__file__).parent / "fixtures" / "jobs_synthetic.json"


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def result(self) -> list[Any]:
        return self._rows


class FakeBqClient:
    def __init__(self, event_ids: set[str], fingerprints: dict[str, str] | None = None) -> None:
        self.event_ids = event_ids
        self.fingerprints = fingerprints or {}
        self.queries: list[str] = []

    def query(self, sql: str, job_config: Any = None) -> FakeResult:
        self.queries.append(sql)
        if "DISTINCT event_id" in sql:
            return FakeResult([type("R", (), {"event_id": eid})() for eid in self.event_ids])
        rows = []
        for eid, fp in self.fingerprints.items():
            rows.append(
                type(
                    "R",
                    (),
                    {
                        "event_id": eid,
                        "job_id": "j1",
                        "event_type": "found",
                        "ts": "2025-01-01T00:00:00Z",
                        "cv_version": None,
                        "title_family": "other",
                        "keywords": [],
                        "source_type": "text",
                        "payload": {},
                    },
                )()
            )
        return FakeResult(rows)


def test_select_new_events_only() -> None:
    derived = [
        {"event_id": "a", "job_id": "1", "event_type": "found", "ts": "2025-01-01T00:00:00Z", "payload": {}},
        {"event_id": "b", "job_id": "2", "event_type": "found", "ts": "2025-01-02T00:00:00Z", "payload": {}},
    ]
    to_append, sel = select_events_to_append(
        derived,
        bq_event_ids={"a"},
        bq_fingerprints={},
        local_fingerprints={},
    )
    assert len(to_append) == 1
    assert to_append[0]["event_id"] == "b"
    assert sel["stats"]["new"] == 1


def test_fingerprint_detects_payload_update() -> None:
    e1 = {
        "event_id": "x",
        "job_id": "1",
        "event_type": "found",
        "ts": "2025-01-01T00:00:00Z",
        "payload": {"company": "A"},
    }
    e2 = dict(e1)
    e2["payload"] = {"company": "B"}
    assert event_fingerprint(e1) != event_fingerprint(e2)


def test_incremental_dry_run_no_client(tmp_path: Path) -> None:
    report = run_incremental_sync(
        FIXTURE,
        {},
        outcomes_path=None,
        project_id="noam-job-hub-123",
        client=None,
        apply=False,
    )
    assert report["dry_run"] is True
    assert report["reconciled"] is True
    assert report["rows_to_append"] == report["event_count"]


def test_incremental_selection_with_bq_catalog(tmp_path: Path) -> None:
    from jobs_pipeline.events import derive_events, load_jobs

    jobs = load_jobs(FIXTURE)
    events, _ = derive_events(jobs, [], {})
    first = events[0]
    fp = event_fingerprint(first)
    client = FakeBqClient({first["event_id"]}, {first["event_id"]: fp})

    report = run_incremental_sync(
        FIXTURE,
        {},
        outcomes_path=None,
        project_id="noam-job-hub-123",
        client=client,
        apply=False,
        preview_bq=True,
    )
    assert report["rows_to_append"] < report["event_count"]
    skipped = report["incremental"]["unchanged"] + report["incremental"]["already_in_bq"]
    assert skipped >= 1
