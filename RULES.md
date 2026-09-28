# RULES (short form of `docs/gcp/BRIEF.md` §2 — the brief wins on conflict)

1. RED data never enters this repo or the cloud. AMBER (owner CV/contact) stays local unless D-7 says otherwise.
2. No new writers: never write `statedb.db`, `orchestration.db`, `jobs.json`, `applications.jsonl`. Links go through the Hub loopback API.
3. No inbound ports on the PC; the VM has IAP SSH only. Tasks are pulled.
4. All external text passes `jobs_pipeline/sanitize.py` before any LLM. LLM output never runs commands.
5. Secrets only in Secret Manager or local `.env`. No key files. Pre-commit scan must pass.
6. Scripts default to `DRY_RUN=1`. Cloud actions are run by Noam. Payment settings are Console-only, by Noam.
7. Idempotent handlers; ack after success; DLQ after 5 attempts.
8. Drafts only (`[TEST]`), never auto-send.
9. Every draft claim cites a source line; every AI step is evaluated on labeled data before adoption.
10. `us-central1` / BigQuery `US` only. No new cloud resources in the last 10 trial days.
