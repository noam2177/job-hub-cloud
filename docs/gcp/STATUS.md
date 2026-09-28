# STATUS — 2026-09-28

**Phase:** P2 (local build done, committed first). Then P1+P4 review, then P5. P3 frozen.

## Done
- G0-5/G0-6: repo, secret/RED-path scanner (pre-commit), `.env.example`, RULES, COST_LEDGER, BRIEF v2, DECISIONS D-0..D-10.
- Task contract v1 + validator; untrusted-input sanitizer (EN/HE injection, bidi, PII redaction).
- P2: DDL, views (Wilson SQL verified against Python to 1e-9), DQ checks, events with allow-list, exporter
  (batch load jobs, transient-only retry), backfill with reconciliation and Omer/RED ledger guard, title-family rules
  (agree 16/16 with a local Ollama golden set).

## Review fixes applied to P2 before commit
1. Wilson constant used 1.9216 instead of z² = 3.8416; the SQL test that should have caught it was skipped. Fixed + real test.
2. Response-rate counts now `COUNT(DISTINCT job_id)`.
3. Exporter retries only transient errors (429/5xx/timeouts).
4. Backfill test writes state to a temp dir.

## In progress / on disk, not committed
- P1+P4 (listener, puller, dispatcher, watcher, infra, systemd): builder finished, 61 tests passed in its run; Cursor review next.
- P5: code files only, no tests, `scripts/p5_eval.py` possibly truncated; Cursor completes after P1+P4.

## Blocked
- GLM review: Hub session call cap (`GLM_MAX_CALLS_SESSION`). Issue #14.

## Open decisions
D-1, D-2 (taxonomy, allow-list), D-6 (drop Tailscale), D-7 (CV local), D-9 (P3 verifies Spark output).

## Cost to date
Cloud $0. Local Ollama $0. GLM $0 (blocked).
