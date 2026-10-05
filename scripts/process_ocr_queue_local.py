#!/usr/bin/env python3
"""Drain state/ocr_queue using local VLM + text LLM (Ollama loopback). No cloud OCR spend."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobs_pipeline.ad_pipeline import PATH_OCR_LLM_LOCAL, PipelineEngines, process_queue_item
from jobs_pipeline.ad_structure import OllamaLlm
from jobs_pipeline.incremental_sync import default_ledger_path
from jobs_pipeline.local_insights import aggregate_ledger
from jobs_pipeline.ocr_extract import LocalVlmOcr


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _refresh_ledger_insights(ledger_path: Path, ocr_summary: dict) -> Path:
    insights_path = ledger_path.parent / "insights_local.json"
    body = {
        "generated_at": _utc_now(),
        "ledger": str(ledger_path),
        "stats": aggregate_ledger(ledger_path),
        "ocr_run": ocr_summary,
    }
    _write_json_atomic(insights_path, body)
    return insights_path


def main() -> None:
    state = Path(os.environ.get("JOBHUB_STATE_DIR", "state"))
    queue = state / "ocr_queue"
    bus = os.environ.get("CAREER_DRIVE_BUS_DIR", "")
    if not bus:
        print(json.dumps({"ok": False, "error": "CAREER_DRIVE_BUS_DIR not set"}))
        sys.exit(1)
    bus_path = Path(bus)
    engines = PipelineEngines(ocr=LocalVlmOcr(), llm=OllamaLlm())
    processed = 0
    errors: list[str] = []
    events: list[dict] = []
    for meta_path in sorted(queue.glob("*.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(meta_path.name)
            continue
        try:
            result = process_queue_item(meta, bus_path, PATH_OCR_LLM_LOCAL, engines, state)
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append(f"{meta_path.stem}:{exc}")
            continue
        processed += 1
        events.append(result.event)
        meta_path.unlink(missing_ok=True)
    ledger_path = default_ledger_path()
    ocr_summary = {"processed": processed, "errors": errors[:20], "events": len(events)}
    insights_path = None
    if ledger_path.is_file():
        try:
            insights_path = _refresh_ledger_insights(ledger_path, ocr_summary)
        except OSError as exc:
            errors.append(f"insights_write:{exc}")
    print(
        json.dumps(
            {
                "ok": True,
                "processed": processed,
                "errors": errors[:20],
                "ledger": str(ledger_path),
                "insights_path": str(insights_path) if insights_path else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
