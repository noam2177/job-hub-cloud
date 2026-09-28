from __future__ import annotations

from pathlib import Path

from jobs_pipeline import contracts
from local.dispatcher import Dispatcher, LocalStore, Outcome, default_handlers
from local.puller.puller import process_batch


class FakeSub:
    def __init__(self, messages: list[tuple[str, bytes]]) -> None:
        self._messages = list(messages)
        self.acked: list[str] = []
        self.nacked: list[str] = []

    def pull(self, max_messages: int) -> list:
        from local.puller.puller import PulledMessage

        batch = self._messages[:max_messages]
        self._messages = self._messages[max_messages:]
        return [PulledMessage(ack_id=a, data=d) for a, d in batch]

    def acknowledge(self, ack_ids: list[str]) -> None:
        self.acked.extend(ack_ids)

    def modify_ack_deadline(self, ack_ids: list[str], seconds: int) -> None:
        self.nacked.extend(ack_ids)


def test_task_invalid_acked_rejected(tmp_path: Path) -> None:
    sub = FakeSub([("a1", b"not-json")])
    store = LocalStore(tmp_path / "jobhub_local.db")
    disp = Dispatcher(store, default_handlers())
    stats = process_batch(sub, disp)
    assert sub.acked == ["a1"]
    assert stats.rejected == 1


def test_handler_raises_then_once(tmp_path: Path) -> None:
    calls = 0
    task = contracts.build_task("telegram_job_link", "telegram", url="https://jobs.example.com/r")

    class Flaky:
        def handle(self, t: dict) -> Outcome:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("boom")
            return Outcome(ack=True, status="done")

    store = LocalStore(tmp_path / "jobhub_local.db")
    disp = Dispatcher(store, {"telegram_job_link": Flaky()})
    sub = FakeSub([("m1", contracts.encode(task)), ("m2", contracts.encode(task))])
    process_batch(sub, disp)
    assert sub.nacked == ["m1"]
    process_batch(sub, disp)
    assert sub.acked == ["m2"]
    assert calls == 2
    assert store.terminal_status(task["dedupe_key"]) == "done"
