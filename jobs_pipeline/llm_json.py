"""Shared JSON extraction from LLM replies."""
from __future__ import annotations

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)


def parse_json_from_llm(text: str) -> dict:
    raw = (text or "").strip()
    match = _FENCE.search(raw)
    if match:
        raw = match.group(1).strip()
    if not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("LLM JSON must be an object")
    return data
