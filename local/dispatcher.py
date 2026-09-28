"""Local task dispatcher: SQLite dedupe + Hub link + file intake."""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from jobs_pipeline import contracts
from jobs_pipeline.sanitize import log_safe

TERMINAL = frozenset({"done", "rejected", "failed"})
TRANSIENT_HTTP = frozenset({408, 429})
_FORBIDDEN_DB_FRAGMENTS = ("statedb", "control_tower")


@dataclass(frozen=True)
class Outcome:
    ack: bool
    status: str


class Handler(Protocol):
    def handle(self, task: dict[str, Any]) -> Outcome: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_db_path(path: Path | str) -> Path:
    p = Path(path)
    name = p.name.lower()
    joined = str(p).lower()
    for frag in _FORBIDDEN_DB_FRAGMENTS:
        if frag in name or frag in joined:
            raise ValueError(f"refused db path containing {frag!r}")
    return p


class LocalStore:
    def __init__(self, db_path: Path | str) -> None:
        self.path = validate_db_path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS processed (
                dedupe_key TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('done','rejected','failed')),
                handled_at TEXT NOT NULL,
                detail TEXT
            );
            CREATE TABLE IF NOT EXISTS attempts (
                dedupe_key TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            );
            """
        )

    def terminal_status(self, dedupe_key: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM processed WHERE dedupe_key = ?", (dedupe_key,)
        ).fetchone()
        if row and row[0] in TERMINAL:
            return str(row[0])
        return None

    def record(self, task: dict[str, Any], status: str, detail: str | None = None) -> None:
        self._conn.execute("BEGIN")
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO processed
                (dedupe_key, task_id, type, status, handled_at, detail)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task["dedupe_key"],
                    task["task_id"],
                    task["type"],
                    status,
                    _utc_now(),
                    detail,
                ),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def bump_attempts(self, dedupe_key: str) -> int:
        self._conn.execute(
            """
            INSERT INTO attempts (dedupe_key, count) VALUES (?, 1)
            ON CONFLICT(dedupe_key) DO UPDATE SET count = count + 1
            """,
            (dedupe_key,),
        )
        row = self._conn.execute(
            "SELECT count FROM attempts WHERE dedupe_key = ?", (dedupe_key,)
        ).fetchone()
        return int(row[0]) if row else 1

    def close(self) -> None:
        self._conn.close()


def _loopback_base(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in ("127.0.0.1", "localhost"):
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


class HubLinkHandler:
    def __init__(self, base_url: str = "http://127.0.0.1:8788") -> None:
        base = _loopback_base(base_url.rstrip("/") + "/")
        if base is None:
            raise ValueError("hub base URL must be loopback")
        self._link_url = base.rstrip("/") + "/api/career/link"

    def handle(self, task: dict[str, Any]) -> Outcome:
        url = task["payload"]["url"]
        body = json.dumps({"url": url}).encode("utf-8")
        req = urllib.request.Request(
            self._link_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                status_code = resp.status
        except urllib.error.HTTPError as exc:
            if exc.code >= 500 or exc.code in TRANSIENT_HTTP:
                print(log_safe("hub_http_%s" % exc.code))
                return Outcome(ack=False, status="transient")
            raw = exc.read().decode("utf-8", errors="replace")
            status_code = exc.code
        except urllib.error.URLError as exc:
            print(log_safe("hub_connection %s" % exc.reason))
            return Outcome(ack=False, status="transient")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return Outcome(ack=False, status="transient")

        if data.get("ok"):
            return Outcome(ack=True, status="done")
        err = data.get("error_type") or ""
        if err == "bus_dir_unset" or status_code >= 500:
            return Outcome(ack=False, status="transient")
        return Outcome(ack=True, status="rejected")


class FileIntakeHandler:
    def __init__(self, queue_dir: Path | str | None = None) -> None:
        root = Path(queue_dir or os.environ.get("JOBHUB_STATE_DIR", "state"))
        self.queue_dir = root / "ocr_queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def handle(self, task: dict[str, Any]) -> Outcome:
        payload = task["payload"]
        sha = payload.get("sha256") or ""
        out = {
            "task_id": task["task_id"],
            "file_id": payload.get("file_id"),
            "sha256": sha,
            "mime": payload.get("mime"),
            "queued_at": contracts.utc_now(),
        }
        path = self.queue_dir / f"{sha}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return Outcome(ack=True, status="done")


class Dispatcher:
    def __init__(self, store: LocalStore, handlers: dict[str, Handler]) -> None:
        self.store = store
        self.handlers = handlers

    def handle(self, task: dict[str, Any]) -> Outcome:
        key = task["dedupe_key"]
        existing = self.store.terminal_status(key)
        if existing in ("done", "rejected"):
            return Outcome(ack=True, status=existing)

        handler = self.handlers.get(task["type"])
        if handler is None:
            self.store.record(task, "rejected", "unknown_type")
            return Outcome(ack=True, status="rejected")

        try:
            result = handler.handle(task)
        except Exception as exc:
            attempts = self.store.bump_attempts(key)
            print(log_safe("handler_error %s attempts=%s" % (task["type"], attempts)))
            return Outcome(ack=False, status="failed")

        if result.ack:
            self.store.record(task, result.status, None)
        return result


def default_handlers(hub_base: str | None = None) -> dict[str, Handler]:
    base = hub_base or os.environ.get("JOBHUB_HUB_URL", "http://127.0.0.1:8788")
    file_handler = FileIntakeHandler()
    return {
        "telegram_job_link": HubLinkHandler(base),
        "drive_file": file_handler,
        "ocr_job_image": file_handler,
    }
