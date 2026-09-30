# pi plays Pokémon

[pi](https://github.com/earendil-works/pi) — the pi coding agent — plays a Game
Boy game. A very lightweight agent: a pi extension gives the model three tools
(screenshots in, button presses out), and a tiny web UI shows the live screen,
the action log, and the model's streaming reasoning.

Nothing about the game is hardcoded: the prompt is just "beat the game", and
the model's own `report()` verdict decides the result.

## Status

The harness works and is fully tested (see below), but current open-weight
models are not yet smart enough to play: MiMo gets stuck in loops in the first
room. Frontier models can do it, so this repo is ready for when open models
catch up — switch pi to any provider it supports and watch.

## Setup (once)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Drop a Game Boy ROM you own at `roms/pokemon_red.gb` (or set `ROM_PATH`).
ROMs are copyrighted and are not in this repo; the test suite uses its own
toy cartridge instead.

`pi` must be installed (`npm i -g @earendil-works/pi-coding-agent`) and set up
as usual — runs use pi's normal global config and default model, which must
accept image input. For long runs on small-context local models, enable
auto-compaction in pi's global `~/.pi/agent/settings.json`.

## Play

```sh
pi -a "Beat the game."
```

That is the whole interface. The extension boots the emulator sidecar on the
first tool call (`emu.py`, reusing an already-running one), and restricts pi
to the three game tools. `-a` trusts the project extension for the run.

- Web UI: **http://localhost:8341** (bound to `0.0.0.0`, so reachable from
  other machines too) — live screen, action log, and the model's reasoning.
- Pick a model for one run with pi's own flags:
  `pi -a --provider openai --model gpt-5-mini "Beat the game."`
- Headless, with the event stream saved and pretty-printed:
  `pi -a --mode json "Beat the game." | tee events.jsonl | python3 -u stream.py`
- Evidence lands in `runs/<run>/`: per-step screenshots (`frames/`), the
  action log, the request log and `result.json` (the model's verdict).
  Name the run yourself with `RUN_NAME=my-run`.
- One run at a time: runs share the single emulator and sidecar.

## Campaign state (runs/campaign-<rom>.state)

A game run **resumes** by default: the emulator state is saved after every
action and reloaded on the next run, so progress accumulates across runs (a
30-hour game cannot be beaten if every run reboots the ROM). A resumed run
therefore starts wherever the last one ended — not in the bedroom. The state
is keyed to the ROM, so different games never clobber each other.

- Start the game over: `PI_FRESH=1 pi -a "Beat the game."`
- The web UI says which mode a run is in.

## Testing

CI runs three jobs (`.github/workflows/ci.yml`):

| Job | What it covers |
| --- | --- |
| `python` | `pytest tests/` — the sidecar HTTP API, run evidence, campaign resume, agent feed, and the `stream.py` event mirror |
| `shell` | `shellcheck` on all scripts |
| `e2e` | the **full loop**: real pi, the real extension and a real emulator against a scripted stub model server |

The e2e job (and the toy-ROM tests) use `toy/toy.gb`: a tiny homebrew
cartridge built from `toy/toy.asm` with [RGBDS](https://rgbds.gbdev.io)
(`make toy/toy.gb`). It is original code — a square the d-pad moves, A
flashes the screen — so the whole pipeline can be tested without a
copyrighted ROM. Without the toy built, those tests skip cleanly.

## What is where

| File | Purpose |
| --- | --- |
| `emu.py` | emulator sidecar: screenshots, button presses, web UI (port 8341) |
| `stream.py` | pretty-prints pi's `--mode json` event stream |
| `.pi/SYSTEM.md` | the whole prompt: beat the game |
| `.pi/extensions/game.ts` | `look` / `act` / `report` tools; boots the sidecar |
| `toy/toy.asm` | the toy test cartridge (RGBDS assembly) |
| `tests/` | pytest suite, stub model, e2e script |

Environment variables: `ROM_PATH`, `EMU_PORT`, `EMU_URL`, `RUN_NAME`,
`PI_FRESH`, `PI_IMAGE_SCALE`, `REQUEST_LOG`.

## License

MIT (the code here). Game Boy ROMs are not included; bring your own.
