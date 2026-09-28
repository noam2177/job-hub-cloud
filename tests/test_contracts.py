import copy

import pytest

from jobs_pipeline.contracts import TaskInvalid, build_task, decode, encode, validate

SHA = "a" * 64


def test_link_task_roundtrip() -> None:
    task = build_task("telegram_job_link", "telegram", url="https://jobs.example/123/")
    assert task["payload"]["url"] == "https://jobs.example/123"
    assert decode(encode(task)) == task


def test_same_url_same_dedupe_key() -> None:
    a = build_task("telegram_job_link", "telegram", url="https://jobs.example/1")
    b = build_task("telegram_job_link", "telegram", url="https://jobs.example/1/")
    assert a["dedupe_key"] == b["dedupe_key"]
    assert a["task_id"] != b["task_id"]


def test_rename_is_not_a_new_file_task() -> None:
    a = build_task("drive_file", "drive", file_id="inbox_raw/ad.png", sha256=SHA, mime="image/png")
    b = build_task("drive_file", "drive", file_id="inbox_raw/renamed.png", sha256=SHA, mime="image/png")
    assert a["dedupe_key"] == b["dedupe_key"]


def test_file_task_requires_sha256() -> None:
    with pytest.raises(TaskInvalid):
        build_task("drive_file", "drive", file_id="inbox_raw/ad.png")


def test_http_url_rejected() -> None:
    with pytest.raises(TaskInvalid):
        build_task("telegram_job_link", "telegram", url="http://127.0.0.1/apply")


def test_extra_fields_rejected() -> None:
    task = build_task("telegram_job_link", "telegram", url="https://jobs.example/1")
    bad = copy.deepcopy(task)
    bad["command"] = "rm -rf /"
    with pytest.raises(TaskInvalid):
        validate(bad)


def test_tampered_dedupe_key_rejected() -> None:
    task = build_task("telegram_job_link", "telegram", url="https://jobs.example/1")
    task["payload"]["url"] = "https://jobs.example/2"
    with pytest.raises(TaskInvalid):
        validate(task)


def test_garbage_bytes_rejected() -> None:
    with pytest.raises(TaskInvalid):
        decode(b"\xff\xfe not json")
