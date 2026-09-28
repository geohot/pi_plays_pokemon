"""HTTP API tests for the emulator sidecar (emu.py), using a synthetic ROM."""
import io
import json

from PIL import Image

import emu
from conftest import get, get_json, post


def test_reset_creates_evidence(sidecar, tmp_path):
    run_dir = tmp_path / "runs" / "test"
    assert (run_dir / "frames" / "step-000.png").exists()
    assert json.loads((run_dir / "run.json").read_text())["rom_sha256"]
    assert (run_dir / "actions.jsonl").read_text() == ""


def test_status(sidecar):
    status, body = get_json(sidecar, "/status")
    assert status == 200
    assert body["run"] == "test"
    assert body["step"] == 0
    assert body["mode"] == "fresh"
    assert body["last"] is None


def test_screen_png_scales(sidecar):
    status, data = get(sidecar, "/screen.png")
    assert status == 200
    assert Image.open(io.BytesIO(data)).size == (480, 432)  # default scale 3

    _, data = get(sidecar, "/screen.png?scale=1")
    assert Image.open(io.BytesIO(data)).size == (160, 144)

    _, data = get(sidecar, "/screen.png?scale=99")  # clamped to 6
    assert Image.open(io.BytesIO(data)).size == (960, 864)


def test_act_buttons_and_validation(sidecar):
    for button in ["a", "b", "start", "select", "up", "down", "left", "right", None]:
        status, entry = post(sidecar, "/act", {"button": button, "frames": 8, "presses": 2})
        assert status == 200
        assert entry["button"] == button
        if button is None:
            assert entry["emulated_frames"] == 8
        else:
            assert entry["emulated_frames"] == 2 * (8 + emu.SETTLE_FRAMES)

    for bad in [{"button": "turbo"}, {"frames": 0}, {"frames": 121}, {"presses": 5}]:
        status, body = post(sidecar, "/act", bad)
        assert status == 400
        assert "error" in body


def test_act_advances_steps_and_logs(sidecar, tmp_path):
    post(sidecar, "/act", {"button": "up", "frames": 8})
    post(sidecar, "/act", {"button": None, "frames": 30})

    status, body = get_json(sidecar, "/log")
    assert body["step"] == 2
    assert [a["button"] for a in body["actions"]] == ["up", None]

    run_dir = tmp_path / "runs" / "test"
    lines = (run_dir / "actions.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    assert (run_dir / "frames" / "step-002.png").exists()

    status, body = get_json(sidecar, "/status")
    assert body["last"]["button"] is None


def test_static_rom_reports_zero_change(sidecar):
    _, entry = post(sidecar, "/act", {"button": "a", "frames": 16})
    assert entry["changed"] == 0.0


def test_campaign_state_saved_in_resume_mode(sidecar, tmp_path):
    # fixture booted fresh: no state saved on act
    post(sidecar, "/act", {"button": "a", "frames": 8})
    assert not emu._campaign_path().exists()

    status, body = post(sidecar, "/reset?fresh=0")  # resume mode
    assert status == 200
    post(sidecar, "/act", {"button": "a", "frames": 8})
    assert emu._campaign_path().exists()
    assert emu._campaign_path().stat().st_size > 0
    assert "campaign-" in emu._campaign_path().name  # keyed to the ROM

    _, body = get_json(sidecar, "/status")
    assert body["mode"] == "resume"
    assert body["campaign"] is True


def test_agent_feed_merges_streams(sidecar):
    post(sidecar, "/agent", {"kind": "thinking", "text": "let me "})
    post(sidecar, "/agent", {"kind": "thinking", "text": "think"})
    post(sidecar, "/agent", {"kind": "action", "text": "act(a)"})

    _, body = get_json(sidecar, "/agent")
    kinds = [(e["kind"], e["text"]) for e in body["entries"]]
    assert ("thinking", "let me think") in kinds
    assert ("action", "act(a)") in kinds


def test_ui_page_served(sidecar):
    status, body = get(sidecar, "/")
    assert status == 200
    assert b"<title>Game Boy</title>" in body
