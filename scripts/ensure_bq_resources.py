#!/usr/bin/env python3
"""Ensure jobs dataset, events table, and views exist (ADC only; no IAM policy APIs)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobs_pipeline.incremental_sync import DEFAULT_PROJECT_ID


def _substitute(sql: str, project: str) -> str:
    return sql.replace("${PROJECT}", project)


def _run_statements(client, sql: str) -> list[str]:
    parts = [p.strip() for p in sql.split(";") if p.strip()]
    done: list[str] = []
    for stmt in parts:
        job = client.query(stmt)
        job.result()
        preview = stmt.split("\n", 1)[0][:100]
        done.append(preview)
        print(f"OK: {preview}...")
    return done


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create BQ dataset/table/views if missing (no IAM changes).")
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID", DEFAULT_PROJECT_ID))
    parser.add_argument("--dataset", default=os.environ.get("BQ_DATASET", "jobs"))
    parser.add_argument("--location", default=os.environ.get("BQ_LOCATION", "US"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    ddl_path = ROOT / "sql" / "ddl_events.sql"
    views_path = ROOT / "sql" / "views.sql"
    ddl = _substitute(ddl_path.read_text(encoding="utf-8"), args.project)
    views = _substitute(views_path.read_text(encoding="utf-8"), args.project)

    if args.dry_run:
        print(f"DRY RUN project={args.project} dataset={args.dataset} location={args.location}")
        print(ddl[:200])
        print("---")
        print(views[:200])
        return

    try:
        from google.cloud import bigquery
    except ImportError:
        print("google-cloud-bigquery is required", file=sys.stderr)
        sys.exit(2)

    client = bigquery.Client(project=args.project)
    dataset_id = f"{args.project}.{args.dataset}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = args.location
    client.create_dataset(dataset, exists_ok=True)
    print(f"OK: dataset {dataset_id} ({args.location})")

    print("Applying ddl_events.sql...")
    _run_statements(client, ddl)
    print("Applying views.sql...")
    _run_statements(client, views)
    print("BigQuery resources ready.")


if __name__ == "__main__":
    main()
