# P2-01 — Event taxonomy and field dictionary (D-1, D-2)

Status: **approved 2026-09-28** (D-1, D-2, D-11 in `DECISIONS.md`).

## Sources (read-only; this project never writes them)

| Source | Writer today | Used for |
|---|---|---|
| `<bus>/ledger/jobs.json` → `{"jobs":[...]}` | Hub `career_link`, `career_submit`, `career_digest`, and Spark | snapshot of every job |
| `<bus>/ledger/applications.jsonl` | Hub `career_submit` | submission log |
| `state/outcomes.csv` (new, local, manual) | Noam | interview / reject / offer / withdrawn |
| job-hub-cloud pipeline | this repo | `draft_created`, `found` for image ads |

The exporter is **snapshot-diff + deterministic event ids**: re-running it emits the same `event_id`s, so re-runs are no-ops after view-level dedupe.

## event_type (closed list)

| event_type | Derived from | ts |
|---|---|---|
| `found` | any job row | `created_at_utc` → `found_at_utc` → `added_at_utc` → first time seen by exporter |
| `draft_created` | P3 drafting step | draft write time |
| `applied` | `sent_at_utc` / `form_submitted_at_utc` / `email_sent_at_utc`, or status in {submitted, sent, email_sent, form_submitted} | that timestamp, else first time seen in that status |
| `reply` | `reply_seen_at_utc` present | `reply_seen_at_utc` |
| `interview` / `reject` / `offer` / `withdrawn` | `state/outcomes.csv` rows `job_id,event_type,ts` | CSV ts |
| `closed` | status `closed` | first time seen closed |

`event_id = sha256(job_id|event_type|ts)`; BigQuery `row_ids` and view dedupe both use it.

## Field dictionary (export allow-list, D-2)

| Column | Rule |
|---|---|
| `job_id` | as in ledger (`link-<sha12>` or Spark id) |
| `event_type` | list above |
| `ts` | UTC TIMESTAMP |
| `cv_version` | `cv-YYYYMMDD-<family>` if the CV basename already matches; else `cv-` + sha256(basename)[:8]; null if none |
| `title_family` | closed list below; rule-based, Ollama fallback for unknown titles, `other` if still unsure |
| `keywords` | ≤ 12 lowercase skill tokens from a fixed vocabulary (sql, python, ml, nlp, rag, bi, looker, bigquery, gcp, aws, spark, excel, ...) |
| `source_type` | `text` \| `image` \| `pdf` |
| `payload` JSON | only: `company`, `title` (≤160), `location`, `application_type`, `source_host` (host only, not the full URL), `match_score`, `origin` |

**Never exported:** `notes`, `job_text`, `reply_from`, `reply_subject`, `reply_message_id`, `submit_note`, `blocker`, `verification`, `cv_pdf`/`cv_docx` paths, `spark_task_id`, full `source_url`, any e-mail or phone.

## title_family (approved, D-11)

`data_analyst`, `bi_analyst`, `data_scientist`, `ml_engineer`, `data_engineer`, `software_engineer`, `research`, `other`.

## Statistics rule

Rates are shown with `n` and a 95% Wilson interval. Any group with `n < 30` is labelled `insufficient_n` in the view and must not be used for conclusions.
