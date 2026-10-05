#!/usr/bin/env python3
"""One-shot local audit: pytest + incremental preview + ledger insights + optional BQ DQ."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = ROOT / ".venv" / "Scripts" / "python.exe"


def _ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def run_pytest() -> dict:
    proc = _run([str(PY), "-m", "pytest", "-q"])
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "tail": proc.stdout[-500:]}


def run_incremental_check() -> dict:
    proc = _run([str(PY), str(ROOT / "scripts" / "incremental_sync_to_bq.py"), "--check-bq"])
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr[-800:]}
    return {"ok": True, "report": json.loads(proc.stdout)}


def run_insights() -> dict:
    proc = _run([str(PY), str(ROOT / "scripts" / "job_insights_local.py")])
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr[-500:]}
    return {"ok": True, "report": json.loads(proc.stdout)}


def run_dq() -> dict:
    out_path = OUT / "bq_dq_latest.json"
    proc = _run([str(PY), str(ROOT / "scripts" / "bq_dq_local.py"), "--out", str(out_path)])
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr[-800:]}
    return {"ok": True, "path": str(out_path.relative_to(ROOT)), "report": json.loads(proc.stdout)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = {
        "generated_at": _ts(),
        "repo": str(ROOT),
        "pytest": run_pytest(),
        "incremental_check_bq": run_incremental_check(),
        "ledger_insights": run_insights(),
        "bq_dq": run_dq(),
    }
    audit["ok"] = all(audit[k].get("ok") for k in ("pytest", "incremental_check_bq", "ledger_insights", "bq_dq"))

    paths = {
        "audit": OUT / "audit_latest.json",
        "p2_check_bq": OUT / "p2_check_bq.json",
        "p2_dry_run": OUT / "p2_dry_run.json",
        "ledger_insights": OUT / "ledger_insights.json",
    }
    paths["audit"].write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if audit["incremental_check_bq"].get("ok"):
        body = json.dumps(audit["incremental_check_bq"]["report"], ensure_ascii=False, indent=2) + "\n"
        paths["p2_check_bq"].write_text(body, encoding="utf-8")
        paths["p2_dry_run"].write_text(body, encoding="utf-8")
    if audit["ledger_insights"].get("ok"):
        paths["ledger_insights"].write_text(
            json.dumps(audit["ledger_insights"]["report"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {"ok": audit["ok"], "written": {k: str(v.relative_to(ROOT)) for k, v in paths.items()}}
    print(json.dumps(summary, indent=2))
    sys.exit(0 if audit["ok"] else 1)


if __name__ == "__main__":
    main()
