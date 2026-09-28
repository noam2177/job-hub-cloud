from __future__ import annotations

import io
import sys
import types
from typing import Any

import pytest

from jobs_pipeline.bq_exporter import CHUNK_SIZE, Exporter, is_transient, to_ndjson


def _install_fake_bigquery() -> None:
    bq = types.ModuleType("google.cloud.bigquery")

    class LoadJobConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    bq.LoadJobConfig = LoadJobConfig
    bq.SourceFormat = types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON")
    bq.WriteDisposition = types.SimpleNamespace(WRITE_APPEND="WRITE_APPEND")
    google = types.ModuleType("google")
    cloud = types.ModuleType("google.cloud")
    sys.modules["google"] = google
    sys.modules["google.cloud"] = cloud
    sys.modules["google.cloud.bigquery"] = bq


class FakeJob:
    def __init__(self, errors: list[Any] | None = None) -> None:
        self.errors = errors or []
        self.job_id = "job-1"

    def result(self) -> None:
        return None


class FakeClient:
    def __init__(self, fail_times: int = 0, error: type[Exception] = TimeoutError) -> None:
        self.fail_times = fail_times
        self.error = error
        self.loads: list[bytes] = []
        self.attempts = 0

    def load_table_from_file(
        self,
        file_obj: io.IOBase,
        destination: str,
        job_config: Any,
        rewind: bool = True,
    ) -> FakeJob:
        self.attempts += 1
        data = file_obj.read()
        if rewind:
            file_obj.seek(0)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise self.error("load failed")
        self.loads.append(data)
        return FakeJob()


def test_to_ndjson_roundtrip_shape() -> None:
    rows = [{"event_id": "abc", "keywords": ["sql"], "payload": {"company": "X"}}]
    text = to_ndjson(rows)
    assert text.endswith("\n")
    assert '"event_id":"abc"' in text.replace(" ", "")


def test_exporter_dry_run() -> None:
    ex = Exporter(None, project_id="demo-project")
    report = ex.export([{"event_id": "1"}], dry_run=True)
    assert report["dry_run"] is True
    assert report["table"] == "demo-project.jobs.events"
    assert report["rows"] == 1


def test_exporter_chunking() -> None:
    _install_fake_bigquery()
    client = FakeClient()
    ex = Exporter(client, project_id="p", sleep_fn=lambda _s: None)
    rows = [{"event_id": str(i)} for i in range(CHUNK_SIZE + 3)]
    report = ex.export(rows, dry_run=False)
    assert report["chunks"] == 2
    assert len(client.loads) == 2


def test_exporter_retry() -> None:
    _install_fake_bigquery()
    client = FakeClient(fail_times=2)
    sleeps: list[float] = []
    ex = Exporter(client, project_id="p", sleep_fn=lambda s: sleeps.append(s))
    ex.export([{"event_id": "1"}], dry_run=False)
    assert client.attempts == 3
    assert sleeps == [1.0, 2.0]


def test_permanent_error_is_not_retried() -> None:
    _install_fake_bigquery()

    class BadRequest(Exception):
        pass

    client = FakeClient(fail_times=3, error=BadRequest)
    sleeps: list[float] = []
    ex = Exporter(client, project_id="p", sleep_fn=lambda s: sleeps.append(s))
    with pytest.raises(BadRequest):
        ex.export([{"event_id": "1"}], dry_run=False)
    assert client.attempts == 1
    assert sleeps == []


def test_google_style_transient_names_are_retried() -> None:
    class ServiceUnavailable(Exception):
        pass

    assert is_transient(ServiceUnavailable())
    assert not is_transient(ValueError())


def test_export_sets_exported_at() -> None:
    ex = Exporter(None, project_id="p")
    report = ex.export([{"event_id": "1", "exported_at": None}], dry_run=True)
    assert report["rows"] == 1
