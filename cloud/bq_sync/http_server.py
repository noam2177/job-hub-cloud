"""Minimal HTTP entry for Cloud Run (stdlib only). GET /health, POST /sync."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from main import handle


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        return

    def _json(self, code: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            self._json(200, json.dumps({"ok": True, "service": "jobhub-bq-sync"}))
            return
        self._json(404, json.dumps({"ok": False, "error": "not_found"}))

    def do_POST(self) -> None:
        if self.path.rstrip("/") not in ("", "/sync"):
            self._json(404, json.dumps({"ok": False, "error": "not_found"}))
            return
        body, code = handle(None)
        self._json(code, body)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), _Handler).serve_forever()


if __name__ == "__main__":
    main()
