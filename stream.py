#!/usr/bin/env python3
"""Pretty-print pi's JSONL agent event stream and mirror it to the web UI.

Reads pi --mode json events from stdin, prints a live text stream to stdout,
and posts reasoning/text/action blocks to the emulator sidecar (/agent) so the
web UI can show what the model is thinking.
"""
import json
import os
import sys
import time
import urllib.request

EMU = os.environ.get("EMU_URL", "http://127.0.0.1:8341")
DIM = "\033[2m" if sys.stdout.isatty() else ""
OFF = "\033[27m" if sys.stdout.isatty() else ""

buf_kind, buf_text, buf_at = None, "", 0.0


def push(kind, text):
    if not text:
        return
    try:
        req = urllib.request.Request(
            f"{EMU}/agent", data=json.dumps({"kind": kind, "text": text}).encode(),
            headers={"content-type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass  # the terminal stream stays authoritative


def flush():
    global buf_kind, buf_text
    push(buf_kind or "text", buf_text)
    buf_kind, buf_text = None, ""


def buffer(kind, text):
    global buf_kind, buf_text, buf_at
    if buf_kind != kind:
        flush()
        buf_kind, buf_at = kind, time.monotonic()
    buf_text += text
    if len(buf_text) > 400 or time.monotonic() - buf_at > 0.4:
        flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "message_start":
            if (event.get("message") or {}).get("role") == "assistant":
                flush()
                push("turn", time.strftime("%H:%M:%S"))
        elif kind == "message_update":
            update = event.get("assistantMessageEvent") or {}
            sub = update.get("type")
            if sub == "thinking_delta":
                buffer("thinking", update.get("delta", ""))
                sys.stdout.write(DIM + update.get("delta", "") + OFF)
            elif sub == "text_delta":
                buffer("text", update.get("delta", ""))
                sys.stdout.write(update.get("delta", ""))
            elif sub == "toolcall_start":
                flush()
                sys.stdout.write(f"\n-> {update.get('toolName')}(")
            elif sub == "toolcall_delta":
                sys.stdout.write(update.get("delta", ""))
            sys.stdout.flush()
        elif kind == "message_end":
            flush()
            print()
        elif kind == "tool_execution_end":
            flush()
            texts = [c.get("text", "") for c in (event.get("result") or {}).get("content", [])
                     if c.get("type") == "text"]
            first = (texts[0] if texts else "").strip().splitlines()
            summary = first[0] if first else ""
            push("result", f"{event.get('toolName')}: {summary}")
            print(f"\n<- {summary}")
        elif kind == "compaction_start":
            flush()
            print(f"\n-- compaction ({event.get('reason')}) --")
        elif kind == "agent_settled":
            flush()
            print("-- settled --")
    flush()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        flush()
        print("\n[stream] stopped")
