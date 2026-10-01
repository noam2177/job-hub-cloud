#!/usr/bin/env python3
"""P2 canonical schema migration (explicit operator approval). Drops legacy events + recreates views."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "noam-job-hub-123"


def _substitute(sql: str, project: str) -> str:
    return sql.replace("${PROJECT}", project)


def _run_statements(client, sql: str) -> None:
    # BigQuery client runs one statement at a time for DDL mixes
    parts = [p.strip() for p in sql.split(";") if p.strip()]
    for stmt in parts:
        job = client.query(stmt)
        job.result()
        print(f"OK: {stmt[:80].replace(chr(10), ' ')}...")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=PROJECT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    p = args.project

    ddl_path = ROOT / "sql" / "ddl_events.sql"
    views_path = ROOT / "sql" / "views.sql"
    ddl = _substitute(ddl_path.read_text(encoding="utf-8"), p)
    views = _substitute(views_path.read_text(encoding="utf-8"), p)

    drops = f"""
DROP VIEW IF EXISTS `{p}.jobs.response_rate_by_cv_version`;
DROP VIEW IF EXISTS `{p}.jobs.response_rate_by_title_family`;
DROP VIEW IF EXISTS `{p}.jobs.days_to_reply`;
DROP VIEW IF EXISTS `{p}.jobs.jobs_latest`;
DROP VIEW IF EXISTS `{p}.jobs.events_dedup`;
DROP TABLE IF EXISTS `{p}.jobs.events`;
"""
    if args.dry_run:
        print("DRY RUN — would execute drops + ddl + views")
        print(drops[:200])
        return

    from google.cloud import bigquery

    client = bigquery.Client(project=p)
    print("Dropping legacy views and events table...")
    _run_statements(client, drops)
    print("Creating canonical events table...")
    _run_statements(client, ddl)
    print("Creating views...")
    _run_statements(client, views)
    print("P2 schema migration complete.")


if __name__ == "__main__":
    main()
