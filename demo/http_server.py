"""HTTP lab UI: login, live RPC feed, and one-click reset."""

from __future__ import annotations

import json
import logging
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from demo.state import (
    SESSION_COOKIE,
    create_session,
    credentials_match,
    drop_session,
    reset_key_matches,
    reset_state,
    session_user,
    snapshot,
    subscribe,
    unsubscribe,
)

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def start_http(state: dict[str, Any], host: str, port: int) -> ThreadingHTTPServer:
    handler = _handler_for(state)
    server = ThreadingHTTPServer((host, port), handler)
    logger.info("HTTP lab UI listening on http://%s:%s", host, port)
    return server


def _handler_for(state: dict[str, Any]):
    class LabHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("%s - %s", self.address_string(), format % args)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._json(200, {"ok": True})
                return
            if path in ("/", "/index.html"):
                self._send_file(INDEX_FILE, "text/html; charset=utf-8")
                return
            if path == "/api/me":
                user = self._user()
                if not user:
                    self._json(401, {"ok": False, "error": "not logged in"})
                    return
                self._json(200, {"ok": True, "username": user})
                return
            if path == "/api/snapshot":
                if not self._user():
                    self._json(401, {"ok": False, "error": "not logged in"})
                    return
                self._json(200, snapshot(state))
                return
            if path == "/events":
                self._stream_events()
                return
            self._json(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/login":
                self._login()
                return
            if path == "/logout":
                drop_session(state, self._token())
                self._redirect("/")
                return
            if path == "/reset":
                self._reset()
                return
            self._json(404, {"ok": False, "error": "not found"})

        def _login(self) -> None:
            fields = self._form()
            username = fields.get("username", [""])[0]
            password = fields.get("password", [""])[0]
            if not credentials_match(state, username, password):
                self._redirect("/?error=1")
                return
            token = create_session(state, username)
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie",
                f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax",
            )
            self.end_headers()

        def _reset(self) -> None:
            authorized = self._user() or reset_key_matches(
                state, self.headers.get("X-Reset-Key")
            )
            if not authorized:
                self._json(401, {"ok": False, "error": "login required"})
                return
            reset_state(state)
            logger.info("Lab state reset")
            wants_json = bool(self.headers.get("X-Reset-Key")) or "application/json" in (
                self.headers.get("Accept") or ""
            )
            if wants_json:
                self._json(200, {"ok": True, **snapshot(state)})
                return
            self._redirect("/")

        def _stream_events(self) -> None:
            if not self._user():
                self._json(401, {"ok": False, "error": "not logged in"})
                return
            subscriber = subscribe(state)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    event = subscriber.get()
                    payload = json.dumps(event)
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                logger.debug("Event stream closed")
            finally:
                unsubscribe(state, subscriber)

        def _user(self) -> str | None:
            return session_user(state, self._token())

        def _token(self) -> str | None:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            morsel = cookie.get(SESSION_COOKIE)
            return morsel.value if morsel else None

        def _form(self) -> dict[str, list[str]]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            return parse_qs(raw, keep_blank_values=True)

        def _json(self, status: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _redirect(self, location: str) -> None:
            self.send_response(303)
            self.send_header("Location", location)
            self.end_headers()

        def _send_file(self, path: Path, content_type: str) -> None:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return LabHandler
