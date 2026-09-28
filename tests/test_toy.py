"""End-to-end tests against the toy cartridge (toy/toy.gb).

The toy ROM is original test homebrew (see toy/toy.asm): a square the d-pad
moves, A inverts the palette, B restores it, Start resets. It lets CI verify
the whole loop - button press in, changed pixels out - without a copyrighted
ROM. Skipped when the cartridge has not been built (`make toy/toy.gb`).
"""
import io
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import emu  # noqa: E402
from conftest import TOY_ROM, get, get_json, post  # noqa: E402

pytestmark = pytest.mark.skipif(not TOY_ROM.exists(),
                                reason="toy cartridge not built (run: make toy/toy.gb)")


@pytest.fixture()
def toy(tmp_path, monkeypatch):
    monkeypatch.setattr(emu, "ROM", TOY_ROM)
    monkeypatch.setattr(emu, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(emu, "_rom_cache", None)
    emu.RUNS.mkdir()
    emu.reset("toy", fresh=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), emu.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    emu._emu.stop()


def sprite_box(png: bytes):
    """Bounding box of the darkest pixels (the square) in a screenshot."""
    import numpy as np
    img = Image.open(io.BytesIO(png)).convert("L")
    ys, xs = np.where(np.asarray(img) < 100)
    return (int(xs.min()), int(ys.min())) if len(xs) else None


def test_toy_idle_screen_is_static(toy):
    _, entry = post(toy, "/act", {"button": None, "frames": 60})
    assert entry["changed"] == 0.0


def test_toy_dpad_moves_the_square(toy):
    _, before = get(toy, "/screen.png?scale=1")
    _, entry = post(toy, "/act", {"button": "right", "frames": 60})
    assert entry["changed"] > 0
    _, after = get(toy, "/screen.png?scale=1")

    x0, y0 = sprite_box(before)
    x1, y1 = sprite_box(after)
    assert x1 > x0          # moved right
    assert y1 == y0         # did not drift vertically


def test_toy_a_flashes_and_b_restores(toy):
    _, entry = post(toy, "/act", {"button": "a", "frames": 16})
    assert entry["changed"] > 0.9     # palette invert: the whole screen flips

    _, entry = post(toy, "/act", {"button": "b", "frames": 16})
    assert entry["changed"] > 0.9     # and flips back


def test_toy_start_resets_position(toy):
    _, before = get(toy, "/screen.png?scale=1")
    post(toy, "/act", {"button": "right", "frames": 60})
    post(toy, "/act", {"button": "start", "frames": 16})
    _, after = get(toy, "/screen.png?scale=1")
    assert sprite_box(after) == sprite_box(before)


def test_toy_campaign_resume_keeps_position(toy):
    post(toy, "/reset?fresh=0")       # resume mode: save state on every act
    post(toy, "/act", {"button": "right", "frames": 60})
    _, moved = get(toy, "/screen.png?scale=1")

    post(toy, "/reset?fresh=0")       # new run, same campaign
    _, resumed = get(toy, "/screen.png?scale=1")
    assert sprite_box(resumed) == sprite_box(moved)

    _, body = get_json(toy, "/status")
    assert body["mode"] == "resume"
