from __future__ import annotations

import io
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol

CHUNK_SIZE = 5000
DEFAULT_TABLE = "jobs.events"
MAX_RETRIES = 3
TRANSIENT_ERRORS = frozenset(
    {
        "TooManyRequests",
        "InternalServerError",
        "ServiceUnavailable",
        "BadGateway",
        "GatewayTimeout",
        "DeadlineExceeded",
        "RetryError",
        "ConnectionError",
        "TimeoutError",
    }
)


def is_transient(exc: BaseException) -> bool:
    return any(cls.__name__ in TRANSIENT_ERRORS for cls in type(exc).__mro__)


class LoadJob(Protocol):
    job_id: str
    errors: list[Any]


class BqClient(Protocol):
    def load_table_from_file(
        self,
        file_obj: io.IOBase,
        destination: str,
        job_config: Any,
        rewind: bool = ...,
    ) -> LoadJob: ...


def to_ndjson(events: list[dict[str, Any]]) -> str:
    lines = [json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in events]
    return "\n".join(lines) + ("\n" if lines else "")


def _exported_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ts = _exported_now()
    out: list[dict[str, Any]] = []
    for row in events:
        stamped = dict(row)
        stamped["exported_at"] = ts
        out.append(stamped)
    return out


def _chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


class Exporter:
    def __init__(
        self,
        client: BqClient | None,
        *,
        project_id: str | None = None,
        table: str = DEFAULT_TABLE,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.client = client
        self.project_id = project_id
        self.table = table
        self.sleep_fn = sleep_fn or (lambda _s: None)

    def _destination(self) -> str:
        if self.project_id:
            return f"{self.project_id}.{self.table}"
        return self.table

    def _load_chunk(self, chunk: list[dict[str, Any]]) -> None:
        if self.client is None:
            raise RuntimeError("BigQuery client is required for apply mode")
        from google.cloud import bigquery

        payload = to_ndjson(chunk).encode("utf-8")
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                buf = io.BytesIO(payload)
                job = self.client.load_table_from_file(
                    buf,
                    self._destination(),
                    job_config=job_config,
                    rewind=True,
                )
                job.result()
                if getattr(job, "errors", None):
                    raise RuntimeError(f"load job errors: {job.errors}")
                return
            except Exception as exc:
                last_exc = exc
                if not is_transient(exc):
                    raise
                if attempt + 1 < MAX_RETRIES:
                    self.sleep_fn(2**attempt)
        raise last_exc or RuntimeError("load failed")

    def export(self, events: list[dict[str, Any]], *, dry_run: bool = True) -> dict[str, Any]:
        stamped = _stamp(events)
        dest = self._destination()
        if dry_run:
            return {"rows": len(stamped), "dry_run": True, "table": dest, "chunks": len(_chunks(stamped, CHUNK_SIZE))}
        for chunk in _chunks(stamped, CHUNK_SIZE):
            self._load_chunk(chunk)
        return {"rows": len(stamped), "dry_run": False, "table": dest, "chunks": len(_chunks(stamped, CHUNK_SIZE))}
