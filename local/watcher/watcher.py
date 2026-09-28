"""Scan Drive-synced inbox for stable files and build drive_file tasks."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jobs_pipeline import contracts

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".txt"}
MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}
SKIP_DIRS = {"_failed", "_done"}


@dataclass
class SeenState:
    """Tracks size+mtime between scans for stability."""

    pending: dict[str, tuple[int, float]] = field(default_factory=dict)


def _is_temp(name: str) -> bool:
    lower = name.lower()
    if lower == "desktop.ini":
        return True
    if name.startswith("~$"):
        return True
    if lower.endswith(".tmp") or lower.endswith(".partial"):
        return True
    return False


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _relative_file_id(bus_root: Path, path: Path) -> str:
    rel = path.relative_to(bus_root)
    return rel.as_posix()


def scan(root: Path, seen_state: SeenState, bus_root: Path | None = None) -> list[dict[str, Any]]:
    bus = bus_root or root.parent
    inbox = root
    tasks: list[dict[str, Any]] = []
    if not inbox.is_dir():
        return tasks

    current_files: dict[str, Path] = {}
    for path in inbox.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(inbox).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if _is_temp(path.name):
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        key = str(path)
        current_files[key] = path

    stable_keys: list[str] = []
    for key, path in current_files.items():
        stat = path.stat()
        sig = (stat.st_size, stat.st_mtime)
        prev = seen_state.pending.get(key)
        if prev == sig:
            stable_keys.append(key)
        else:
            seen_state.pending[key] = sig

    for key in list(seen_state.pending):
        if key not in current_files:
            del seen_state.pending[key]

    for key in stable_keys:
        path = current_files[key]
        sha = _sha256_file(path)
        mime = MIME_BY_SUFFIX.get(path.suffix.lower())
        file_id = _relative_file_id(bus, path)
        task = contracts.build_task(
            "drive_file",
            "drive",
            file_id=file_id,
            version=sha[:16],
            sha256=sha,
            mime=mime,
        )
        tasks.append(task)
        del seen_state.pending[key]

    return tasks


def move_to_done(path: Path, inbox_root: Path) -> None:
    rel = path.relative_to(inbox_root)
    dest = inbox_root / "_done" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    path.replace(dest)


def move_to_failed(path: Path, inbox_root: Path) -> None:
    rel = path.relative_to(inbox_root)
    dest = inbox_root / "_failed" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    path.replace(dest)


def inbox_path() -> Path:
    bus = os.environ.get("CAREER_DRIVE_BUS_DIR", "")
    if not bus:
        raise RuntimeError("CAREER_DRIVE_BUS_DIR not set")
    return Path(bus) / "inbox_raw"


def run_once(
    dispatcher: Any,
    seen: SeenState | None = None,
    inbox: Path | None = None,
) -> int:
    root = inbox or inbox_path()
    bus = root.parent
    state = seen or SeenState()
    scan(root, state, bus_root=bus)
    tasks = scan(root, state, bus_root=bus)
    count = 0
    for task in tasks:
        outcome = dispatcher.handle(task)
        file_path = bus / task["payload"]["file_id"]
        if outcome.ack:
            if file_path.is_file():
                move_to_done(file_path, root)
            count += 1
        else:
            attempts = dispatcher.store.bump_attempts(task["dedupe_key"])
            if attempts >= 5 and file_path.is_file():
                dispatcher.store.record(task, "failed", "max_attempts")
                move_to_failed(file_path, root)
    return count
