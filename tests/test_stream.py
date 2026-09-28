"""stream.py mirrors pi's JSONL agent events into the sidecar's /agent feed."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect(events):
    """Run stream.py over `events` with a stub sidecar; return its POSTs."""
    posts = []

    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            posts.append(json.loads(self.rfile.read(n) or b"{}"))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Collector)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = dict(os.environ, EMU_URL=f"http://127.0.0.1:{server.server_address[1]}")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "stream.py")],
        input="\n".join(json.dumps(e) for e in events) + "\n",
        env=env, capture_output=True, text=True, timeout=30)
    server.shutdown()
    return posts, proc


def delta(kind, text):
    return {"type": "message_update", "assistantMessageEvent": {"type": kind, "delta": text}}


def test_thinking_deltas_merge():
    posts, proc = collect([
        {"type": "message_start", "message": {"role": "assistant"}},
        delta("thinking_delta", "let me "),
        delta("thinking_delta", "think"),
        {"type": "message_end"},
    ])
    assert proc.returncode == 0
    kinds = [(p["kind"], p["text"]) for p in posts]
    assert ("turn", kinds[0][1]) == kinds[0]          # turn marker first
    assert ("thinking", "let me think") in kinds      # deltas merged, flushed at end


def test_text_deltas_and_tool_result():
    posts, proc = collect([
        {"type": "message_start", "message": {"role": "assistant"}},
        delta("text_delta", "moving right"),
        {"type": "message_end"},
        {"type": "tool_execution_end", "toolName": "act",
         "result": {"content": [{"type": "text", "text": "step 5: right 16f x1\nmore"}]}},
    ])
    assert proc.returncode == 0
    kinds = [(p["kind"], p["text"]) for p in posts]
    assert ("text", "moving right") in kinds
    assert ("result", "act: step 5: right 16f x1") in kinds  # first line only


def test_garbage_lines_are_skipped():
    posts, proc = collect([])
    assert proc.returncode == 0
    proc = subprocess.run(
        [sys.executable, str(ROOT / "stream.py")],
        input='not json\n{"type": "unknown"}\n',
        env=dict(os.environ, EMU_URL="http://127.0.0.1:1"),
        capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0
