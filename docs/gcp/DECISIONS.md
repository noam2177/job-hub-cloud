# DECISIONS (append-only)

| D | Date | Decision | Alternatives | Who |
|---|---|---|---|---|
| D-0 | 2026-09-28 | Goal is both a working tool and GCP portfolio experience | tool only; learning only | Noam |
| D-1 | 2026-09-28 | Event taxonomy in `P2_TAXONOMY.md` (found, draft_created, applied, reply, interview, reject, offer, withdrawn, closed); interview/reject/offer/withdrawn come from a manual `state/outcomes.csv` | infer from e-mail text (no signal exists; PII risk) | **proposed** — Noam to approve |
| D-2 | 2026-09-28 | Export allow-list: company, title, location, application_type, source_host, match_score, origin; never notes/job_text/reply_*/paths/full URL | export whole row | **proposed** — Noam to approve |
| D-3 | 2026-09-28 | Local side never writes Hub stores: links → loopback `POST /api/career/link`; files → own `state/` queue | write `inbox/*.task.json`; write `jobs.json` | Cursor (per R2); Noam to confirm |
| D-4 | 2026-09-28 | Drive intake is local (watcher on synced `inbox_raw/`), no Drive API/webhook | Cloud Run webhook; Scheduler polling | Noam |
| D-5 | 2026-09-28 | Task v1: add `payload.sha256`, `payload.mime`; content-hash dedupe for files; strict schema | v1 as drafted | Cursor; Noam to confirm |
| D-6 | 2026-09-28 | Telegram intake on an e2-micro VM, long-poll, new dedicated bot; no Tailscale (IAP SSH) | Cloud Run webhook (cheaper); local only | Noam (VM); Tailscale drop proposed |
| D-7 | 2026-09-28 | Owner CV / master profile is AMBER: local retrieval + local/GLM wording only after sanitization; not uploaded to Vertex AI Search unless approved | upload corpus to GCP | **proposed** |
| D-8 | 2026-09-28 | BigQuery writes via batch load jobs (free), dedupe in views | streaming insert with row_ids | Cursor |
| D-9 | 2026-09-28 | P3 does not re-write CVs (Spark does); P3 = evidence verifier of Spark output + cover-letter draft | P3 drafts CVs itself | **proposed** |
| D-10 | 2026-09-28 | Ground-truth fixtures are template-based, not LLM-generated (qwen2.5:7b produced broken Hebrew) | LLM fixtures | Cursor |
| D-1 ✔ | 2026-09-28 | **Approved** as proposed: event taxonomy in `P2_TAXONOMY.md` | — | Noam |
| D-2 ✔ | 2026-09-28 | **Approved** as proposed: export allow-list in `P2_TAXONOMY.md` | — | Noam |
| D-11 | 2026-09-28 | **Approved**: title families `data_analyst, bi_analyst, data_scientist, ml_engineer, data_engineer, software_engineer, research, other` (closed list in `jobs_pipeline/title_family.py`) | rename/add families | Noam |
| D-6 ✔ | 2026-09-28 | **Approved**: no Tailscale; admin access is IAP SSH only (P1-03 removed) | Tailscale admin mesh | Noam |
| D-7 ✔ | 2026-09-28 | **Approved**: CV / master profile stays on the local PC only; never uploaded to GCP (no Vertex AI Search over the CV) | sanitized upload | Noam |
| D-9 ✔ | 2026-09-28 | **Approved**: P3 verifies Spark's tailored CVs against the master CV and drafts cover letters; it never writes CVs | P3 writes CVs | Noam |
