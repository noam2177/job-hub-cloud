"""CLI: python -m local.watcher [--once]"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from local.dispatcher import Dispatcher, LocalStore, default_handlers
from local.watcher.watcher import SeenState, run_once


def main() -> None:
    if os.environ.get("JOBHUB_WATCHER") != "1":
        raise SystemExit("JOBHUB_WATCHER=1 required")
    parser = argparse.ArgumentParser(prog="local.watcher")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    state_dir = Path(os.environ.get("JOBHUB_STATE_DIR", "state"))
    store = LocalStore(state_dir / "jobhub_local.db")
    dispatcher = Dispatcher(store, default_handlers())
    seen = SeenState()
    if args.once:
        run_once(dispatcher, seen)
        return
    while True:
        run_once(dispatcher, seen)
        time.sleep(5)


if __name__ == "__main__":
    main()
