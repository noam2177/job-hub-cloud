"""Pull tasks from Pub/Sub and dispatch locally."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from jobs_pipeline import contracts
from jobs_pipeline.contracts import TaskInvalid
from jobs_pipeline.sanitize import log_safe
from local.dispatcher import Dispatcher, Outcome


@dataclass
class PulledMessage:
    ack_id: str
    data: bytes
    delivery_attempt: int = 1


class Subscriber(Protocol):
    def pull(self, max_messages: int) -> list[PulledMessage]: ...

    def acknowledge(self, ack_ids: list[str]) -> None: ...

    def modify_ack_deadline(self, ack_ids: list[str], seconds: int) -> None: ...


@dataclass
class PullerStats:
    pulled: int = 0
    acked: int = 0
    nacked: int = 0
    rejected: int = 0


class PubSubSubscriber:
    def __init__(self, project_id: str, subscription_id: str) -> None:
        self._project_id = project_id
        self._subscription_id = subscription_id
        self._client: Any = None

    def _sub_path(self) -> str:
        if self._client is None:
            from google.cloud import pubsub_v1  # lazy

            self._client = pubsub_v1.SubscriberClient()
        return self._client.subscription_path(self._project_id, self._subscription_id)

    def pull(self, max_messages: int) -> list[PulledMessage]:
        client = self._client
        if client is None:
            from google.cloud import pubsub_v1  # lazy

            client = pubsub_v1.SubscriberClient()
            self._client = client
        response = client.pull(
            request={"subscription": self._sub_path(), "max_messages": max_messages}
        )
        out: list[PulledMessage] = []
        for msg in response.received_messages:
            attempt = 1
            if msg.message and getattr(msg.message, "delivery_attempt", None):
                attempt = int(msg.message.delivery_attempt)
            out.append(
                PulledMessage(
                    ack_id=msg.ack_id,
                    data=msg.message.data,
                    delivery_attempt=attempt,
                )
            )
        return out

    def acknowledge(self, ack_ids: list[str]) -> None:
        if not ack_ids:
            return
        sub = self._sub_path()
        self._client.acknowledge(request={"subscription": sub, "ack_ids": ack_ids})

    def modify_ack_deadline(self, ack_ids: list[str], seconds: int) -> None:
        if not ack_ids:
            return
        if self._client is None:
            from google.cloud import pubsub_v1  # lazy

            self._client = pubsub_v1.SubscriberClient()
        self._client.modify_ack_deadline(
            request={
                "subscription": self._sub_path(),
                "ack_ids": ack_ids,
                "ack_deadline_seconds": seconds,
            }
        )


def heartbeat_path() -> Path:
    base = Path(os.environ.get("JOBHUB_STATE_DIR", "state"))
    return base / "heartbeat_puller.json"


def write_heartbeat(stats: PullerStats) -> None:
    path = heartbeat_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "utc": contracts.utc_now(),
        "pulled": stats.pulled,
        "acked": stats.acked,
        "nacked": stats.nacked,
        "rejected": stats.rejected,
    }
    path.write_text(json.dumps(body), encoding="utf-8")


def process_batch(
    subscriber: Subscriber,
    dispatcher: Dispatcher,
    *,
    max_messages: int = 10,
    dry_run: bool = False,
    stats: PullerStats | None = None,
) -> PullerStats:
    st = stats or PullerStats()
    messages = subscriber.pull(max_messages)
    st.pulled += len(messages)
    for msg in messages:
        try:
            task = contracts.decode(msg.data)
        except TaskInvalid as exc:
            print(log_safe("task_invalid %s" % exc))
            if not dry_run:
                subscriber.acknowledge([msg.ack_id])
            st.acked += 1
            st.rejected += 1
            continue

        if dry_run:
            print(log_safe("dry_run task=%s" % task["task_id"]))
            continue

        outcome = dispatcher.handle(task)
        if outcome.ack:
            subscriber.acknowledge([msg.ack_id])
            st.acked += 1
            if outcome.status == "rejected":
                st.rejected += 1
        else:
            subscriber.modify_ack_deadline([msg.ack_id], 0)
            st.nacked += 1
    write_heartbeat(st)
    return st


def run_loop(
    subscriber: Subscriber,
    dispatcher: Dispatcher,
    *,
    once: bool = False,
    dry_run: bool = False,
    sleep_seconds: float = 2.0,
) -> PullerStats:
    stats = PullerStats()
    while True:
        stats = process_batch(subscriber, dispatcher, dry_run=dry_run, stats=stats)
        if once:
            break
        if stats.pulled == 0:
            time.sleep(sleep_seconds)
    return stats
