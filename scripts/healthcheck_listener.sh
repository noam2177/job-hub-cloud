#!/usr/bin/env bash
# Runs as root from jobhub-healthcheck.service: restarting a unit needs root.
set -uo pipefail
STATE_DIR="${JOBHUB_STATE_DIR:-/var/lib/jobhub}"
HB="${STATE_DIR}/heartbeat_listener.json"
export HB MAX_AGE="${MAX_AGE:-180}"

if python3 - <<'PY'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

try:
    data = json.loads(Path(os.environ["HB"]).read_text())
    ts = datetime.fromisoformat(data["utc"].replace("Z", "+00:00"))
except (OSError, ValueError, KeyError):
    sys.exit(1)
age = (datetime.now(timezone.utc) - ts).total_seconds()
sys.exit(0 if age <= int(os.environ["MAX_AGE"]) else 1)
PY
then
  exit 0
fi
echo "listener heartbeat stale or missing; restarting"
systemctl restart jobhub-telegram.service
