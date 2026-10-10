#!/usr/bin/env python3
"""Deduplicate jobs.events by event_id (keep latest exported_at). Matches sql/views events_dedup logic."""

from __future__ import annotations

import argparse
import json
import os
import sys

from google.cloud import bigquery


def main() -> int:
    parser = argparse.ArgumentParser(description="Dedupe BigQuery jobs.events on event_id")
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID", "noam-job-hub-123"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run CREATE OR REPLACE (default: report duplicate groups only)",
    )
    args = parser.parse_args()
    table = f"{args.project}.jobs.events"
    client = bigquery.Client(project=args.project)

    dup_probe = f"""
        SELECT event_id, COUNT(*) AS n
        FROM `{table}`
        GROUP BY event_id
        HAVING COUNT(*) > 1
        ORDER BY n DESC
    """
    groups = list(client.query(dup_probe).result())
    extra = sum(int(r.n) - 1 for r in groups)
    print(f"duplicate_groups={len(groups)} extra_rows_to_remove={extra}")
    if not args.apply:
        return 0 if extra == 0 else 1

    dedup_sql = f"""
        CREATE OR REPLACE TABLE `{table}`
        PARTITION BY DATE(ts)
        CLUSTER BY event_type, title_family
        AS
        SELECT * EXCEPT(rn)
        FROM (
          SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY exported_at DESC) AS rn
          FROM `{table}`
        )
        WHERE rn = 1
    """
    job = client.query(dedup_sql)
    job.result()
    print(f"dedup_job_id={job.job_id} bytes_processed={job.total_bytes_processed}")

    verify = list(
        client.query(
            f"SELECT COUNT(*) AS total, COUNT(DISTINCT event_id) AS distinct_ids FROM `{table}`"
        ).result()
    )[0]
    print(
        json.dumps(
            {
                "total_rows": int(verify.total),
                "distinct_event_id": int(verify.distinct_ids),
                "duplicates": int(verify.total) - int(verify.distinct_ids),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
