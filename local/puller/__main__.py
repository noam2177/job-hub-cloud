"""CLI: python -m local.puller [--once] [--dry-run]"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from local.dispatcher import Dispatcher, LocalStore, default_handlers
from local.puller.puller import PubSubSubscriber, run_loop


def main() -> None:
    parser = argparse.ArgumentParser(prog="local.puller")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run or os.environ.get("JOBHUB_DRY_RUN", "1") == "1"
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT", "")
    subscription = os.environ.get("JOBHUB_PUBSUB_SUBSCRIPTION", "tasks-local")
    state = Path(os.environ.get("JOBHUB_STATE_DIR", "state"))
    db = state / "jobhub_local.db"
    store = LocalStore(db)
    dispatcher = Dispatcher(store, default_handlers())
    subscriber = PubSubSubscriber(project, subscription)
    run_loop(subscriber, dispatcher, once=args.once, dry_run=dry)


if __name__ == "__main__":
    main()
