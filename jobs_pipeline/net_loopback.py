"""Loopback-only guard for local Ollama calls."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def is_loopback_host(host: str) -> bool:
    h = (host or "").strip().lower()
    if not h:
        return False
    if h == "localhost":
        return True
    if h.endswith(".localhost"):
        return True
    try:
        addr = ipaddress.ip_address(h)
        return addr.is_loopback
    except ValueError:
        pass
    try:
        for info in socket.getaddrinfo(h, None, type=socket.SOCK_STREAM):
            ip = info[4][0]
            if not ipaddress.ip_address(ip).is_loopback:
                return False
        return True
    except OSError:
        return False


def assert_loopback_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Ollama base URL must be http or https")
    if not is_loopback_host(parsed.hostname or ""):
        raise ValueError("Ollama base URL must use a loopback host only")
    return base_url.rstrip("/")
