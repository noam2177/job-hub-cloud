# COST LEDGER

Cap: **$10 / month**. Any single action expected > $5 needs Noam's explicit approval.
Budget and payment settings are handled by Noam in the Console only.

## Trial

| Item | Value |
|---|---|
| Credit amount | $300 (verify in Console) |
| Credit start date | _Noam fills_ |
| Credit expiry date | _Noam fills_ |
| Last day to create resources (expiry − 10 d) | _computed_ |
| Day-80 go/no-go (upgrade or tear down) | _computed_ |
| Budget alerts 50 / 90 / 100% created | _yes/no + screenshot ref_ |

## Expected monthly run cost

| Component | Expected $/month | Note |
|---|---|---|
| e2-micro VM + 30 GB pd-standard | 0 | Always Free (us-central1) |
| VM external IPv4 | ~3.65 | not Always Free; IPv6-only variant may remove it (unverified) |
| Pub/Sub | 0 | far under 10 GB |
| Secret Manager | ~0.06 | 1 secret version + access ops |
| BigQuery | 0 | load jobs free; tiny storage/queries |
| Looker Studio | 0 | |
| Document AI OCR (P5 eval, 20 ads) | ~0.03 | one-off |
| Gemini Flash (P5 eval) | < 0.05 | one-off |
| GLM reviews | < 0.20 | Hub spend ledger |
| **Total steady state** | **~3.7** | |

## Log

| Date | Action | Who | Cost | Evidence |
|---|---|---|---|---|
| 2026-09-28 | Repo, code, tests, local Ollama runs | Cursor | $0 cloud | `STATUS.md` |
