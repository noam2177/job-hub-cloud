# TASKS (GC- ledger)

Status: todo / inspect / planned / approved / building / verify / blocked / done. Owner: C = Cursor, N = Noam, CL = Claude via Noam.
GitHub issues: https://github.com/noam2177/job-hub-cloud/issues

| ID | Owner | Status | Updated | Evidence |
|---|---|---|---|---|
| GC-G0-1 trial expiry + budget alerts | N | **done** (expiry 2026-12-04, ₪891, budget alerts) | 2026-09-30 | `COST_LEDGER.md` |
| GC-G0-2 project + service accounts | N (C script) | **done** (sa-telegram-listener, sa-bq-exporter, sa-local-puller) | 2026-09-30 | `infra/00_project.sh`, operator Console |
| GC-G0-3 APIs per phase | N (C script) | **done** (G0 minimum) | 2026-09-30 | `infra/01_apis.sh g0` |
| GC-G0-4 intake token in Secret Manager | N | todo | 2026-09-30 | `NOAM_GUIDE.md` step 5, issue #8 |
| GC-G0-5 repo, .gitignore, .env.example, secret scan | C | done | 2026-09-28 | `tests/test_secret_scan.py` |
| GC-G0-6 RULES, COST_LEDGER | C | done | 2026-09-30 | `COST_LEDGER.md` |
| GC-G0-7 day-80 go/no-go | N | todo | 2026-09-28 | calendar from trial start |
| GC-G0-8 ADC impersonation (local puller / backfill) | N | **done** | 2026-09-30 | operator setup; no keys in repo |
| GC-P2-00 jobs.json count + local dry-run backfill | N | **done** (111 jobs, reconciled) | 2026-09-30 | operator report; save JSON to `out/p2_dry_run.json` |
| GC-P2-01 taxonomy + field dictionary | C+N | done | 2026-09-28 | `P2_TAXONOMY.md` |
| GC-P2-02 DDL + `infra/10_bq.sh` | N (C script) | **done** (dataset `jobs`, US) | 2026-09-30 | `sql/ddl_events.sql`, `sql/views.sql` |
| GC-P2-03 exporter | C | done | 2026-09-28 | `tests/test_bq_exporter.py` |
| GC-P2-04 backfill **live** `--apply` | N | **todo** | 2026-09-30 | `RUNBOOK_P2.md`; needs `GCP_PROJECT_ID` |
| GC-P2-05 views with n + Wilson | C | done | 2026-09-28 | `tests/test_views_sql.py` |
| GC-P2-06 Looker Studio | N | todo | 2026-09-28 | `docs/looker_steps.md`, issue #7 |
| GC-P2-07 single exporter design | C | done | 2026-09-28 | D-8 |
| GC-P2-08 data-quality checks | N | todo after apply | 2026-09-30 | `sql/dq_checks.sql`, `RUNBOOK_P2.md` |
| GC-P1-01..07 VM, Pub/Sub, listener, puller | N (C script) | todo (code ready) | 2026-09-30 | `RUNBOOK_P1.md`, issue #9 |
| GC-P1-08 7-day soak | N | todo | 2026-09-28 | issue #10 |
| GC-P4-L1..07 local watcher | N | todo (code ready) | 2026-09-30 | `local/windows/run_watcher.ps1`, issue #11 |
| GC-P5-01 20 labeled ads | N | in progress | 2026-09-30 | issue #12 |
| GC-P5-02..07 schema, OCR, eval | C | done in code; Hebrew eval pending | 2026-09-30 | `P5_PLAN.md`, `scripts/p5_eval.py` |
| GC-P5-03 Document AI processor | N | todo if local < 90% | 2026-09-28 | `P5_PLAN.md` |
| GC-P3-* | C+N | frozen | 2026-09-28 | `P3_PLAN.md` |
