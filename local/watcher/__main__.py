"""CLI: python -m local.watcher [--once]"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from local.dispatcher import Dispatcher, LocalStore, default_handlers
from local.watcher.state_io import load_seen, save_seen
from local.watcher.watcher import run_once


def main() -> None:
    if os.environ.get("JOBHUB_WATCHER") != "1":
        raise SystemExit("JOBHUB_WATCHER=1 required")
    parser = argparse.ArgumentParser(prog="local.watcher")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between scans")
    args = parser.parse_args()
    state_dir = Path(os.environ.get("JOBHUB_STATE_DIR", "state"))
    seen_path = state_dir / "watcher_seen.json"
    store = LocalStore(state_dir / "jobhub_local.db")
    dispatcher = Dispatcher(store, default_handlers())
    seen = load_seen(seen_path)
    if args.once:
        run_once(dispatcher, seen)
        save_seen(seen_path, seen)
        return
    while True:
        run_once(dispatcher, seen)
        save_seen(seen_path, seen)
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    main()
