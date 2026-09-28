"""Pre-commit guard: secrets and RED paths. Exit 1 blocks the commit.

Usage: python scripts/scan_secrets.py FILE [FILE ...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "telegram_bot_token": re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    "gcp_service_account_key": re.compile(r'"private_key"\s*:\s*"-----BEGIN'),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "google_oauth_secret": re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{28}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
    "generic_assignment": re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]([^'\"\s<>]{16,})['\"]"
    ),
}

RED_PATH_MARKERS = (
    "real_inputs",
    "real_ground_truth",
    "real_benchmark_results",
    "sagole",
    "secure_data_939",
    "statedb.db",
)

BLOCKED_NAMES = re.compile(r"(^|/)\.env(\.(?!example$)[^/]+)?$")
PLACEHOLDER = re.compile(r"(?i)(example|placeholder|change_?me|dummy|fake|xxx+|<[^>]+>)")
ALLOW_MARKER = "secret-scan: allow"


def scan_text(text: str) -> list[str]:
    hits: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            match = pattern.search(line)
            if not match:
                continue
            if name == "generic_assignment" and PLACEHOLDER.search(match.group(2)):
                continue
            hits.append(f"{lineno}:{name}")
    return hits


def scan_path(path: Path) -> list[str]:
    posix = path.as_posix().lower()
    if any(marker in posix for marker in RED_PATH_MARKERS):
        return ["red_path"]
    if BLOCKED_NAMES.search(posix):
        return ["env_file"]
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    return scan_text(text)


def main(argv: list[str]) -> int:
    failed = False
    for raw in argv:
        hits = scan_path(Path(raw))
        if hits:
            failed = True
            print(f"BLOCKED {raw}: {', '.join(hits)}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
