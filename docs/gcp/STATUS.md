# STATUS — 2026-09-28 (end of session)

**Phase:** all Cursor-side code for G0, P2, P1, P4, P5 is committed and tested (105 tests, 0 skipped).
Next is Noam's cloud/label work. P3 frozen until P1/P2/P4/P5 run clean.

## Commits (sequential, reviewed)
1. `6df1196` G0+P2 — guardrails, contract v1, sanitizer, BigQuery layer.
2. `f7299fa` P1+P4 — Telegram listener, puller, dispatcher, watcher, infra, systemd.
3. P5 — ad schema, OCR/VLM engines, structuring, pipeline, eval script, templates.

## Review fixes applied before each commit
- P2: Wilson z² constant (1.9216 → 3.8416) + real SQL-vs-Python test; distinct job counts; transient-only retry.
- P1+P4: Hub HTTP 429/408 treated as transient (was silently dropping links); publish-failure backoff (was a hot loop);
  atomic OCR queue writes; healthcheck now restarts (was blocked by `set -e` + non-root user); missing
  `secretAccessor` binding added; `IPV6_ONLY=1` no longer creates two VMs.
- P5: state moved out of the Drive bus; path-traversal prefix bug; deterministic image `found` event with
  `event_id` + title family; prompt delimiter injection; injection scan over all fields; bad contact no longer
  fails the whole ad; network errors retry instead of going to review.

## Evidence
- Local VLM smoke (`scripts/p5_smoke.py`, qwen3-vl 8B): 5/5 fields on a synthetic English ad, 56 s cold.
  Self-reported confidence was 1.0 → not calibrated; real Hebrew ads needed.
- Backfill dry-run on the synthetic ledger: 8 jobs, 16 events, reconciled.

## Blocked
- GLM review: Hub session call cap (`GLM_MAX_CALLS_SESSION`). Issue #14.

## Open decisions
D-1, D-2, D-6, D-7, D-9 (see `DECISIONS.md`).

## Cost to date
Cloud $0. Local Ollama $0. GLM $0.
