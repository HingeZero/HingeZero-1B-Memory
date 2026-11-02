"""Opt-in localhost memory API, bearer-token authenticated. Disabled by default.
The desktop UI starts this only after an explicit user action.
"""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import threading
from hzdesktop.retrieval import search, RetainedMemorySession


class LocalAPI:
    def __init__(self, vault, port: int = 0):
        self.vault = vault
        self.token = secrets.token_urlsafe(32)
        self.read_token = secrets.token_urlsafe(32)
        self.retained_session = RetainedMemorySession()
        self.lock = threading.RLock()
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *args):
                pass  # Do not log private queries or tokens.

            def do_GET(self):
                self._reply(405, {"error": "POST only"})

            def do_POST(self):
                supplied = self.headers.get("Authorization", "")
                can_write = hmac.compare_digest(supplied, "Bearer " + parent.token)
                can_read = hmac.compare_digest(supplied, "Bearer " + parent.read_token)
                if not (can_write or can_read):
                    self._reply(401, {"error": "Unauthorized"})
                    return
                if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                    self._reply(415, {"error": "Content-Type application/json required"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16_384:
                        self._reply(413, {"error": "Request body size must be 1-16384 bytes"})
                        return
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("Request must be a JSON object")
                    if self.path == "/v1/search":
                        query = str(payload.get("query", ""))[:2000]
                        with parent.lock:
                            found = search(parent.vault.list(), query, limit=5,
                                           session=parent.retained_session)
                        self._reply(200, {"results": [{"id": r["record"]["id"],
                            "title": r["record"]["title"],
                            "content": r["record"]["content"],
                            "source": r["record"]["source"],
                            "score": round(r["score"], 5)} for r in found]})
                    elif self.path == "/v1/remember":
                        if not can_write:
                            self._reply(403, {"error": "Read-only session token cannot write"})
                            return
                        title = str(payload.get("title", ""))[:200]
                        content = str(payload.get("content", ""))
                        with parent.lock:
                            identifier = parent.vault.add(title, content, "local-api")
                            parent.retained_session.reset()
                        self._reply(201, {"id": identifier})
                    else:
                        self._reply(404, {"error": "Unknown endpoint"})
                except (ValueError, TypeError, UnicodeError) as exc:
                    self._reply(400, {"error": str(exc)[:160]})
                except Exception:
                    self._reply(500, {"error": "Internal error"})

            def _reply(self, status: int, payload: dict):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.http = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.http.daemon_threads = True
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return self.http.server_address[1]

    def stop(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)
