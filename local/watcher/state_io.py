from __future__ import annotations

import json
from pathlib import Path

from local.watcher.watcher import SeenState


def load_seen(path: Path) -> SeenState:
    if not path.is_file():
        return SeenState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return SeenState()
    pending = data.get("pending") if isinstance(data, dict) else None
    if not isinstance(pending, dict):
        return SeenState()
    out: dict[str, tuple[int, float]] = {}
    for k, v in pending.items():
        if isinstance(v, list) and len(v) == 2:
            out[str(k)] = (int(v[0]), float(v[1]))
    return SeenState(pending=out)


def save_seen(path: Path, seen: SeenState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pending": {k: [a, b] for k, (a, b) in seen.pending.items()}}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
