import json
from pathlib import Path

import pytest

from jobs_pipeline.ad_direct import DirectResult
from jobs_pipeline.ad_pipeline import PATH_DIRECT_LOCAL, PipelineEngines, process_queue_item
from jobs_pipeline.ad_schema import JobAd

SHA = "b" * 64


class FakeDirect:
    def __init__(self, ad: JobAd | None, hits: list[str] | None = None) -> None:
        self.ad, self.hits = ad, hits or []

    def extract(self, image_bytes: bytes, mime: str) -> DirectResult:
        return DirectResult(job_ad=self.ad, cost_usd=0.0, latency_ms=1, injection_hits=self.hits)


def _setup(tmp_path: Path) -> tuple[Path, Path, dict]:
    bus = tmp_path / "bus"
    (bus / "inbox_raw").mkdir(parents=True)
    (bus / "inbox_raw" / "ad.png").write_bytes(b"\x89PNG fake")
    item = {"task_id": "t1", "file_id": "inbox_raw/ad.png", "sha256": SHA, "mime": "image/png",
            "queued_at": "2026-09-28T10:00:00Z"}
    return bus, tmp_path / "state", item


def _good_ad() -> JobAd:
    return JobAd(title="Data Analyst", company="Example Ltd", location="Haifa", contact="jobs@example.com",
                 requirements=["SQL", "Python"], confidence=0.95)


def test_good_ad_written_to_local_state_not_bus(tmp_path: Path) -> None:
    bus, state, item = _setup(tmp_path)
    result = process_queue_item(item, bus, PATH_DIRECT_LOCAL, PipelineEngines(direct_local=FakeDirect(_good_ad())), state)
    assert not result.needs_review
    assert result.record_path == state / "ads" / f"{SHA}.json"
    assert not (bus / "state").exists()


def test_event_is_deterministic_and_allow_listed(tmp_path: Path) -> None:
    bus, state, item = _setup(tmp_path)
    engines = PipelineEngines(direct_local=FakeDirect(_good_ad()))
    first = process_queue_item(item, bus, PATH_DIRECT_LOCAL, engines, state).event
    second = process_queue_item(item, bus, PATH_DIRECT_LOCAL, engines, state).event
    assert first["event_id"] == second["event_id"]
    assert first["title_family"] == "data_analyst"
    blob = json.dumps(first, ensure_ascii=False)
    assert "jobs@example.com" not in blob and "Python" not in blob


def test_low_confidence_goes_to_review(tmp_path: Path) -> None:
    bus, state, item = _setup(tmp_path)
    ad = JobAd(title="Analyst", company=None, confidence=0.3)
    result = process_queue_item(item, bus, PATH_DIRECT_LOCAL, PipelineEngines(direct_local=FakeDirect(ad)), state)
    assert result.needs_review and {"low_confidence", "missing_company"} <= set(result.reasons)
    assert (state / "review_queue" / f"{SHA}.json").is_file()


def test_injection_forces_review(tmp_path: Path) -> None:
    bus, state, item = _setup(tmp_path)
    engines = PipelineEngines(direct_local=FakeDirect(_good_ad(), hits=["instruction_override"]))
    assert "injection_hits" in process_queue_item(item, bus, PATH_DIRECT_LOCAL, engines, state).reasons


@pytest.mark.parametrize("bad", ["../secret.png", "/etc/passwd", "inbox_raw/../../x.png"])
def test_path_traversal_refused(tmp_path: Path, bad: str) -> None:
    bus, state, item = _setup(tmp_path)
    item["file_id"] = bad
    with pytest.raises(ValueError):
        process_queue_item(item, bus, PATH_DIRECT_LOCAL, PipelineEngines(direct_local=FakeDirect(_good_ad())), state)


def test_sibling_directory_prefix_refused(tmp_path: Path) -> None:
    bus, state, item = _setup(tmp_path)
    sibling = tmp_path / "bus2"
    sibling.mkdir()
    (sibling / "x.png").write_bytes(b"x")
    item["file_id"] = str(sibling / "x.png")
    with pytest.raises(ValueError):
        process_queue_item(item, bus, PATH_DIRECT_LOCAL, PipelineEngines(direct_local=FakeDirect(_good_ad())), state)
