# MASTER BRIEF v2 — `job-hub-cloud` (GCP job-search automation)

> Single source of truth. v1 was the owner's original brief (2026-09-28). v2 folds in the Discovery findings
> and the owner's decisions D-1..D-8 (`DECISIONS.md`). Re-read the relevant section before each task.

Fixed name: **job-hub-cloud** (Hebrew: «מרכז משרות · ענן»). Portfolio id: `job-hub-cloud`. It extends the earlier
`hybrid-cloud-bus` dry run; that one stays archived.

## 0. Role and operating mode

Cursor = implementation engineer (code, tests, SQL, dry-run scripts, docs). Not the cloud operator: no cloud
credentials, never asks for, prints, or stores any. Every task: `Inspect → Plan → APPROVE <id> → Build → Verify → Report`.
Token economy: one task (or one approved batch) per session, targeted reads, patches not rewrites, REPORT ≤ 40 lines.
Cheap sub-steps go to local Ollama through `hub.local_infer.local_chat` (zone checks + $0 spend row); reviews go to GLM
(`glm-5.3` for high importance). Code/docs in English; talk to the owner in Hebrew.

## 1. Mission and end state E0

Semi-automatic job-search pipeline: ingest postings (links, images, PDFs), verify/draft evidence-backed material,
measure the funnel. **< $10/month**, zero sensitive data in the cloud.

E0: Noam sends a job link on the **intake bot** (Telegram) or drops a file into Drive `inbox_raw/`. Then:
1. the task is handled exactly once (dedupe key, local store),
2. link → Hub loopback `POST /api/career/link` (the Hub stays the ledger writer); file → local OCR queue,
3. a `[TEST]` draft with per-claim citations appears in Drive `drafts/`,
4. events land in BigQuery through the single exporter,
5. Looker Studio reflects it. Nothing is ever sent to an employer automatically.

| Area | Target |
|---|---|
| P2 BigQuery | every ledger job has a `found` event (reconciled = true); dashboard with 3 pages |
| P1 Bridge VM | 99% uptime over a 7-day soak; Telegram → processed < 60 s p95 while the PC is on |
| P4 local intake | file in `inbox_raw/` → task < 30 s p95; zero double-processing in tests |
| P5 OCR | ≥ 90% field accuracy (Wilson low ≥ 80%) on 20 labeled ads; < $0.01 per ad |
| P3 evidence | 100% of draft claims cite a master-CV line; recall@3 ≥ 80% on 10 postings |

## 2. Non-negotiable rules

| # | Rule |
|---|---|
| R1 | GREEN (public job ads, owner's own code) may go to the cloud. RED (Sagole, `real_inputs`, ID numbers, real ground truth) never leaves the machine. The owner's CV/contact data is **AMBER**: local PC only, never uploaded to GCP (D-7). |
| R2 | **No new writers to existing stores.** This project never writes `statedb.db`, `orchestration.db`, or the Hub ledger (`jobs.json`, `applications.jsonl`). Links go through the Hub loopback API. This project's only local store is `state/jobhub_local.db`, written only by the local dispatcher. The only BigQuery writer is `jobs_pipeline/bq_exporter.py`. |
| R3 | Outbound-only locally. No inbound ports. Tasks arrive by pull. The VM also has no public ingress (IAP SSH only). |
| R4 | Telegram text, Drive files, ads and OCR output are untrusted → `jobs_pipeline/sanitize.py` before any LLM. LLM output never executes; only allow-listed handlers run. |
| R5 | Secrets only in Secret Manager or local `.env`. Pre-commit `scripts/scan_secrets.py` + detect-secrets. One service account per component, resource-level roles, no key files (impersonation instead). |
| R6 | `COST_LEDGER.md` kept current. Anything expected > $5 needs explicit owner approval. Payment/billing surfaces are operated by Noam only, in the Console (google-pay fence). |
| R7 | Idempotency: dedupe by `dedupe_key`; ack only after success; poison → ack+rejected; transient → nack → DLQ after 5. |
| R8 | Drafts only, `[TEST]` format. No auto-send. |
| R9 | One phase active at a time (order in §4). |
| R10 | Every draft claim cites a source line; every AI component is evaluated on a labeled set before adoption. |
| R11 | One region: `us-central1` / BigQuery `US`. |
| R12 | Trial credit is time-boxed: no new resources in the last 10 days; the day-80 go/no-go (upgrade or tear down) is on the calendar. |

No-touch list (never read, mount, copy, reference): `Desktop/sagole/939`, `real_inputs`, `real_ground_truth.csv`,
`real_benchmark_results.csv`, any `.env`, `statedb.db`. Do not edit the Hub ledger rows or frozen Hub tasks; this project
keeps its own `GC-` ledger in `TASKS.md`. Hub code changes need a separate APPROVE (the Hub has no git history).

## 3. Division of labor

| Actor | Does |
|---|---|
| Cursor | code, tests, SQL, dry-run `infra/*.sh`, docs, click-by-click steps, eval scripts |
| Ollama (local) | cheap sub-steps: title-family fallback, local OCR/VLM baseline, draft wording |
| GLM | advisory review: `glm-5.3-flash` normal, `glm-5.3` high importance |
| Noam | Console/gcloud runs, credentials, bot creation, secrets, Looker Studio, labeling, approvals |
| Claude (chat, relayed) | design/prompt review; questions in `CLAUDE_HANDOFF.md` |
| Spark (existing) | writes tailored CV DOCX from `ledger/cv_requests/*.json` using the master CV; this project only **reads** its output |

## 4. Plan

### 4.1 Existing system this project plugs into (Discovery 2026-09-28)

- Drive bus (`CAREER_DRIVE_BUS_DIR`, synced by Drive for Desktop): `inbox/`, `outbox/`, `ledger/jobs.json`,
  `ledger/applications.jsonl`, `ledger/cv_requests/`, `ledger/cv_packs/`, `ledger/search_hits.json`, `ledger/link_intake.json`.
- `principal-architect-hub/scripts/drive_bus.py` polls `inbox/` every 5 s (Spark task format, `schema_version: 1`).
- `dashboard/career_link.start_link` (exposed as loopback `POST /api/career/link`) is how a URL becomes a ledger job.
- Replies are stamped on job rows (`reply_seen_at_utc`, `reply_from`, `reply_subject`); no interview/reject signal exists.
- `hub/telegram_listener.py` long-polls the Hub bot → the intake bot must be a **new** bot (409 otherwise).
- `cloud_node/` is a Cloud Run scaffold (not deployed); not used by v2.
- The sandbox sidecar writes `orchestration.db` only; it is not part of this project.

### 4.2 Build order

`G0 → P2 → P1 → P4(local) → P5 → P3`. Inside P2, the exporter design (P2-07) precedes the writer (P2-03).

### 4.3 Risks

| ID | Risk | Status / fallback |
|---|---|---|
| K1–K3 | Drive webhook domain rules, noisy `changes.watch`, channel expiry | **Removed** (D-4: local watcher on the synced folder) |
| K4 | e2-micro 1 GB RAM | listener only; 2 GB swap; `MemoryMax=300M` |
| K5 | PC off | pull model; Telegram keeps updates 24 h, Pub/Sub 7 d |
| K6 | streaming buffer blocks DML | **Removed**: batch load jobs, append-only, view dedupe |
| K7 | Hebrew OCR quality | P5 compares local VLM, Document AI+LLM, Gemini direct |
| K8 | SA access to Drive | **Removed** (no Drive API) |
| K9 | VM external IPv4 is billable (~$3.65/mo) | budgeted; IPv6-only variant to verify (Q1) |
| K10 | Local 7B models write poor Hebrew | fixtures are template-based; LLM only classifies |
| K11 | Multiple writers to `jobs.json` today (Hub + Spark) | exporter is read-only + snapshot-diff; never writes it |

## 5. Contracts

**Task v1** — `contracts/task_v1.schema.json`, `jobs_pipeline/contracts.py`. Changes vs v1 draft (D-5): `payload.sha256`
and `payload.mime` added; `dedupe_key = sha256(source|url|<normalized url>)` for links and `sha256(source|sha256|<content hash>)`
for files (rename ≠ new task); `additionalProperties: false`; https only.

**BigQuery `jobs.events`** (append-only, `PARTITION BY DATE(ts)`, cluster `event_type,title_family`): `event_id, job_id,
event_type, ts, cv_version, title_family, keywords, source_type, payload JSON, exported_at`. Written only by batch load
jobs from NDJSON. Views: `events_dedup`, `jobs_latest`, `days_to_reply`, `response_rate_by_title_family`,
`response_rate_by_cv_version` (with `n`, Wilson 95%, `insufficient_n` when n < 30). Taxonomy + allow-list: `P2_TAXONOMY.md`.

**Pub/Sub:** topics `tasks`, `tasks-dlq`, `results`; pull sub `tasks-local` (ack 60 s, retention 7 d, retry 10–600 s,
DLQ after 5); `tasks-dlq-hold` for inspection.

## 6. Task ledger

See `TASKS.md` (IDs `GC-*`). Removed from v1: P4-02, P4-04, P4-08 (cloud Drive webhook), P1-03 (Tailscale; IAP covers admin).
Added: P4-L1 local watcher, G0-7 day-80 decision, P3-00 Spark integration (read-only evidence check).

## 7–8. Workflow and reporting

Unchanged from v1: Inspect → Plan (≤ 15 lines) → APPROVE → Build (tests first, `DRY_RUN=1`) → Verify → Report.
`TASKS.md` one row per task; `STATUS.md` overwritten per session (≤ 60 lines); `DECISIONS.md` append-only;
REPORT block at the end of each session; Claude questions also in `CLAUDE_HANDOFF.md`.

## 9. Stop conditions

No-touch list, secrets or RED data involved; any new writer to an existing store or an inbound port; a finding that
contradicts §4.3; expected cost > $5 or a new paid service; a contract change not in `DECISIONS.md`; two unexplained
consecutive test failures; any payment/billing surface (Noam only).

## 10. External facts to re-verify when implementing

- Free Trial $300 / ~90 days; resources stop unless upgraded; budget alerts notify, they do not cap spend.
- Always Free: one e2-micro in us-west1/us-central1/us-east1 + 30 GB pd-standard; external IPv4 billed separately.
- BigQuery: batch load jobs free; ~1 TB query + 10 GB storage free per month. Streaming `row_ids` dedupe is best-effort only.
- Pub/Sub ~10 GB/month free. Telegram keeps undelivered updates ~24 h.
- Document AI Enterprise OCR ~$1.50 / 1,000 pages. Vertex AI Search Standard ~$1.50 / 1,000 queries after free quota.
