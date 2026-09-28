from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from jobs_pipeline import contracts
from local.dispatcher import Dispatcher, HubLinkHandler, LocalStore, Outcome, validate_db_path


class _HubHandler(BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *_args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length)
        if self.mode == "down":
            self.send_response(503)
            self.end_headers()
            return
        if self.mode == "rate":
            body = json.dumps({"ok": False, "error": "rate"}).encode()
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.mode == "reject":
            body = json.dumps({"ok": False, "error_type": "bad_url"}).encode()
        else:
            body = json.dumps({"ok": True, "status": "linked", "job_id": "j1"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


def _start_hub(mode: str) -> tuple[HTTPServer, str]:
    _HubHandler.mode = mode
    server = HTTPServer(("127.0.0.1", 0), _HubHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def test_db_path_statedb_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        validate_db_path(tmp_path / "statedb.db")
    with pytest.raises(ValueError):
        LocalStore(tmp_path / "control_tower_backup.db")


def test_hub_down_nacks(tmp_path: Path) -> None:
    server, base = _start_hub("down")
    store = LocalStore(tmp_path / "jobhub_local.db")
    handler = HubLinkHandler(base)
    task = contracts.build_task("telegram_job_link", "telegram", url="https://jobs.example.com/x")
    outcome = handler.handle(task)
    assert outcome.ack is False
    server.shutdown()


def test_hub_rate_limit_is_transient_not_lost(tmp_path: Path) -> None:
    server, base = _start_hub("rate")
    store = LocalStore(tmp_path / "jobhub_local.db")
    disp = Dispatcher(store, {"telegram_job_link": HubLinkHandler(base)})
    task = contracts.build_task("telegram_job_link", "telegram", url="https://jobs.example.com/x")
    out = disp.handle(task)
    assert out.ack is False
    assert store.terminal_status(task["dedupe_key"]) is None
    server.shutdown()


def test_hub_deterministic_reject_acks(tmp_path: Path) -> None:
    server, base = _start_hub("reject")
    store = LocalStore(tmp_path / "jobhub_local.db")
    disp = Dispatcher(store, {"telegram_job_link": HubLinkHandler(base)})
    task = contracts.build_task("telegram_job_link", "telegram", url="https://jobs.example.com/x")
    out = disp.handle(task)
    assert out.ack is True
    assert out.status == "rejected"
    server.shutdown()


def test_duplicate_dedupe_handler_once(tmp_path: Path) -> None:
    server, base = _start_hub("ok")
    calls = 0

    class CountingHub(HubLinkHandler):
        def handle(self, task: dict) -> Outcome:
            nonlocal calls
            calls += 1
            return super().handle(task)

    store = LocalStore(tmp_path / "jobhub_local.db")
    disp = Dispatcher(store, {"telegram_job_link": CountingHub(base)})
    task = contracts.build_task("telegram_job_link", "telegram", url="https://jobs.example.com/dup")
    assert disp.handle(task).status == "done"
    task2 = contracts.build_task("telegram_job_link", "telegram", url="https://jobs.example.com/dup")
    assert disp.handle(task2).ack is True
    assert calls == 1
    server.shutdown()
