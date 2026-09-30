#!/usr/bin/env python3
"""Stub OpenAI-compatible model server for end-to-end tests.

Speaks just enough of the streaming chat-completions API for pi's
`openai-completions` provider. It plays a fixed script, one tool call per
request, keyed on how many tool results the conversation already contains:

  0 tool results -> look()
  1              -> act("right")
  2              -> act("a")     (palette flash: a big screen change)
  3+             -> report(done=true)

Usage: stub_model.py [port]  (default 8398)
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = [
    ("look", {}),
    ("act", {"button": "right", "frames": 30}),
    ("act", {"button": "a"}),
    ("report", {"done": True, "note": "stub model reached its target"}),
]


def sse(obj):
    return f"data: {json.dumps(obj)}\n\n".encode()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not self.path.rstrip("/").endswith("chat/completions"):
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        tools_seen = sum(1 for m in body.get("messages", []) if m.get("role") == "tool")
        name, args = SCRIPT[min(tools_seen, len(SCRIPT) - 1)]

        model = body.get("model", "stub-1")
        call_id = f"call_{tools_seen}"
        chunks = [
            {"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}]},
            {"choices": [{"index": 0, "delta": {"tool_calls": [
                {"index": 0, "id": call_id, "type": "function",
                 "function": {"name": name, "arguments": ""}}]}}]},
            {"choices": [{"index": 0, "delta": {"tool_calls": [
                {"index": 0, "function": {"arguments": json.dumps(args)}}]}}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
        ]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for chunk in chunks:
            chunk.setdefault("id", "chatcmpl-stub")
            chunk.setdefault("object", "chat.completion.chunk")
            chunk.setdefault("created", 0)
            chunk.setdefault("model", model)
            self.wfile.write(sse(chunk))
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8398
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[stub] model server on 127.0.0.1:{port}", flush=True)
    server.serve_forever()
