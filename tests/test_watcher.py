from __future__ import annotations

import hashlib
from pathlib import Path

from jobs_pipeline import contracts
from local.dispatcher import Dispatcher, LocalStore, default_handlers
from local.watcher.watcher import SeenState, scan, run_once


def _stable_scan(inbox: Path, bus: Path, seen: SeenState) -> list[dict]:
    scan(inbox, seen, bus_root=bus)
    return scan(inbox, seen, bus_root=bus)


def test_ten_files_ten_tasks(tmp_path: Path) -> None:
    bus = tmp_path / "bus"
    inbox = bus / "inbox_raw"
    inbox.mkdir(parents=True)
    for i in range(10):
        (inbox / f"ad{i}.png").write_bytes(b"x" * (i + 1))
    seen = SeenState()
    tasks = _stable_scan(inbox, bus, seen)
    assert len(tasks) == 10


def test_same_content_renamed_one_dedupe(tmp_path: Path) -> None:
    bus = tmp_path / "bus"
    inbox = bus / "inbox_raw"
    inbox.mkdir(parents=True)
    data = b"same-bytes"
    (inbox / "a.png").write_bytes(data)
    seen = SeenState()
    first = _stable_scan(inbox, bus, seen)
    assert len(first) == 1
    (inbox / "a.png").unlink()
    (inbox / "b.png").write_bytes(data)
    seen2 = SeenState()
    second = _stable_scan(inbox, bus, seen2)
    assert len(second) == 1
    assert first[0]["dedupe_key"] == second[0]["dedupe_key"]
    store = LocalStore(tmp_path / "jobhub_local.db")
    disp = Dispatcher(store, default_handlers())
    run_once(disp, seen, inbox)
    run_once(disp, seen2, inbox)
    assert store.terminal_status(first[0]["dedupe_key"]) == "done"


def test_growing_file_not_picked_until_stable(tmp_path: Path) -> None:
    bus = tmp_path / "bus"
    inbox = bus / "inbox_raw"
    inbox.mkdir(parents=True)
    path = inbox / "grow.png"
    path.write_bytes(b"a")
    seen = SeenState()
    assert scan(inbox, seen, bus_root=bus) == []
    path.write_bytes(b"ab")
    assert scan(inbox, seen, bus_root=bus) == []
    tasks = scan(inbox, seen, bus_root=bus)
    assert len(tasks) == 1
