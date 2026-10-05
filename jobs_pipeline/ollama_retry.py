"""Small retry helper for transient Ollama loopback errors."""
from __future__ import annotations

import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError


def urlopen_with_retry(
    urlopen: Callable[..., Any],
    req: Any,
    *,
    timeout: int,
    retries: int | None = None,
    backoff_s: float = 2.0,
) -> Any:
    attempts = retries if retries is not None else int(os.environ.get("OLLAMA_HTTP_RETRIES", "3"))
    last: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            return urlopen(req, timeout=timeout)
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            if attempt + 1 >= attempts:
                break
            time.sleep(backoff_s * (attempt + 1))
    assert last is not None
    raise last
