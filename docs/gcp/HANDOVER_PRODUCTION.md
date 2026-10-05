# Production handover — job-hub-cloud

## P2 data layer (live)

- Project: `noam-job-hub-123`, dataset `jobs`, table `events` (canonical).
- Views: `events_dedup`, `jobs_latest`, `days_to_reply`, `response_rate_by_*`.
- Verify: `python scripts/bq_dq_local.py` → 146 rows, 0 duplicate `event_id`.

## Local agents (no token spend)

| Script | Role |
|--------|------|
| `scripts/job_insights_local.py` | Ledger aggregates; `--ollama` for Hebrew summary via Hub |
| `scripts/process_ocr_queue_local.py` | OCR queue → `state/ocr_results` via Local VLM |
| `local/windows/run_watcher_background.ps1` | Drive `inbox_raw` watcher |
| `scripts/ollama_fixtures.py` | Synthetic ads / title families (dev) |

Requires: `HUB_ROOT` → `principal-architect-hub`, Ollama on `127.0.0.1:11434`, Hub dashboard for link handler.

## Cloud deploy (operator, billing)

See copy-paste block in chat / run `scripts/dry_run_infra.ps1` (Git Bash).
