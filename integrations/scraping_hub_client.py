"""Call scraping-hub-service /extract-job (optional enrich before Hub link)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _enabled() -> bool:
    return os.environ.get("JOBHUB_SCRAPING_ENRICH", "").strip().lower() in ("1", "true", "yes")


def _base() -> str:
    return (os.environ.get("SCRAPING_HUB_URL") or "http://127.0.0.1:8791").rstrip("/")


def extract_job(url: str, intent: str = "job posting") -> dict[str, Any]:
    body = json.dumps({"url": url, "intent": intent}).encode("utf-8")
    req = urllib.request.Request(
        f"{_base()}/extract-job",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=float(os.environ.get("SCRAPING_HUB_TIMEOUT_S") or "150")) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cache_extract(url: str) -> Path | None:
    if not _enabled():
        return None
    try:
        data = extract_job(url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, RuntimeError):
        return None
    safe = "".join(c if c.isalnum() else "_" for c in url[:120])
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    written: Path | None = None
    root = Path(os.environ.get("JOBHUB_STATE_DIR", "state"))
    out_dir = root / "scrape_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{safe}.json"
    path.write_text(payload, encoding="utf-8")
    written = path
    bus = os.environ.get("CAREER_DRIVE_BUS_DIR", "").strip()
    if bus:
        bus_dir = Path(bus) / "ledger" / "scrape_cache"
        bus_dir.mkdir(parents=True, exist_ok=True)
        bus_path = bus_dir / f"{safe}.json"
        if bus_path != path:
            bus_path.write_text(payload, encoding="utf-8")
            written = bus_path
    return written
