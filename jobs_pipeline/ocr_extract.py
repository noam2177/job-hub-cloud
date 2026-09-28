"""OCR engines for job-ad images (P5)."""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib import request
from urllib.error import HTTPError, URLError

from jobs_pipeline.net_loopback import assert_loopback_base_url

DOCAI_COST_PER_PAGE = 0.0015


@dataclass(frozen=True)
class OcrResult:
    text: str
    pages: int
    engine: str
    cost_usd: float
    latency_ms: int


class OcrEngine(Protocol):
    def run(self, image_bytes: bytes, mime: str) -> OcrResult: ...


class DocumentAiOcr:
    """Google Document AI OCR (lazy import)."""

    def __init__(self, processor: str | None = None) -> None:
        self._processor = processor or os.environ.get("DOCAI_PROCESSOR", "")
        if not self._processor:
            raise ValueError("DOCAI_PROCESSOR is required for DocumentAiOcr")

    def run(self, image_bytes: bytes, mime: str) -> OcrResult:
        from google.cloud import documentai_v1 as documentai  # noqa: PLC0415

        t0 = time.perf_counter()
        client = documentai.DocumentProcessorServiceClient()
        raw_document = documentai.RawDocument(content=image_bytes, mime_type=mime)
        req = documentai.ProcessRequest(name=self._processor, raw_document=raw_document)
        result = client.process_document(request=req)
        doc = result.document
        pages = max(1, len(doc.pages) if doc.pages else 1)
        text = doc.text or ""
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return OcrResult(
            text=text,
            pages=pages,
            engine="document_ai",
            cost_usd=pages * DOCAI_COST_PER_PAGE,
            latency_ms=latency_ms,
        )


class LocalVlmOcr:
    """Verbatim transcription via local Ollama vision model."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        urlopen: Callable[..., Any] | None = None,
    ) -> None:
        self._base = assert_loopback_base_url(
            base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        )
        self._model = model or os.environ.get("OLLAMA_VLM_MODEL", "qwen3-vl:8b-instruct")
        self._urlopen = urlopen or request.urlopen

    def run(self, image_bytes: bytes, mime: str) -> OcrResult:
        t0 = time.perf_counter()
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Transcribe all visible text from this job advertisement image "
                        "verbatim. Output only the transcription, no commentary."
                    ),
                    "images": [b64],
                }
            ],
            "stream": False,
            "options": {"temperature": 0},
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self._base}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Ollama VLM OCR failed: {exc}") from exc
        data = json.loads(raw)
        text = str((data.get("message") or {}).get("content") or "").strip()
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return OcrResult(
            text=text,
            pages=1,
            engine="local_vlm_ocr",
            cost_usd=0.0,
            latency_ms=latency_ms,
        )
