"""Deprecated. Use: python scripts/incremental_sync_to_bq.py --check-bq | --apply"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("incremental_sync_safe.py is deprecated (removed WRITE_TRUNCATE path).", file=sys.stderr)
    cmd = [sys.executable, str(ROOT / "scripts" / "incremental_sync_to_bq.py"), "--check-bq"]
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == "__main__":
    main()
