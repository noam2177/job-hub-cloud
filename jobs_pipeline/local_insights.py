from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from jobs_pipeline.events import classify_title, load_jobs
from jobs_pipeline.title_family import TITLE_FAMILIES

APPLIED = frozenset({"submitted", "sent", "email_sent", "form_submitted"})


def aggregate_ledger(jobs_path: Path) -> dict[str, Any]:
    jobs = load_jobs(jobs_path)
    by_status: Counter[str] = Counter()
    by_family: Counter[str] = Counter()
    by_origin: Counter[str] = Counter()
    applied = 0
    with_reply = 0
    for job in jobs:
        status = str(job.get("status") or "unknown").lower()
        by_status[status] += 1
        if status in APPLIED:
            applied += 1
        if job.get("reply_seen_at_utc"):
            with_reply += 1
        title = str(job.get("title") or "")
        family = classify_title(title)
        if family not in TITLE_FAMILIES:
            family = "other"
        by_family[family] += 1
        origin = str(job.get("origin") or "unknown")
        by_origin[origin] += 1
    return {
        "jobs_total": len(jobs),
        "applied_count": applied,
        "reply_count": with_reply,
        "apply_rate": round(applied / len(jobs), 4) if jobs else 0.0,
        "reply_rate_of_applied": round(with_reply / applied, 4) if applied else 0.0,
        "by_status": dict(by_status),
        "by_title_family": dict(by_family),
        "by_origin": dict(by_origin),
    }


def maybe_ollama_summary(stats: dict[str, Any], *, max_tokens: int = 600) -> dict[str, Any]:
    """Optional Hebrew narrative via Hub local_infer (Ollama). Skips if Hub/Ollama unavailable."""
    if os.environ.get("JOBHUB_SKIP_OLLAMA", "").strip() in {"1", "true", "yes"}:
        return {"ok": False, "skipped": True, "reason": "JOBHUB_SKIP_OLLAMA"}
    repo = Path(__file__).resolve().parents[1]
    hub = Path(os.environ.get("HUB_ROOT", repo.parent / "principal-architect-hub"))
    if not hub.is_dir():
        return {"ok": False, "skipped": True, "reason": "HUB_ROOT not found"}
    import sys

    sys.path.insert(0, str(hub))
    try:
        from hub.local_infer import local_chat
    except ImportError:
        return {"ok": False, "skipped": True, "reason": "local_infer import failed"}

    prompt = (
        "סכם ב-3 משפטים בעברית מגמות בחיפוש עבודה מהנתונים הבאים (מספרים בלבד, בלי PII). "
        f"JSON: {json.dumps(stats, ensure_ascii=False)}"
    )
    out = local_chat(prompt, model=os.environ.get("OLLAMA_HEBREW_MODEL", "qwen2.5:7b"), max_tokens=max_tokens, timeout=120)
    if not out.get("ok"):
        return {"ok": False, "error": out.get("error")}
    return {"ok": True, "model": out.get("model"), "summary_he": (out.get("content") or "").strip()}
