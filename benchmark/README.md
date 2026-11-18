# PokeVision: can the model see what is on a Pokemon Red screen?

337 direct questions about single Pokemon Red screenshots, in 10 categories. One screenshot and one question a
request, no history, JSON answer. Every correct answer comes from **emulator memory** or from **a cloned emulator
pressing the button**, never from a model. The screens are real moments from the agent games in `../runs`: the
emulator states the sidecar saved after each action. So these are the screens a playing agent actually gets.

Images are sent at **480x432** (nearest-neighbour 3x, the harness's and PokeBench's wire size), as a PNG data URL.

| group | category | n | question (short) | truth from |
|---|---|---:|---|---|
| reading | `text` | 36 | transcribe the dialogue box (2 lines) | tile map `wTileMap` rows 14 / 16 |
| reading | `cursor` | 36 | which menu entry the ▶ cursor is on (start / battle / move / item / yes-no / PC menus) | tile map: the text right of the 0xED tile |
| reading | `enemy_name` | 30 | the opposing Pokemon's name | battle HUD row 0 |
| reading | `enemy_level` | 30 | its level | HUD row 1, must equal `wEnemyMonLevel` |
| reading | `player_hp` | 30 | your Pokemon's HP `cur/max` | HUD numbers (only while the battle HUD is drawn) |
| graphics | `enemy_hp_bar` | 32 | enemy HP bar full / more than half / less than half / empty | bar tiles (0x63+n = n px of 48); must agree with `wEnemyMonHP/MaxHP` (so the bar is not mid-animation); a margin around 1/2 and near full is left out |
| graphics | `facing` | 36 | which way the player sprite faces | `wSpritePlayerStateData1FacingDirection` |
| graphics | `npc_count` | 36 | how many people / Pokemon besides the player | sprite table, image index != 0xFF; must equal the drawn OAM entries / 4; still objects (balls, books) left out |
| scene | `walkable` | 36 | if the player pressed `<dir>` once, would they move? (18 true / 18 false) | clone the emulator, tap the button with the harness timing (8 + 96 frames), did map/x/y change; done twice (now and 30 frames later), kept only if both agree; scenes with no way out are left out (scripted) |
| scene | `place` | 35 | outdoors / house / lab / pokemon_center / poke_mart (+ gym, gate, forest, museum as wrong options) | map id (pret `map_constants.asm`) |

Answers are balanced inside a category (e.g. 9 per facing direction), with at most a few screens from one game or
map and never the same screen twice. Scoring is exact match after light normalization: case, whitespace, accents,
quote styles, and `NIDORAN♂` ≈ `NIDORAN`. No answer, invalid JSON or a reply cut off at the token limit counts as wrong.
These are also counted separately. **Macro** is the mean of the 10 category accuracies.

## Results (Nov 18, llm.tinygrad.win, each model's default sampling, max_tokens 16384)

`/v1/models` lists four models. Three of them accept pictures. **`zai-org/GLM-5.3` does not**: the gateway drops
the image (131 prompt tokens against ~390 with the picture), and the model says it got no image or hallucinates tool
calls. It is kept as a **blind control**: what the questions give away without sight.

| model | macro | correct | reading | graphics | scene | text | cursor | e_name | e_level | p_hp | hp_bar | facing | npc | walk | place |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| claude-opus-5-5, thinking high (calibration) | **96.6** | 325/337 | 100 | 92.6 | 94.3 | 100 | 100 | 100 | 100 | 100 | 100 | 78 | 100 | 100 | 89 |
| claude-opus-5-5, thinking off (calibration) | **95.5** | 321/337 | 100 | 91.7 | 90.1 | 100 | 100 | 100 | 100 | 100 | 100 | 75 | 100 | 94 | 86 |
| moonshotai/Kimi-K3.1-Pro (run 1 / run 2) | **91.4 / 92.3** | 307 / 310 | 100 / 99.4 | 79 / 82 | 89 / 90 | 100/97 | 100 | 100 | 100 | 100 | 84/91 | 56/56 | 97/100 | 97/97 | 80/83 |
| qwen/Qwen3.8-Flash-Next (run 1 / run 2) | **82.6 / 82.0** | 276 / 274 | 97.8 / 97.7 | 68 / 64 | 66 / 70 | 89/92 | 100 | 100 | 100/97 | 100 | 69/72 | 47/36 | 89/83 | 75/81 | 57/60 |
| zai-org/GLM-5.3-Flash | **77.3** | 259 | 90.7 | 64.5 | 63.4 | 86 | 97 | 100 | 73 | 97 | 66 | 39 | 89 | 64 | 63 |
| zai-org/GLM-5.3 (no vision on the gateway: blind control) | 11.1 | 38 | 3 | 14 | 27 | 0 | 0 | 7 | 10 | 0 | 16 | 22 | 3 | 36 | 17 |
| guessing the most common answer | 21.6 | | | | | 3 | 6 | 27 | 27 | 3 | 31 | 25 | 25 | 50 | 20 |

Full tables with k/n, 95% Wilson intervals, invalid / no-final counts, latency and output tokens:
[`results/SCORES.md`](results/SCORES.md). Raw replies: `results/<model>.jsonl`. With n = 30-36, one category cell
has a ±10-15 point interval; the macro and the group columns are the numbers to compare.

What it says:
- **Reading the screen is solved** for every vision model here (Kimi and Qwen 98-100%). GLM-5.3-Flash loses a
  little: 3 of its 8 level misses and several others are replies cut off at 16,384 tokens of thinking.
- **The open models fall behind on graphics and scene understanding.** Examples: which way the player faces,
  how full the enemy HP bar is, whether a step is blocked, and what kind of building this is. Qwen and GLM-Flash
  are near chance on facing (36-47%; chance 25%) and only 57-64% on place. These are the skills the agent's walls
  in `../runs` point at (e.g. taking an ordinary house for a Pokemon Center).
- **Facing "right" is a blind spot for every model, the calibrator included.** 4 items are missed by all 7 vision
  runs, all four with truth `right`. They were checked by eye on 8x crops (the cap brim and face point right).
  Models mostly answer `down`.
- **GLM-5.3-Flash thinks itself out of answers on `walkable`.** 12 of 36 replies hit the 16,384-token limit with no
  final answer (median 98 s a question). Over the whole set it has 24 cut-off replies; Qwen has 2-4, Kimi 0-1.
- Run-to-run spread with default sampling: Kimi 91.4 vs 92.3, Qwen 82.6 vs 82.0.

## Calibration (with myself, claude-opus-5-5)

The calibrator is the model that built this, run through the same item files and the same question text. The run
goes through the pi CLI with the screenshot attached (`run.py --pi anthropic/claude-opus-5-5`). Every item the
calibrator got wrong, and every item two or more models got wrong the same way, was looked at by eye against the
truth (`sheet.py`). Contact sheets of every category were also read before the first model run. A truth was changed
only when it was wrong or not decidable from the picture. An item was never dropped because a model missed it.

Truth bugs this found and fixed (the item set was then rebuilt and every model run again from scratch; the first
run is archived in `work/run1/`):
1. `player_hp` matched `PP 10/35` on a Pokemon summary page opened during a battle. HP is now read only while the
   battle HUD is on screen.
2. `npc_count`: in Pokemon Centers, the man on the bench is drawn into the background tiles, not as a sprite. Memory
   said 2 people while the picture shows 3. Pokemon Center screens are left out of this category (checked by turning
   sprites off and rendering the frame again).
3. `text`: odd player names made of glyph soup (`JJ);;[[`, tiny `PK` ligature tiles). The models' spacing and
   readings of these were defensible either way. Texts are now limited to letters, digits and `.,!?'-:`.
4. Scoring: `POKèMON` for `POKéMON` is now accepted (accents are ignored).

Kept on purpose, though hard:
- `place` items inside Pokemon Centers seen from the entrance: the counter is off screen, but the potted plants,
  floor and bench are visible. A player who knows the game can tell, and the calibrator got 2 of 7. These are the
  game's hard cases.
- The facing items above.

Calibrator misses that remain (16 with thinking off, 12 with high): facing 9 / 8, place 5 / 4, walkable 2 / 0. All
are its own errors on checked truths. So the ceiling is not 100%, and the remaining misses are real vision misses.

## Use

```sh
# from the repo root. Build (only needs the repo's .venv with pyboy; reads ../runs and ../roms, writes benchmark/)
.venv/bin/python benchmark/build.py census --states 30000   # ~1.5 min on 48 cores -> benchmark/work/census.jsonl (16 MB, not tracked)
.venv/bin/python benchmark/build.py select                  # -> benchmark/data/{items.jsonl,frames/,states/} (same bytes every time)
.venv/bin/python benchmark/build.py verify                  # re-derive all 337 truths from data/states (local, see below)

# ask a model (Python + Pillow; key from ~/.pi/agent/models.json provider 'tinygrad' or $PV_API_KEY; resumable)
python3 benchmark/run.py --model qwen/Qwen3.8-Flash-Next --workers 6
python3 benchmark/run.py --model X --url http://host:port/v1 --name X-local    # any OpenAI-compatible server
python3 benchmark/run.py --pi anthropic/claude-opus-5-5 --thinking high --name claude-opus-5-5-high
python3 benchmark/run.py --model X --limit 2                                    # dry run: 2 items a category

python3 benchmark/score.py                  # -> results/SCORES.md, results/scores.json
python3 benchmark/sheet.py facing --answers benchmark/results/Kimi-K3.1-Pro.jsonl   # eye review sheet -> work/sheets/
```

What is committed (about 2.2 MB, 356 files): the code, `data/items.jsonl` (questions, truths and the source state of each),
`data/frames/<id>.png` (the native 160x144 screenshot, sent 3x as 480x432) and `results/` (replies, parsed answers,
usage, timing). Not committed (`.gitignore`): `data/states/` (the settled emulator state behind each picture: it
holds copies of game data, so it stays local; `build.py select` rebuilds it from `../runs` and `build.py verify`
re-checks every truth against it), `work/` (the census list, eye-review sheets, the first pre-fix run in
`work/run1/`, the models' thinking text) and `logs/`.
`gb.py` holds every memory address with its pret source; question text and scoring live in `questions.py`, the
only place they are defined.

## Relation to earlier work

`llm_inference_company/results/scout/vision-probe` (phase 5) asked Qwen, Kimi and GLM five kinds of questions
(text, cursor, HP, movement, entrances) on 40 frames each, to choose a picture size. This benchmark was built
separately and borrows two ideas from it: memory truth and cloned-press movement truth. It differs in these ways:
- 10 categories, balanced answers, and frames drawn from 212 games rather than 5 (the census read 29,105 saved
  states of 391 games).
- A settle step: every picture and its truth are read together after 60 idle frames, and screens still changing
  are left out.
- Drawn-vs-memory cross-checks: HP bar tiles against memory, OAM against the sprite table, and two press timings.
- One question per walk direction instead of all four at once.
- An entrance list dropped in favour of the `place` question.
- A blind control and a calibrator run.
