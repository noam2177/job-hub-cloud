# COST LEDGER

Cap: **$10 / month**. Any single action expected > $5 needs Noam's explicit approval.
Budget and payment settings are handled by Noam in the Console only.

## Trial

| Item | Value |
|---|---|
| Credit amount | **₪891** (per Noam Console 2026-09-30) |
| Credit start date | _record from Console if not already noted_ |
| Credit expiry date | **2026-12-04** (per Noam Console 2026-09-30) |
| Last day to create resources (expiry − 10 d) | **2026-11-24** |
| Day-80 go/no-go (upgrade or tear down) | _set calendar from credit start + 80 d_ |
| Budget alerts 50 / 90 / 100% created | **yes** — Noam verified in Console 2026-09-30 |

## Expected monthly run cost

| Component | Expected $/month | Note |
|---|---|---|
| e2-micro VM + 30 GB pd-standard | 0 | Always Free (us-central1) |
| VM external IPv4 | ~3.65 | not Always Free; IPv6-only variant may remove it (unverified) |
| Pub/Sub | 0 | far under 10 GB |
| Secret Manager | ~0.06 | 1 secret version + access ops |
| BigQuery | 0 | load jobs free; tiny storage/queries |
| Looker Studio | 0 | |
| Document AI OCR (P5 eval, 20 ads) | ~0.03 | one-off; Vision free tier is separate from P5 code path |
| Gemini Flash (P5 eval) | < 0.05 | one-off |
| GLM reviews | < 0.20 | Hub spend ledger |
| **Total steady state** | **~3.7** | |

## Log

| Date | Action | Who | Cost | Evidence |
|---|---|---|---|---|
| 2026-09-28 | Repo, code, tests, local Ollama runs | Cursor | $0 cloud | `STATUS.md` |
| 2026-09-30 | $10 budget + alerts 50/90/100% | Noam | $0 | Console |
| 2026-09-30 | Trial ledger: ₪891, expiry 2026-12-04 | Noam | $0 | this table |
