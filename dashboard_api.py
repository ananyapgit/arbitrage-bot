from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8001
SUBSCRIBERS_FILE = Path("dashboard/public/data/subscribers.txt")
MASTER_LOG = Path("data/master_log.csv")
AUDIT_LOG = Path("dashboard/public/data/delivery_audit.csv")
BROADCAST_LOG = Path("dashboard/public/data/broadcast_log.csv")
WORKFLOW_HEARTBEAT = Path("dashboard/public/data/workflow_heartbeat.json")
POST_AUDIT = Path("post_audit.log")
FOLLOWUPS = Path("sale_followup_cache.json")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ApiHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Serve local artifacts so dashboard shows real bot state without GitHub pushes.
        if self.path == "/api/data/master_log.csv":
            return self._send_file(MASTER_LOG, "text/csv")
        if self.path == "/api/data/delivery_audit.csv":
            return self._send_file(AUDIT_LOG, "text/csv")
        if self.path == "/api/data/broadcast_log.csv":
            return self._send_file(BROADCAST_LOG, "text/csv")
        if self.path == "/api/data/workflow_heartbeat.json":
            return self._send_file(WORKFLOW_HEARTBEAT, "application/json")
        if self.path == "/api/data/post_audit.log":
            return self._send_file(POST_AUDIT, "text/plain")
        if self.path == "/api/data/sale_followup_cache.json":
            return self._send_file(FOLLOWUPS, "application/json")
        self._json(404, {"ok": False, "error": "not_found"})

    def _send_file(self, path: Path, content_type: str):
        try:
            if not path.exists():
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", content_type)
                self.end_headers()
                return
            data = path.read_bytes()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    def do_POST(self):
        if self.path != "/api/subscribers/add":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        try:
            ln = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(ln).decode("utf-8")
            payload = json.loads(raw or "{}")
            email = str(payload.get("email", "")).strip().lower()
            if not EMAIL_RE.match(email):
                self._json(400, {"ok": False, "error": "invalid_email"})
                return

            SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            existing: list[str] = []
            if SUBSCRIBERS_FILE.exists():
                existing = [
                    x.strip().lower()
                    for x in SUBSCRIBERS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if x.strip() and not x.strip().startswith("#")
                ]
            if email in set(existing):
                self._json(200, {"ok": True, "duplicate": True, "email": email})
                return
            with SUBSCRIBERS_FILE.open("a", encoding="utf-8") as f:
                if SUBSCRIBERS_FILE.stat().st_size == 0:
                    f.write("# one email per line\n")
                f.write(email + "\n")
            self._json(200, {"ok": True, "email": email})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})


def main():
    httpd = HTTPServer((HOST, PORT), ApiHandler)
    print(f"[dashboard_api] listening on http://{HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
