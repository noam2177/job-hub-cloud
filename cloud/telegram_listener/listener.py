"""Telegram long-poll intake: parse updates, publish tasks, persist offset."""
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Protocol

from jobs_pipeline import contracts
from jobs_pipeline.sanitize import clean, log_safe

PUBLISH_BACKOFF_S = 10.0
_HTTPS_URL = re.compile(r"https://[^\s<>\"']+", re.IGNORECASE)


class Publisher(Protocol):
    def publish(self, data: bytes) -> None: ...


class OffsetStore(Protocol):
    def load(self) -> int | None: ...

    def save(self, offset: int) -> None: ...


class TelegramApi(Protocol):
    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]: ...

    def send_message(self, chat_id: int, text: str) -> None: ...


def _hostname_blocked(host: str) -> bool:
    h = (host or "").strip().lower().rstrip(".")
    if not h or h == "localhost":
        return True
    if h.endswith(".internal"):
        return True
    try:
        addr = ip_address(h)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or str(addr).startswith("127.")
    )


def _url_ok(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    host = parsed.hostname or ""
    return not _hostname_blocked(host)


def _urls_from_entities(text: str, entities: list[dict[str, Any]] | None) -> list[str]:
    found: list[str] = []
    if not text:
        return found
    for ent in entities or []:
        etype = ent.get("type")
        start = int(ent.get("offset", 0))
        length = int(ent.get("length", 0))
        chunk = text[start : start + length]
        if etype == "url" and chunk:
            found.append(chunk)
        elif etype == "text_link":
            link = ent.get("url")
            if link:
                found.append(str(link))
    return found


def _first_https_url(text: str, entities: list[dict[str, Any]] | None) -> str | None:
    for candidate in _urls_from_entities(text, entities):
        if candidate.lower().startswith("http://"):
            continue
        if candidate.lower().startswith("https://") and _url_ok(candidate):
            return candidate.rstrip(").,;]")
    for match in _HTTPS_URL.finditer(text or ""):
        url = match.group(0).rstrip(").,;]")
        if _url_ok(url):
            return url
    return None


def parse_update(update: dict[str, Any], allowed_chat_ids: set[int]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id not in allowed_chat_ids:
        return None
    if message.get("photo") or message.get("document"):
        print(log_safe("unsupported_media chat=%s" % chat_id))
        return None
    text = message.get("text") or message.get("caption") or ""
    entities = message.get("entities") or message.get("caption_entities")
    url = _first_https_url(text, entities)
    if not url:
        return None
    sanitized = clean(text)
    if not sanitized.ok:
        print(log_safe("sanitize_hits=%s" % ",".join(sanitized.hits)))
        safe_text = None
    else:
        safe_text = sanitized.text or None
    return contracts.build_task("telegram_job_link", "telegram", url=url, text=safe_text)


def _resolve_token() -> str:
    if os.environ.get("TOKEN_FROM_SECRET_MANAGER") == "1":
        from google.cloud import secretmanager  # lazy: not in dev venv

        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT required for Secret Manager token")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project}/secrets/telegram-intake-token/versions/latest"
        return client.access_secret_version(request={"name": name}).payload.data.decode("utf-8").strip()
    token = os.environ.get("TELEGRAM_INTAKE_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_INTAKE_BOT_TOKEN not set")
    return token


class UrllibTelegramApi:
    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}/"

    def _post(self, method: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._base + method,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(log_safe("telegram_api_error %s" % payload.get("description", "")))
        return payload

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            body["offset"] = offset
        return self._post("getUpdates", body).get("result") or []

    def send_message(self, chat_id: int, text: str) -> None:
        self._post("sendMessage", {"chat_id": chat_id, "text": text})


class FileOffsetStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> int | None:
        if not self._path.is_file():
            return None
        raw = self._path.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None

    def save(self, offset: int) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(str(offset), encoding="utf-8")


class PubSubPublisher:
    def __init__(self, project_id: str, topic_id: str) -> None:
        self._project_id = project_id
        self._topic_id = topic_id
        self._client: Any = None

    def publish(self, data: bytes) -> None:
        if self._client is None:
            from google.cloud import pubsub_v1  # lazy

            self._client = pubsub_v1.PublisherClient()
        topic = self._client.topic_path(self._project_id, self._topic_id)
        future = self._client.publish(topic, data)
        future.result(timeout=30)


def _heartbeat_path() -> Path:
    base = Path(os.environ.get("JOBHUB_STATE_DIR", "/var/lib/jobhub"))
    return base / "heartbeat_listener.json"


def write_heartbeat(extra: dict[str, Any] | None = None) -> None:
    path = _heartbeat_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"utc": contracts.utc_now(), **(extra or {})}
    path.write_text(json.dumps(body), encoding="utf-8")


def run(
    api: TelegramApi,
    publisher: Publisher,
    offset_store: OffsetStore,
    allowed: set[int],
    stop_event: Any,
    sleep: Any = time.sleep,
) -> None:
    offset = offset_store.load()
    reply_ack = os.environ.get("REPLY_ACK") == "1"
    while not getattr(stop_event, "is_set", lambda: False)():
        if getattr(stop_event, "is_set", lambda: False)():
            break
        try:
            updates = api.get_updates(offset, timeout=50)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            print(log_safe("getUpdates_error %s" % exc))
            sleep(5)
            continue
        publish_failed = False
        for update in updates:
            update_id = int(update.get("update_id", 0))
            task = parse_update(update, allowed)
            if task is None:
                offset = update_id + 1
                offset_store.save(offset)
                continue
            try:
                publisher.publish(contracts.encode(task))
            except Exception as exc:
                print(log_safe("publish_failed update=%s %s" % (update_id, exc)))
                publish_failed = True
                break
            offset = update_id + 1
            offset_store.save(offset)
            if reply_ack:
                message = update.get("message") or {}
                chat_id = (message.get("chat") or {}).get("id")
                if chat_id is not None:
                    try:
                        api.send_message(int(chat_id), "התקבל")
                    except Exception as exc:
                        print(log_safe("reply_failed %s" % exc))
        write_heartbeat({"updates": len(updates), "publish_failed": publish_failed})
        if getattr(stop_event, "is_set", lambda: False)():
            break
        if publish_failed:
            sleep(PUBLISH_BACKOFF_S)
