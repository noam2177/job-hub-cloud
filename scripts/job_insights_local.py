#!/usr/bin/env python3
"""Local ledger analytics (no cloud). Optional Ollama summary via OpenClaw Hub."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobs_pipeline.incremental_sync import default_ledger_path
from jobs_pipeline.local_insights import aggregate_ledger, maybe_ollama_summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Aggregate career ledger stats locally")
    parser.add_argument("--jobs", default=None, help="Path to jobs.json")
    parser.add_argument("--ollama", action="store_true", help="Add short Hebrew summary via local Ollama (Hub)")
    args = parser.parse_args(argv)

    jobs_path = Path(args.jobs) if args.jobs else default_ledger_path()
    if not jobs_path.is_file():
        print(json.dumps({"ok": False, "error": f"ledger not found: {jobs_path}"}, ensure_ascii=False))
        sys.exit(1)

    report: dict = {"ok": True, "ledger": str(jobs_path), "stats": aggregate_ledger(jobs_path)}
    if args.ollama:
        report["ollama"] = maybe_ollama_summary(report["stats"])
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
