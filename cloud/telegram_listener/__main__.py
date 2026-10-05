"""CLI entry for telegram listener on GCE VM."""
from __future__ import annotations

import os
import signal
import threading
from pathlib import Path

from cloud.telegram_listener.listener import (
    FileOffsetStore,
    PubSubPublisher,
    UrllibTelegramApi,
    _resolve_token,
    run,
)


def main() -> None:
    state = Path(os.environ.get("JOBHUB_STATE_DIR", "/var/lib/jobhub"))
    allowed_raw = os.environ.get("TELEGRAM_INTAKE_ALLOWED_CHAT_IDS") or os.environ.get(
        "TELEGRAM_ALLOWED_CHAT_IDS", ""
    )
    allowed = {int(x.strip()) for x in allowed_raw.split(",") if x.strip()}
    if not allowed:
        raise SystemExit("TELEGRAM_ALLOWED_CHAT_IDS required")
    token = _resolve_token()
    api = UrllibTelegramApi(token)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT", "")
    topic = os.environ.get("JOBHUB_PUBSUB_TOPIC", "tasks")
    publisher = PubSubPublisher(project, topic)
    offset_store = FileOffsetStore(state / "telegram_offset.txt")
    stop = threading.Event()

    def _stop(*_args: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    run(api, publisher, offset_store, allowed, stop)


if __name__ == "__main__":
    main()
