"""Untrusted-input gate (R4). Runs before any LLM and before any log line.

Rules mirror principal-architect-hub/hub/skills/prompt_injection_scan.py plus Hebrew
phrases, bidi/zero-width smuggling, and PII redaction. Never returns matched text.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MAX_CHARS = 4000

_INVISIBLE = re.compile("[\u200b-\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"(?i)(ignore (all )?(previous|prior|above) (instructions|rules)|disregard (your )?(rules|policy)"
            r"|jailbreak|\bDAN\b|developer mode|system prompt)"
        ),
    ),
    ("instruction_override_he", re.compile(r"(התעלם|תתעלם|שכח|תשכח)\s+(מכל\s+)?(ה)?(הוראות|כללים|ההנחיות)")),
    ("role_hijack", re.compile(r"(?i)(you are now|new (system )?persona|pretend you have no (rules|limits)|act as (root|admin))")),
    ("tool_coercion", re.compile(r"(?i)(system\.run|shell\s*=\s*true|docker\.sock|/bin/sh|subprocess|os\.system|curl\s+-)")),
    ("path_exfil", re.compile(r"(?i)(desktop[/\\]sagole|sagole[/\\]939|real_inputs|secure_data_939|statedb\.db|\.env\b)")),
    ("encoding_smuggle", re.compile(r"(?i)(base64.{0,20}ignore|<script|\\x00)")),
    ("send_action", re.compile(r"(?i)(send (this|the) (cv|email|application)|submit (the )?application|שלח (את )?(הקורות|המייל|המועמדות))")),
)

_PII: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("il_id", re.compile(r"(?<!\d)\d{9}(?!\d)")),
    ("phone", re.compile(r"(?<![\d])(?:\+972[-\s]?|0)(?:[23489]|5\d)[-\s]?\d{3}[-\s]?\d{4}(?!\d)")),
    ("card", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
)


@dataclass
class Sanitized:
    text: str
    hits: list[str] = field(default_factory=list)
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return not self.hits


def clean(raw: str | None, *, max_chars: int = MAX_CHARS) -> Sanitized:
    text = unicodedata.normalize("NFKC", str(raw or ""))
    stripped = _INVISIBLE.sub("", text)
    hits = ["invisible_chars"] if len(stripped) != len(text) else []
    truncated = len(stripped) > max_chars
    stripped = stripped[:max_chars]
    hits.extend(code for code, pattern in _RULES if pattern.search(stripped))
    return Sanitized(text=stripped, hits=hits, truncated=truncated)


def redact_pii(text: str) -> str:
    out = str(text or "")
    for name, pattern in _PII:
        out = pattern.sub(f"<{name}>", out)
    return out


def log_safe(text: str, *, limit: int = 120) -> str:
    """For log lines: no PII, no control chars, bounded."""
    return redact_pii(_INVISIBLE.sub("", str(text or "")))[:limit]
