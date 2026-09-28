# P5 — Job ads as images

Queue input: `state/ocr_queue/<sha256>.json` from the local dispatcher. Output: `state/ads/<sha256>.json`, low-confidence
items also in `state/review_queue/`, and one allow-listed `found` event (`source_type=image`, deterministic `event_id`)
for the BigQuery exporter. All state stays local; nothing is written back into the Drive bus.

## Paths compared (`scripts/p5_eval.py`)

| Path | Steps | Est. cost / ad | Data leaves PC? |
|---|---|---|---|
| `direct_local` | Ollama `qwen3-vl:8b-instruct` image → JSON | $0 | no |
| `ocr_llm_local` | Ollama VLM transcription → `qwen2.5:7b` structuring | $0 | no |
| `ocr_llm_gcp` | Document AI Enterprise OCR (~$0.0015/page) → Gemini Flash | ~$0.002 | yes (public ad only) |
| `direct_gcp` | Gemini Flash multimodal | ~$0.0005 | yes (public ad only) |

## Decision rule
On 20 labeled ads: adopt the **cheapest** path with overall field accuracy ≥ 90% and Wilson 95% lower bound ≥ 80%.
If no local path qualifies, run GCP paths (needs `JOBHUB_ALLOW_GCP_EVAL=1`, total ≈ $0.05). If none qualifies,
keep the review queue as the default and re-evaluate.

## Safeguards
- OCR/model text passes `sanitize.clean`; injection hits force human review.
- Ad text cannot close the prompt's data block (markers neutralized).
- Model output is validated by pydantic; invalid contacts are salvaged or dropped, not fatal.
- Network failures raise (retry later); validation failures go to review.
- Only public job ads go to GCP paths.
