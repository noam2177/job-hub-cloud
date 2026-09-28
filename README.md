# job-hub-cloud · מרכז משרות · ענן

Semi-automatic job-search pipeline on GCP (free tier, < $10/month) that plugs into the local OpenClaw Hub career bus.

```
Telegram intake bot ─▶ e2-micro VM listener ─▶ Pub/Sub `tasks` ─(pull)─▶ local puller ─┐
Drive for Desktop `inbox_raw/` ─▶ local watcher ───────────────────────────────────────┤
                                                                                      ▼
                          local dispatcher (dedupe, ack-after-success, state/jobhub_local.db)
                           ├─ link  ─▶ Hub loopback POST /api/career/link (Hub owns jobs.json)
                           └─ file  ─▶ state/ocr_queue ─▶ P5 extraction ─▶ review queue
Hub ledger (read-only) ─▶ events exporter ─▶ BigQuery `jobs.events` (load jobs) ─▶ views ─▶ Looker Studio
```

- Source of truth: [`docs/gcp/BRIEF.md`](docs/gcp/BRIEF.md) · tasks: [`docs/gcp/TASKS.md`](docs/gcp/TASKS.md) · status: [`docs/gcp/STATUS.md`](docs/gcp/STATUS.md)
- Owner steps: [`docs/gcp/NOAM_GUIDE.md`](docs/gcp/NOAM_GUIDE.md)

## Dev

```powershell
python -m venv .venv; .\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\pre-commit install
```

All `infra/*.sh` scripts print commands by default (`DRY_RUN=1`). Nothing here holds credentials.
