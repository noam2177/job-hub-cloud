from __future__ import annotations

from pathlib import Path

from local.watcher.state_io import load_seen, save_seen
from local.watcher.watcher import SeenState


def test_seen_state_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "watcher_seen.json"
    seen = SeenState(pending={"/x/a.png": (100, 1.5)})
    save_seen(p, seen)
    loaded = load_seen(p)
    assert loaded.pending["/x/a.png"] == (100, 1.5)
