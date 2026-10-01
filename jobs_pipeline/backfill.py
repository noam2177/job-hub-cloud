from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jobs_pipeline.events import derive_events, load_jobs, load_outcomes
from jobs_pipeline.incremental_sync import run_incremental_sync


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def build_report(jobs: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    job_ids = {str(j.get("job_id") or j.get("id")) for j in jobs if j.get("job_id") or j.get("id")}
    found_jobs = {e["job_id"] for e in events if e.get("event_type") == "found"}
    dropped: list[dict[str, str]] = []
    for jid in job_ids - found_jobs:
        dropped.append({"job_id": jid, "reason": "missing_found_event"})
    by_type = dict(Counter(e.get("event_type", "?") for e in events))
    return {
        "jobs_in_ledger": len(job_ids),
        "jobs_with_found_event": len(found_jobs),
        "events_by_type": by_type,
        "dropped_rows": dropped,
        "reconciled": len(job_ids) == len(found_jobs),
    }


_FOREIGN_MARKERS = ("seekers", "sagole", "real_inputs", "secure_data_939")


class ForeignLedger(ValueError):
    pass


def refuse_foreign_ledger(path: Path) -> None:
    """Omer's seeker track and RED paths are never exported; only the operator's career ledger is."""
    posix = path.as_posix().lower()
    if any(marker in posix for marker in _FOREIGN_MARKERS) or not re.fullmatch(r"jobs(_\w+)?\.json", path.name):
        raise ForeignLedger(path.name)


def run_backfill(
    jobs_path: Path,
    outcomes_path: Path | None,
    state_path: Path,
    *,
    apply: bool,
) -> dict[str, Any]:
    refuse_foreign_ledger(jobs_path)
    jobs = load_jobs(jobs_path)
    outcomes = load_outcomes(outcomes_path) if outcomes_path else []
    state = _load_state(state_path)
    project = os.environ.get("GCP_PROJECT_ID")
    if apply and not project:
        print("GCP_PROJECT_ID is required for --apply", file=sys.stderr)
        sys.exit(2)

    client = None
    if apply:
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=project)
        except ImportError:
            print("google-cloud-bigquery is required for --apply", file=sys.stderr)
            sys.exit(2)

    report = run_incremental_sync(
        jobs_path,
        state,
        outcomes_path=outcomes_path,
        project_id=project or "noam-job-hub-123",
        client=client,
        apply=apply,
    )
    new_state = report.pop("_state", None)
    if new_state is not None:
        _save_state(state_path, new_state)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Backfill job events to BigQuery")
    parser.add_argument("--jobs", required=True, help="Path to ledger jobs.json")
    parser.add_argument("--outcomes", default=None, help="Path to outcomes.csv")
    parser.add_argument("--state", default="state/export_state.json", help="Export state file")
    parser.add_argument("--apply", action="store_true", help="Load to BigQuery (requires GCP_PROJECT_ID)")
    args = parser.parse_args(argv)

    outcomes = Path(args.outcomes) if args.outcomes else None
    report = run_backfill(Path(args.jobs), outcomes, Path(args.state), apply=args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
