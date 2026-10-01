#!/usr/bin/env python3
"""Incremental ledger → BigQuery sync (WRITE_APPEND only, no full table truncate)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobs_pipeline.backfill import _load_state, _save_state
from jobs_pipeline.incremental_sync import DEFAULT_PROJECT_ID, default_ledger_path, run_incremental_sync


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Sync ledger/jobs.json to BigQuery jobs.events incrementally (append / dedupe-safe)."
    )
    parser.add_argument(
        "--jobs",
        default=None,
        help="Path to ledger jobs.json (default: JOBHUB_LEDGER_JOBS, CAREER_DRIVE_BUS_DIR/ledger/jobs.json, or ./ledger/jobs.json)",
    )
    parser.add_argument("--outcomes", default=None, help="Optional outcomes.csv")
    parser.add_argument("--state", default="state/export_state.json", help="Export state file")
    parser.add_argument("--project", default=None, help=f"GCP project id (default: GCP_PROJECT_ID or {DEFAULT_PROJECT_ID})")
    parser.add_argument("--table", default="jobs.events", help="BigQuery table id (dataset.table)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Append new/updated rows to BigQuery (requires ADC + BigQuery access)",
    )
    parser.add_argument(
        "--check-bq",
        action="store_true",
        help="Dry-run but query BigQuery for existing event_ids (no load jobs)",
    )
    args = parser.parse_args(argv)

    jobs_path = Path(args.jobs) if args.jobs else default_ledger_path()
    if not jobs_path.is_file():
        print(f"Ledger not found: {jobs_path}", file=sys.stderr)
        sys.exit(1)

    project = args.project or os.environ.get("GCP_PROJECT_ID") or DEFAULT_PROJECT_ID
    state_path = Path(args.state)
    state = _load_state(state_path)
    outcomes = Path(args.outcomes) if args.outcomes else None

    client = None
    if args.apply or args.check_bq:
        try:
            from google.cloud import bigquery
        except ImportError:
            print("google-cloud-bigquery is required for --apply / --check-bq", file=sys.stderr)
            sys.exit(2)
        client = bigquery.Client(project=project)

    report = run_incremental_sync(
        jobs_path,
        state,
        outcomes_path=outcomes,
        project_id=project,
        table=args.table,
        client=client,
        apply=args.apply,
        preview_bq=args.check_bq and not args.apply,
    )
    new_state = report.pop("_state", None)
    if new_state is not None:
        _save_state(state_path, new_state)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
