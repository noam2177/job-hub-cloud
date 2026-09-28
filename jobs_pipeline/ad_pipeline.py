"""Queue item processing for image job ads (P5)."""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jobs_pipeline.ad_direct import DirectResult, GeminiVision, LocalVlmDirect
from jobs_pipeline.ad_schema import JobAd
from jobs_pipeline.ad_structure import Llm, StructureResult, structure
from jobs_pipeline.contracts import utc_now
from jobs_pipeline.events import keywords_from_title
from jobs_pipeline.ocr_extract import OcrEngine, OcrResult
from jobs_pipeline.title_family import classify_title

PATH_OCR_LLM_LOCAL = "ocr_llm_local"
PATH_DIRECT_LOCAL = "direct_local"
PATH_OCR_LLM_GCP = "ocr_llm_gcp"
PATH_DIRECT_GCP = "direct_gcp"


@dataclass
class PipelineResult:
    record_path: Path
    needs_review: bool
    reasons: list[str]
    event: dict[str, Any]
    cost_usd: float
    latency_ms: int


@dataclass
class PipelineEngines:
    ocr: OcrEngine | None = None
    llm: Llm | None = None
    direct_local: LocalVlmDirect | None = None
    direct_gcp: GeminiVision | None = None


def _resolve_image_path(bus_root: Path, file_id: str) -> Path:
    if not file_id or file_id.startswith(("/", "\\")) or ".." in file_id.replace("\\", "/").split("/"):
        raise ValueError("invalid file_id path")
    root = bus_root.resolve()
    target = (root / file_id).resolve()
    if not target.is_relative_to(root):
        raise ValueError("file_id escapes bus root")
    if not target.is_file():
        raise FileNotFoundError(f"missing image: {file_id}")
    return target


def _review_reasons(
    job_ad: JobAd | None,
    injection_hits: list[str],
    validation_failed: bool,
) -> list[str]:
    reasons: list[str] = []
    if validation_failed or job_ad is None:
        reasons.append("validation_failed")
        return reasons
    if job_ad.confidence < 0.7:
        reasons.append("low_confidence")
    if not job_ad.title:
        reasons.append("missing_title")
    if not job_ad.company:
        reasons.append("missing_company")
    if injection_hits:
        reasons.append("injection_hits")
    return reasons


def build_found_event(sha256: str, job_ad: JobAd | None, ts: str) -> dict[str, Any]:
    """ts is the queue time, so re-processing the same image yields the same event_id."""
    title = ((job_ad.title if job_ad else None) or "")[:160]
    job_id = f"img-{sha256[:12]}"
    payload = {"company": job_ad.company if job_ad else None, "title": title or None,
               "location": job_ad.location if job_ad else None, "origin": "image_ad"}
    return {
        "event_id": hashlib.sha256(f"{job_id}|found|{ts}".encode("utf-8")).hexdigest(),
        "job_id": job_id,
        "event_type": "found",
        "ts": ts,
        "cv_version": None,
        "title_family": classify_title(title),
        "keywords": keywords_from_title(title),
        "source_type": "image",
        "payload": {k: v for k, v in payload.items() if v},
    }


def default_state_root() -> Path:
    return Path(os.environ.get("JOBHUB_STATE_DIR", "state"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def process_queue_item(
    item: dict[str, Any],
    bus_root: Path,
    path_name: str,
    engines: PipelineEngines,
    state_root: Path | None = None,
) -> PipelineResult:
    sha256 = str(item.get("sha256") or "")
    file_id = str(item.get("file_id") or "")
    mime = str(item.get("mime") or "image/png")
    image_path = _resolve_image_path(bus_root, file_id)
    image_bytes = image_path.read_bytes()

    t0 = time.perf_counter()
    cost = 0.0
    job_ad: JobAd | None = None
    injection_hits: list[str] = []
    validation_failed = False

    if path_name == PATH_OCR_LLM_LOCAL or path_name == PATH_OCR_LLM_GCP:
        if engines.ocr is None or engines.llm is None:
            raise ValueError(f"{path_name} requires ocr and llm engines")
        ocr: OcrResult = engines.ocr.run(image_bytes, mime)
        cost += ocr.cost_usd
        struct: StructureResult = structure(ocr.text, engines.llm)
        job_ad = struct.job_ad
        injection_hits = struct.injection_hits
        validation_failed = job_ad is None
    elif path_name == PATH_DIRECT_LOCAL:
        if engines.direct_local is None:
            raise ValueError("direct_local requires direct_local engine")
        direct: DirectResult = engines.direct_local.extract(image_bytes, mime)
        job_ad = direct.job_ad
        injection_hits = list(direct.injection_hits)
        validation_failed = direct.error is not None or job_ad is None
        cost += direct.cost_usd
    elif path_name == PATH_DIRECT_GCP:
        if engines.direct_gcp is None:
            raise ValueError("direct_gcp requires direct_gcp engine")
        direct = engines.direct_gcp.extract(image_bytes, mime)
        job_ad = direct.job_ad
        injection_hits = list(direct.injection_hits)
        validation_failed = direct.error is not None or job_ad is None
        cost += direct.cost_usd
    else:
        raise ValueError(f"unknown path_name: {path_name}")

    latency_ms = int((time.perf_counter() - t0) * 1000)
    reasons = _review_reasons(job_ad, injection_hits, validation_failed)
    needs_review = bool(reasons)

    state = state_root or default_state_root()

    record = {
        "job_ad": job_ad.model_dump() if job_ad else None,
        "path": path_name,
        "cost_usd": cost,
        "latency_ms": latency_ms,
        "needs_review": needs_review,
        "reasons": reasons,
        "sha256": sha256,
        "file_id": file_id,
        "processed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    out_path = state / "ads" / f"{sha256}.json"
    _write_json(out_path, record)
    if needs_review:
        _write_json(state / "review_queue" / f"{sha256}.json", record)

    event = build_found_event(sha256, job_ad, str(item.get("queued_at") or utc_now()))
    return PipelineResult(
        record_path=out_path,
        needs_review=needs_review,
        reasons=reasons,
        event=event,
        cost_usd=cost,
        latency_ms=latency_ms,
    )
