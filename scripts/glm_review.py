"""Advisory GLM review of the plan through the Hub pipeline (architect glm-5.3 → Flash QA → final review).

Usage: python scripts/glm_review.py   (run with the Hub venv). Prints verdicts and cost only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HUB = Path(os.environ.get("HUB_ROOT", REPO.parents[1] / "principal-architect-hub"))
sys.path.insert(0, str(HUB))
os.chdir(HUB)

from hub.glm_pipeline import run_pipeline  # noqa: E402

BRIEF = (
    "job-hub-cloud: GCP free-tier job-search pipeline, cap 10 USD/month, importance high. "
    "Telegram intake bot long-polls on e2-micro VM, publishes task v1 to Pub/Sub; local PC pulls (outbound only), "
    "dedupes by sha256 key in own sqlite, acks after success, DLQ after 5. Links go to Hub loopback API, never write Hub ledger. "
    "Drive intake is a local watcher on synced folder. Exporter reads ledger read-only, derives events with deterministic ids, "
    "allow-list fields, BigQuery batch load jobs, views dedupe + Wilson intervals. OCR eval: local VLM vs DocAI+LLM vs Gemini. "
    "Success: no inbound ports, no secrets in repo, no RED data to cloud, exactly-once effects. Failure: PII export, double processing, spend over cap."
)
ARTIFACT = (
    "Controls: sanitize.py strips bidi/zero-width, flags EN/HE injection, redacts PII in logs. scan_secrets pre-commit blocks tokens, SA keys, .env, RED paths. "
    "Schema additionalProperties false, https only, dedupe_key recomputed on validate. Scripts DRY_RUN=1 default; SA per component; IAP SSH only; no key files. "
    "Open: VM external IPv4 ~3.65/mo; owner CV is AMBER local-only; interview/reject from manual CSV."
)


def main() -> int:
    out = run_pipeline(BRIEF, artifact=ARTIFACT, force_architect=True)
    keep = {k: out.get(k) for k in ("ok", "stage", "live", "score", "est_usd")}
    keep["plan"] = {k: (out.get("plan") or {}).get(k) for k in ("importance", "work_size", "success", "failure")}
    keep["flash"] = {k: (out.get("flash") or {}).get(k) for k in ("verdict", "summary", "failures")}
    keep["review"] = {k: (out.get("review") or {}).get(k) for k in ("verdict", "corrections", "summary")} if out.get("review") else None
    print(json.dumps(keep, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
