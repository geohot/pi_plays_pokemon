#!/usr/bin/env bash
# Stop the emulator sidecar started by .pi/extensions/game.ts.
set -euo pipefail
cd "$(dirname "$0")"

pid_file="runs/emu.pid"
if [[ ! -f "$pid_file" ]]; then
  echo "Game Boy server is not running (no $pid_file)."
  exit 0
fi

pid=$(<"$pid_file")
if [[ ! "$pid" =~ ^[0-9]+$ ]] || (( pid <= 1 )); then
  echo "Invalid PID in $pid_file: $pid" >&2
  exit 1
fi

if ! kill -0 "$pid" 2>/dev/null; then
  echo "Game Boy server is not running (stale PID $pid)."
  rm -f "$pid_file"
  exit 0
fi

# Do not kill an unrelated process if the PID has been recycled.
is_emu=false
while IFS= read -r -d '' arg; do
  if [[ "$arg" == "emu.py" || "$arg" == */emu.py ]]; then
    is_emu=true
    break
  fi
done < "/proc/$pid/cmdline"

if [[ "$is_emu" != true ]]; then
  echo "Refusing to kill PID $pid: it is not emu.py." >&2
  exit 1
fi

kill "$pid"
rm -f "$pid_file"
echo "Stopped Game Boy server (PID $pid)."
