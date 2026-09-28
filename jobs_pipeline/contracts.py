"""Task message v1: build, validate, dedupe identity. Shared by cloud and local sides."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "contracts" / "task_v1.schema.json"
TASK_TYPES = ("telegram_job_link", "drive_file", "ocr_job_image")
IMAGE_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})


class TaskInvalid(ValueError):
    pass


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def identity(task_type: str, source: str, payload: dict[str, Any]) -> str:
    """Stable identity: URL for links, content hash for files (a rename is not a new task)."""
    if task_type == "telegram_job_link":
        return f"{source}|url|{normalize_url(str(payload.get('url') or ''))}"
    return f"{source}|sha256|{payload.get('sha256') or ''}"


def dedupe_key(task_type: str, source: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(identity(task_type, source, payload).encode("utf-8")).hexdigest()


def build_task(task_type: str, source: str, **payload_fields: Any) -> dict[str, Any]:
    payload = {"url": None, "file_id": None, "version": None, "text": None}
    payload.update({k: v for k, v in payload_fields.items() if v is not None})
    if payload.get("url"):
        payload["url"] = normalize_url(str(payload["url"]))
    task = {
        "schema": "v1",
        "task_id": str(uuid.uuid4()),
        "type": task_type,
        "source": source,
        "payload": payload,
        "dedupe_key": dedupe_key(task_type, source, payload),
        "created_at": utc_now(),
    }
    validate(task)
    return task


def validate(task: Any) -> dict[str, Any]:
    errors = sorted(_validator().iter_errors(task), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        where = "/".join(str(p) for p in first.path) or "<root>"
        raise TaskInvalid(f"{where}: {first.message[:200]}")
    if task["dedupe_key"] != dedupe_key(task["type"], task["source"], task["payload"]):
        raise TaskInvalid("dedupe_key: does not match payload identity")
    return task


def encode(task: dict[str, Any]) -> bytes:
    return json.dumps(validate(task), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode(raw: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskInvalid(f"not json: {type(exc).__name__}") from exc
    return validate(data)
