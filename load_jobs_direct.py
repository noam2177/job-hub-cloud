"""Deprecated one-off loader. Use scripts/incremental_sync_to_bq.py (WRITE_APPEND, dedupe via views)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "incremental_sync_to_bq.py"


def main() -> None:
    print("load_jobs_direct.py is deprecated; running incremental_sync_to_bq.py --apply")
    cmd = [sys.executable, str(SCRIPT), "--apply"]
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == "__main__":
    main()
