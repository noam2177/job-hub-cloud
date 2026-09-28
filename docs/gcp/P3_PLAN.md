# P3 — Evidence layer over the professional profile (revised by D-7, D-9)

Spark already writes tailored CVs from the master CV (`ledger/cv_requests/*.json` → DOCX, rules in
`handoff/CV_GENERATION_RULES.md`). P3 therefore does **not** write CVs. It:

1. **P3-00 verify Spark output** — split a tailored CV into claim lines; match each to master-CV lines; flag
   unsupported claims; write `drafts/[TEST]-<job_id>-evidence.md` with one citation per claim.
2. **P3-07 cover-letter draft** — only from retrieved master lines; every sentence cites a line id; refuse when
   no evidence (< 2 supporting lines).

## Corpus (P3-01) — checklist before anything is indexed

- [ ] Source files listed by path (master CV DOCX, CV rules MD, own public notebooks) — Noam confirms the list.
- [ ] Contact block removed (phone, e-mail, address, ID number) → `jobs_pipeline.sanitize.redact_pii` + manual look.
- [ ] Nothing from Sagole / office / Octave; no client names.
- [ ] Output lives in `state/corpus/` (gitignored); each chunk has `{doc, line_id, project, skills, year}`.

## Retrieval order (cheapest first)

| Step | Engine | Cost | When |
|---|---|---|---|
| P3-06 | local lexical (BM25) + local embeddings via Ollama, SQLite | $0 | first |
| P3-03/05 | Vertex AI Search Standard | free quota, then ~$1.50/1k queries | only if P3-06 recall@3 < 80% and D-7 approves upload |

## Evaluation (P3-04/05)
`data/rag_eval_template.csv`: `posting_id, posting_text_file, expected_projects (pipe-separated), notes`.
10 postings; metric recall@3 with Wilson interval; results in `P3_EVAL.md`.
