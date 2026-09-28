# TASKS (GC- ledger)

Status: todo / inspect / planned / approved / building / verify / blocked / done. Owner: C = Cursor, N = Noam, CL = Claude via Noam.
GitHub issues: https://github.com/noam2177/job-hub-cloud/issues

| ID | Owner | Status | Updated | Evidence |
|---|---|---|---|---|
| GC-G0-1 trial expiry + budget alerts | N | todo | 2026-09-28 | issue #4, `COST_LEDGER.md` |
| GC-G0-2 project + service accounts | N (C script) | verify | 2026-09-28 | `infra/00_project.sh`, issue #5 |
| GC-G0-3 APIs per phase | N (C script) | verify | 2026-09-28 | `infra/01_apis.sh` |
| GC-G0-4 intake token in Secret Manager | N | todo | 2026-09-28 | `NOAM_GUIDE.md` step 5, issue #8 |
| GC-G0-5 repo, .gitignore, .env.example, secret scan | C | done | 2026-09-28 | `tests/test_secret_scan.py` |
| GC-G0-6 RULES, COST_LEDGER | C | done | 2026-09-28 | `RULES.md`, `COST_LEDGER.md` |
| GC-G0-7 day-80 go/no-go | N | todo | 2026-09-28 | `COST_LEDGER.md` |
| GC-P2-00 jobs.json count + local dry-run backfill | N | todo | 2026-09-28 | issue #1 |
| GC-P2-01 taxonomy + field dictionary | C+N | done (D-1, D-2, D-11 approved) | 2026-09-28 | `P2_TAXONOMY.md`, issue #2 |
| GC-P2-02 DDL + `infra/10_bq.sh` | C | done | 2026-09-28 | `sql/ddl_events.sql`, parse tests |
| GC-P2-03 exporter (load jobs, transient-only retry) | C | done | 2026-09-28 | `tests/test_bq_exporter.py` |
| GC-P2-04 backfill + reconciliation | C (N runs) | verify | 2026-09-28 | `tests/test_backfill.py`, issue #6 |
| GC-P2-05 views with n + Wilson | C | done | 2026-09-28 | `tests/test_views_sql.py` (SQL vs `stats.wilson`, 1e-9) |
| GC-P2-06 Looker Studio | N (C doc) | todo | 2026-09-28 | `docs/looker_steps.md`, issue #7 |
| GC-P2-07 single exporter design | C | done | 2026-09-28 | D-8, `BRIEF.md` R2 |
| GC-P2-08 data-quality checks | C | done | 2026-09-28 | `sql/dq_checks.sql`, `RUNBOOK_P2.md` |
| GC-P1-01..07 VM, hardening, Pub/Sub, listener, puller, systemd | C (N runs) | done in code; cloud run pending | 2026-09-28 | commit f7299fa; `RUNBOOK_P1.md`; issue #9 |
| GC-P1-08 7-day soak | N | todo | 2026-09-28 | issue #10 |
| GC-P4-01 task schema v1 | C | done | 2026-09-28 | `tests/test_contracts.py` |
| GC-P4-L1..07 local watcher, dedupe, routing, tests | C | done in code; live run pending | 2026-09-28 | commit f7299fa; issue #11 |
| GC-P5-01 20 labeled ads | N | todo | 2026-09-28 | issue #12 |
| GC-P5-02..07 schema, OCR, structuring, eval | C | done in code; eval on real ads pending | 2026-09-28 | `P5_PLAN.md`; local VLM smoke 5/5 fields on a synthetic ad |
| GC-P5-03 Document AI processor | N | todo (only if local paths miss the bar) | 2026-09-28 | `P5_PLAN.md` |
| GC-P3-* (scope per D-7, D-9: local-only Spark CV verifier + cover-letter draft) | C+N | frozen until P1/P2/P4/P5 run clean | 2026-09-28 | `P3_PLAN.md` |
