#!/usr/bin/env bash
# End-to-end: real pi + the real game extension + the real emulator sidecar,
# playing the toy cartridge with a scripted stub model server.
#
# Requires: pi on PATH, .venv with requirements.txt installed, toy/toy.gb
# built (make toy/toy.gb). Everything model-side is fake; everything else
# is the production code path.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f toy/toy.gb ]; then
  echo "toy cartridge not built - run: make toy/toy.gb" >&2
  exit 1
fi

EMU_PORT="${E2E_EMU_PORT:-8399}"
STUB_PORT="${E2E_STUB_PORT:-8398}"
RUN="e2e-$(date +%s)"
AGENT_DIR="$(mktemp -d)"

python3 tests/stub_model.py "$STUB_PORT" &
STUB_PID=$!
trap 'kill $STUB_PID 2>/dev/null || true
      [ -f runs/emu.pid ] && kill "$(cat runs/emu.pid)" 2>/dev/null
      rm -rf "$AGENT_DIR" "runs/$RUN"' EXIT

cat > "$AGENT_DIR/models.json" <<EOF
{"providers": {"stub": {
  "baseUrl": "http://127.0.0.1:$STUB_PORT/v1",
  "api": "openai-completions",
  "apiKey": "local",
  "models": [{
    "id": "stub-1", "name": "Stub Model",
    "input": ["text", "image"],
    "reasoning": false,
    "contextWindow": 32768, "maxTokens": 1024,
    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}
  }]
}}}
EOF

echo "[e2e] run=$RUN (emu :$EMU_PORT, stub :$STUB_PORT)"
mkdir -p "runs/$RUN"
export ROM_PATH="$PWD/toy/toy.gb"
export EMU_PORT
export EMU_URL="http://127.0.0.1:$EMU_PORT"
export PI_CODING_AGENT_DIR="$AGENT_DIR"
export RUN_NAME="$RUN"
export PI_FRESH=1

timeout 180 pi -a \
  --provider stub --model stub-1 \
  --mode json \
  --session-dir "runs/$RUN/session" \
  "Beat the game." 2>&1 | tee "runs/$RUN/events.jsonl" | python3 -u stream.py || {
  echo "[e2e] pi run failed" >&2
  exit 1
}

python3 - "$RUN" <<'EOF'
import json
import sys
from pathlib import Path

run = Path("runs") / sys.argv[1]

result = json.loads((run / "result.json").read_text())
assert result["done"] is True, f"stub did not report done: {result}"

actions = [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines()]
buttons = [a["button"] for a in actions]
assert buttons == ["right", "a"], f"unexpected action sequence: {buttons}"
assert actions[0]["changed"] > 0, "the right press changed no pixels"
assert actions[1]["changed"] > 0.9, "the A press should flash the screen"

frames = sorted((run / "frames").glob("step-*.png"))
assert len(frames) == 3, f"expected boot + 2 action frames, got {len(frames)}"

events = (run / "events.jsonl").read_text()
assert '"tool_execution_end"' in events, "no tool executions in the event stream"

log = [json.loads(line) for line in (run / "model_requests.jsonl").read_text().splitlines()]
assert [e["kind"] for e in log] == ["act", "act", "report"], f"unexpected request log: {log}"

print("[e2e] PASS: pi played the toy cartridge (look, right, A, report done)")
EOF
