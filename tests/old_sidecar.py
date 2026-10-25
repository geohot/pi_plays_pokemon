#!/usr/bin/env python3
"""A sidecar frozen at the pre-actions API, for end-to-end tests.

Speaks the old /act contract ({"button": ..., "frames": ..., "presses": ...})
and reports no `api` in /status. The extension must detect this and replace
the process: against this sidecar, every {"actions": [...]} press silently
becomes a no-op wait, which is exactly the regression it guards against.

e2e.sh copies this file to <tmpdir>/emu.py before running it, so the
extension's ownership check (a /proc cmdline ending in emu.py) sees it.

Usage: old_sidecar.py PORT PIDFILE
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8341
PIDFILE = sys.argv[2] if len(sys.argv) > 2 else "runs/emu.pid"


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status":
            self._json({"run": "old", "step": 0, "mode": "fresh",
                        "campaign": False, "last": None})   # no "api": pre-actions sidecar
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/reset":
            self._json({"run": body.get("name") or "old", "step": 0})
        elif self.path == "/act":
            # The old API: one button held `frames`. A body with only
            # {"actions": [...]} reads as button=None: a wait that presses nothing.
            self._json({"step": 1, "button": body.get("button"),
                        "frames": body.get("frames", 8), "presses": body.get("presses", 1),
                        "emulated_frames": 8, "changed": 0.0})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    os.makedirs(os.path.dirname(PIDFILE) or ".", exist_ok=True)
    with open(PIDFILE, "w") as fh:
        fh.write(str(os.getpid()))
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[old-sidecar] http://127.0.0.1:{PORT} (pre-actions API)", flush=True)
    server.serve_forever()
