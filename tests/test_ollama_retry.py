from __future__ import annotations

from urllib.error import URLError

import pytest

from jobs_pipeline.ollama_retry import urlopen_with_retry


def test_urlopen_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky(req, timeout: int = 0):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] < 2:
            raise URLError("refused")
        class R:
            def __enter__(self):
                return self

            def __exit__(self, *_a: object) -> None:
                return None

            def read(self) -> bytes:
                return b"ok"

        return R()

    with urlopen_with_retry(flaky, object(), timeout=1, retries=3, backoff_s=0.01) as resp:
        assert resp.read() == b"ok"
    assert calls["n"] == 2


def test_urlopen_exhausts_retries() -> None:
    def always_fail(req, timeout: int = 0):  # noqa: ANN001
        raise URLError("down")

    with pytest.raises(URLError):
        urlopen_with_retry(always_fail, object(), timeout=1, retries=2, backoff_s=0.01)
