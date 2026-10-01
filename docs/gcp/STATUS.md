# STATUS — 2026-10-01 (local audit)

**Update (2026-10-01):** P2 **closed** — canonical `jobs.events` + all views deployed via ADC (`scripts/ensure_bq_resources.py`); ledger synced (**147** events in BQ, `rows_to_append: 0`); DQ ok (`out/bq_dq_verify.json`). Project id: `noam-job-hub-123`. **Looker** = operator UI (`docs/looker/LOOKER_DATA_SOURCES.md`). P1/P4/P5 unchanged.

# STATUS — 2026-09-30 (handoff)

**Phase:** G0 + P2 **cloud foundation** and **local dry-run backfill** reported complete by operator. Application code for P1, P4, P5 is committed (**105 pytest**, 0 skipped). **Not live yet:** BigQuery load (`--apply`), Telegram bridge VM, local puller/watcher, P5 Hebrew eval gate.

P3 remains frozen until P1/P2/P4/P5 run clean in production-like conditions.

## Executive position

| Layer | State | Notes |
|---|---|---|
| GCP project `project-471f7026-7c4b-401b-8a8` | Operator: APIs + 3 SAs + dataset `jobs` + DDL/views | Agent cannot call `gcloud`/`bq` from this host (CLI not on PATH) |
| Auth | Operator: ADC + impersonation `sa-local-puller@…` | No JSON keys in repo (R5 ✓) |
| P2 ledger → events | Operator: dry-run **111 jobs**, `reconciled: true` | Agent did not read `jobs.json` (R1/D-7); save report to `out/p2_dry_run.json` for audit |
| P2 BigQuery rows | **Empty until `--apply`** | `state/export_state.json` absent → apply not run yet |
| P1 Telegram + VM | Not deployed | Token not in Secret Manager (GC-G0-4) |
| P4 watcher | Not live | `inbox_raw/` + `JOBHUB_WATCHER=1` pending |
| P5 OCR | Code + smoke (English synthetic); Hebrew pilot open | `data/ads/` gitignored; eval harness `scripts/p5_eval.py` |
| Cost | Cloud **$0** usage so far (loads not applied) | Trial ₪891, expiry **2026-12-04**, $10 budget alerts on |

## Code review (autonomous, 2026-09-30)

- **R1 / D-2:** `jobs_pipeline/events.py` exports only allow-listed payload keys; `sanitize.py` redacts PII before LLM; `backfill.py` refuses non-career ledger paths.
- **R8:** No auto-submit paths in pipeline; Hub owns `jobs.json` via loopback only (`RULES.md` R2).
- **R6:** Steady-state estimate ~$3.7/mo (mostly VM IPv4); Document AI reserved for P5 fallback per `P5_PLAN.md`.
- **Infra:** `infra/00_project.sh`, `01_apis.sh`, `10_bq.sh`, `20_vm.sh`, `21_harden.sh`, `30_pubsub.sh` + systemd units ready; all default `DRY_RUN=1`.

## Commits (reviewed)

1. `6df1196` G0+P2 · 2. `f7299fa` P1+P4 · 3. `783423d` P5 · 4. `22b666b` decisions

## Prior automated evidence

- Synthetic backfill: 8 jobs, 16 events, reconciled (tests).
- VLM smoke (`scripts/p5_smoke.py`): 5/5 fields on synthetic English ad.

## Blocked / optional

- GLM repo review: Hub `GLM_MAX_CALLS_SESSION` (issue #14).
- P5 GCP eval paths: need `JOBHUB_ALLOW_GCP_EVAL=1` + explicit approval if local < 90%.

## Cost to date

Cloud $0 (no `--apply`, no VM). Local Ollama $0 for completed Hebrew eval (not finished).
