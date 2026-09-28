# P2 BigQuery runbook

## Dry-run backfill (local)

```powershell
cd C:\Users\noam1\Documents\GitHub\job-hub-cloud
.\.venv\Scripts\python.exe -m jobs_pipeline.backfill --jobs path\to\jobs.json
```

Optional: `--outcomes path\to\outcomes.csv`, `--state state\export_state.json`.

Prints JSON with `jobs_in_ledger`, `jobs_with_found_event`, `events_by_type`, `dropped_rows`, and `reconciled`.

Apply (loads to BigQuery; requires `GCP_PROJECT_ID` and `google-cloud-bigquery`):

```powershell
$env:GCP_PROJECT_ID = "your-gcp-project"
.\.venv\Scripts\python.exe -m jobs_pipeline.backfill --jobs path\to\jobs.json --apply
```

State file is written only after a successful apply.

## Infra: dataset, table, views

From Git Bash or WSL, with `bq` CLI authenticated:

```bash
export PROJECT=your-gcp-project
DRY_RUN=1 bash infra/10_bq.sh   # prints commands only
DRY_RUN=0 bash infra/10_bq.sh   # creates jobs dataset (US), ddl, views
```

## Data quality checks

Substitute project id, then run each statement in `sql/dq_checks.sql`:

```bash
sed "s/\${PROJECT}/${PROJECT}/g" sql/dq_checks.sql | bq query --use_legacy_sql=false
```

Expected columns: `check_name`, `value`, `threshold`, `status` (`ok` or `fail`).

Checks: duplicate `event_id`, null rates (7-day window), export freshness (48h), unknown `event_type`.
