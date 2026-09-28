"""Shared fixtures: run emu.py's HTTP API in-process against a test ROM.

The generated ROM is the smallest program PyBoy accepts: an infinite loop at
the entry point. It draws nothing and ignores input, so tests that need a ROM
that *responds* to buttons use toy/toy.gb instead (see test_toy.py).
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import emu  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TOY_ROM = ROOT / "toy" / "toy.gb"


def make_test_rom(path: Path) -> None:
    """Smallest valid 32 KiB ROM: `nop; jp $100` loops forever."""
    rom = bytearray(0x8000)
    rom[0x100:0x104] = bytes([0x00, 0xC3, 0x00, 0x01])
    rom[0x134:0x13C] = b"PIPLA\0\0\0"          # title
    rom[0x147] = 0x00                          # cartridge type: ROM only
    rom[0x148] = 0x00                          # ROM size: 32 KiB
    rom[0x149] = 0x00                          # RAM size: none
    chk = 0
    for i in range(0x134, 0x14D):
        chk = (chk - rom[i] - 1) & 0xFF
    rom[0x14D] = chk                           # header checksum
    path.write_bytes(rom)


@pytest.fixture()
def sidecar(tmp_path, monkeypatch):
    """emu.py's handler on an ephemeral port, isolated runs dir, test ROM."""
    rom = tmp_path / "test.gb"
    make_test_rom(rom)
    monkeypatch.setattr(emu, "ROM", rom)
    monkeypatch.setattr(emu, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(emu, "_rom_cache", None)
    emu.RUNS.mkdir()
    emu.reset("test", fresh=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), emu.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    yield base
    server.shutdown()
    emu._emu.stop()


def get(base, path):
    with urllib.request.urlopen(base + path) as res:
        return res.status, res.read()


def get_json(base, path):
    status, body = get(base, path)
    return status, json.loads(body)


def post(base, path, payload=None, raw=None):
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else b"")
    req = urllib.request.Request(base + path, data=data,
                                 headers={"content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")
