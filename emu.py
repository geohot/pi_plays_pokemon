#!/usr/bin/env python3
"""Minimal Game Boy sidecar: owns the emulator, serves screenshots + a tiny web UI.

Endpoints (all interfaces, port 8341 by default):
  GET  /              lightweight web UI (live screen + action log + agent feed)
  GET  /screen.png    current frame (optional ?scale=2..6, default 3)
  GET  /status        json: run id, step count, last action
  GET  /log           json: recorded actions for the current run
  GET  /agent         json: the agent's live reasoning/text/action feed
  POST /agent         {kind, text}: append to the agent feed (stream.py posts)
  POST /act           {"button": "a"|"b"|...|null, "frames": 1..120, "presses": 1..4}
  POST /reset         fresh boot; optional ?name=RUN-ID for the evidence folder

Pixels in, button presses out. No game state is read from the emulator.

Configuration via environment:
  ROM_PATH   path to the .gb file (default: roms/pokemon_red.gb)
  EMU_PORT   HTTP port (default: 8341)
"""
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
from PIL import Image
from pyboy import PyBoy

ROOT = Path(__file__).parent
ROM = Path(os.environ.get("ROM_PATH", ROOT / "roms" / "pokemon_red.gb"))
RUNS = ROOT / "runs"
PORT = int(os.environ.get("EMU_PORT", "8341"))
SETTLE_FRAMES = 96          # released frames after each press (matches proven runs)
BOOT_FRAMES = 240           # frames advanced on a fresh boot before first capture
BUTTONS = {"a", "b", "start", "select", "up", "down", "left", "right"}

_lock = threading.Lock()
_emu = None
_run_dir = None
_step = 0
_actions = []
_agent = []          # rolling reasoning/text/action feed for the web UI
_campaign = False    # resume mode: persist emulator state across runs


_rom_cache = None


def _rom_bytes():
    global _rom_cache
    if _rom_cache is None:
        _rom_cache = ROM.read_bytes()
    return _rom_cache


def _campaign_path():
    """Campaign state is per ROM: a state saved by one game crashes another."""
    sha = hashlib.sha256(_rom_bytes()).hexdigest()[:16]
    return RUNS / f"campaign-{sha}.state"


def _new_emulator():
    # A byte stream stops PyBoy from reading/writing a shared <rom>.ram file.
    emu = PyBoy(io.BytesIO(_rom_bytes()), window="null", sound_emulated=False)
    emu.set_emulation_speed(0)
    return emu


def _frame():
    return _emu.screen.image.convert("RGB").copy()


def _png(image, scale=1):
    buf = io.BytesIO()
    if scale != 1:
        image = image.resize((160 * scale, 144 * scale), Image.Resampling.NEAREST)
    image.save(buf, "PNG")
    return buf.getvalue()


def _changed(a, b):
    x = np.asarray(a, dtype=np.int16)
    y = np.asarray(b, dtype=np.int16)
    return float(np.mean(np.max(abs(x - y), axis=2) > 20))


def reset(name=None, fresh=False):
    global _emu, _run_dir, _step, _actions, _agent, _campaign
    with _lock:
        _emu = _new_emulator()
        # fresh: boot the ROM from scratch. Otherwise resume the campaign
        # state if there is one - progress accumulates across runs. A state
        # that fails to load (corrupt, wrong emulator version) falls back to
        # a fresh boot rather than killing the run.
        _campaign = not fresh
        state = _campaign_path()
        if _campaign and state.exists():
            try:
                with state.open("rb") as fh:
                    _emu.load_state(fh)
            except Exception as exc:
                print(f"[emu] campaign state failed to load ({exc}); booting fresh", flush=True)
                _emu.tick(BOOT_FRAMES, render=True, sound=False)
        else:
            _emu.tick(BOOT_FRAMES, render=True, sound=False)
        _step = 0
        _actions = []
        _agent = []
        safe = re.sub(r"[^A-Za-z0-9._-]", "-", name or time.strftime("run-%Y%m%d-%H%M%S"))
        _run_dir = RUNS / safe
        (_run_dir / "frames").mkdir(parents=True, exist_ok=True)
        shot = _frame()
        (_run_dir / "frames" / "step-000.png").write_bytes(_png(shot))
        (_run_dir / "actions.jsonl").write_text("")
        meta = {"rom_sha256": hashlib.sha256(_rom_bytes()).hexdigest(),
                "boot_frames": BOOT_FRAMES, "settle_frames": SETTLE_FRAMES,
                "started_at": time.time()}
        (_run_dir / "run.json").write_text(json.dumps(meta, indent=2))
        return {"run": _run_dir.name, "step": 0}


def act(button, frames, presses=1):
    global _step
    if button is not None and button not in BUTTONS:
        raise ValueError(f"bad button {button!r}")
    frames = int(frames)
    presses = int(presses)
    if not 1 <= frames <= 120:
        raise ValueError("frames must be 1..120")
    if not 1 <= presses <= 4:
        raise ValueError("presses must be 1..4")
    with _lock:
        before = _frame()
        held = 0
        if button is None:
            _emu.tick(frames, render=True, sound=False)
            held = frames
        else:
            for _ in range(presses):
                _emu.button_press(button)
                try:
                    _emu.tick(frames, render=True, sound=False)
                    held += frames
                finally:
                    _emu.button_release(button)
                _emu.tick(SETTLE_FRAMES, render=True, sound=False)
                held += SETTLE_FRAMES
        after = _frame()
        _step += 1
        entry = {"step": _step, "button": button, "frames": frames, "presses": presses,
                 "emulated_frames": held, "changed": round(_changed(before, after), 4),
                 "ts": time.time()}
        if _campaign:
            with _campaign_path().open("wb") as fh:
                _emu.save_state(fh)
        _actions.append(entry)
        with (_run_dir / "actions.jsonl").open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
        (_run_dir / "frames" / f"step-{_step:03d}.png").write_bytes(_png(after))
        return entry


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode())

    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path == "/":
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif url.path == "/screen.png":
                scale = int(parse_qs(url.query).get("scale", ["3"])[0])
                with _lock:
                    data = _png(_frame(), max(1, min(scale, 6)))
                self._send(200, data, "image/png")
            elif url.path == "/status":
                with _lock:
                    self._json({"run": _run_dir.name if _run_dir else None, "step": _step,
                                "mode": "resume" if _campaign else "fresh",
                                "campaign": _campaign_path().exists(),
                                "last": _actions[-1] if _actions else None})
            elif url.path == "/log":
                with _lock:
                    self._json({"run": _run_dir.name if _run_dir else None,
                                "step": _step, "actions": list(_actions)})
            elif url.path == "/agent":
                with _lock:
                    self._json({"entries": list(_agent)})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as exc:  # surface errors to the caller
            self._json({"error": str(exc)}, 500)

    def do_POST(self):
        url = urlparse(self.path)
        try:
            if url.path == "/reset":
                q = parse_qs(url.query)
                fresh = q.get("fresh", ["0"])[0] in ("1", "true", "yes")
                self._json(reset(q.get("name", [None])[0], fresh=fresh))
            elif url.path == "/agent":
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                kind = str(body.get("kind", "text"))[:16]
                text = str(body.get("text", ""))
                with _lock:
                    # Streamed reasoning/text deltas merge into one growing
                    # paragraph; actions and results are always new entries.
                    if kind in ("thinking", "text") and _agent and _agent[-1]["kind"] == kind:
                        _agent[-1]["text"] += text
                    else:
                        _agent.append({"kind": kind, "text": text, "ts": time.strftime("%H:%M:%S")})
                    del _agent[:-2000]
                self._json({"ok": True})
            elif url.path == "/act":
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                self._json(act(body.get("button"), body.get("frames", 8), body.get("presses", 1)))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, *args):
        pass


PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Game Boy</title>
<style>
 body { background:#111; color:#ddd; font:14px/1.5 monospace; margin:16px; }
 img { image-rendering: pixelated; width:480px; border:1px solid #333; }
 #status { margin:8px 0; color:#8f8; }
 #cols { display:flex; gap:24px; align-items:flex-start; }
 #agent { max-width:640px; max-height:70vh; overflow-y:auto; white-space:pre-wrap; }
 #agent .thinking { color:#888; font-style:italic; }
 #agent .text { color:#ddd; }
 #agent .action { color:#8f8; }
 #agent .result { color:#9af; }
 #agent .turn { color:#fc6; margin-top:8px; }
 #agent .ts { color:#555; margin-right:6px; }
 table { border-collapse:collapse; margin-top:12px; }
 td, th { border:1px solid #333; padding:2px 8px; text-align:left; }
 tr:first-child { color:#999; }
</style>
<div id="status">connecting...</div>
<div id="cols">
 <div><img id="screen" src="/screen.png?scale=3">
  <div id="log"></div></div>
 <div id="agent"></div>
</div>
<script>
async function tick() {
  try {
    const s = await (await fetch("/status")).json();
    document.getElementById("status").textContent =
      `run ${s.run} - step ${s.step} - ${s.campaign ? "RESUMED campaign state" : "fresh boot"}` + (s.last
        ? ` - last: ${s.last.button ?? "wait"} ${s.last.frames}f x${s.last.presses} (change ${(s.last.changed*100).toFixed(1)}%)`
        : "");
    document.getElementById("screen").src = "/screen.png?scale=3&t=" + Date.now();
    const l = await (await fetch("/log")).json();
    const rows = l.actions.slice(-200).reverse().map(a =>
      `<tr><td>${a.step}</td><td>${a.button ?? "wait"}</td><td>${a.frames}f x${a.presses}</td><td>${(a.changed*100).toFixed(1)}%</td></tr>`);
    document.getElementById("log").innerHTML =
      "<table><tr><th>step</th><th>button</th><th>hold</th><th>change</th></tr>" + rows.join("") + "</table>";
    const ag = await (await fetch("/agent")).json();
    const box = document.getElementById("agent");
    const near = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    box.innerHTML = ag.entries.map(e =>
      `<div class="${e.kind}">` +
      (e.kind === "turn"
        ? `— model returned ${e.text} —`
        : `<span class="ts">${e.ts ?? ""}</span>` +
          (e.kind === "action" ? "-> " : e.kind === "result" ? "<- " : "") +
          e.text.replace(/</g,"<")) +
      `</div>`).join("");
    if (near) box.scrollTop = box.scrollHeight;
  } catch (e) { document.getElementById("status").textContent = "offline: " + e; }
}
setInterval(tick, 500); tick();
</script>
"""


def main():
    RUNS.mkdir(exist_ok=True)
    reset(sys.argv[1] if len(sys.argv) > 1 else None)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[emu] http://localhost:{PORT} (bound to 0.0.0.0) run={_run_dir.name}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
