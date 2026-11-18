#!/usr/bin/env python3
"""Build the PokeVision item set from the emulator states the harness saved in ../runs.

  census:  sample saved post-action states across many games, settle each 60 frames with no input, and record what the
           game's memory says about the settled screen (truth) plus the screenshot (native 160x144).
  select:  draw a balanced, de-duplicated set of questions per category -> data/items.jsonl + data/frames/ + data/states/

Truth comes only from emulator memory or from cloned-emulator button presses, never from a model.
usage (from the repo root, read-only on everything outside benchmark/):
  .venv/bin/python benchmark/build.py census --states 9000
  .venv/bin/python benchmark/build.py select
"""
import argparse
import hashlib
import io
import json
import lzma
import multiprocessing as mp
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RUNS = REPO / "runs"
ROM = REPO / "roms" / "pokemon_red.gb"
WORK = HERE / "work"
DATA = HERE / "data"
sys.path.insert(0, str(HERE))
import gb  # noqa: E402

SETTLE = 60          # idle frames after loading a state: the picture and the truth are both read at the end
PRESS, RELEASE = 8, 96   # the harness's own press timing (emu.py PRESS_FRAMES / SETTLE_FRAMES)
DIRS = ("up", "down", "left", "right")

_pb = None


def emulator():
    global _pb
    if _pb is None:
        import warnings
        warnings.filterwarnings("ignore")
        from pyboy import PyBoy
        _pb = PyBoy(io.BytesIO(ROM.read_bytes()), window="null", sound_emulated=False)
        _pb.set_emulation_speed(0)
    return _pb


def snapshot(pb):
    buf = io.BytesIO()
    pb.save_state(buf)
    buf.seek(0)
    return buf


def where(m):
    return (m[gb.CUR_MAP], m[gb.X_COORD], m[gb.Y_COORD])


def can_step(pb, base, d, idle):
    """Clone the settled emulator, idle `idle` frames, tap `d` once like the harness does: did the player move (or warp)?"""
    base.seek(0)
    pb.load_state(base)
    if idle:
        pb.tick(idle, False, False)
    before = where(pb.memory)
    pb.button_press(d)
    pb.tick(PRESS, False, False)
    pb.button_release(d)
    pb.tick(RELEASE, False, False)
    return where(pb.memory) != before


def settled(src):
    """Load a saved state and idle SETTLE frames exactly as the census did: the screenshot and the settled state."""
    pb = emulator()
    with open(RUNS / src, "rb") as fh:
        pb.load_state(fh)
    pb.tick(SETTLE - 20, True, False)
    pb.tick(10, True, False)
    pb.tick(10, True, False)
    return pb.screen.image.convert("RGB"), snapshot(pb).getvalue()


def census_one(path):
    pb = emulator()
    try:
        with open(path, "rb") as fh:
            pb.load_state(fh)
        pb.tick(SETTLE - 20, True, False)
        m = pb.memory
        t40 = gb.tiles(m)
        spr40 = gb.visible_sprites(m)
        pb.tick(10, True, False)
        spr50 = gb.visible_sprites(m)
        pb.tick(10, True, False)
        t = gb.tiles(m)
        img = pb.screen.image.convert("RGB")
        spr = gb.visible_sprites(m)
        oam = sum(1 for i in range(40) if pb.get_sprite(i).on_screen)
        mask = lambda tt: [[x if (r, c) != (16, 18) else 0 for c, x in enumerate(row)] for r, row in enumerate(tt)]  # noqa: E731
        rec = {
            "src": str(path.relative_to(RUNS)),
            "map": m[gb.CUR_MAP], "x": m[gb.X_COORD], "y": m[gb.Y_COORD], "tileset": m[gb.TILESET],
            "battle": m[gb.IS_IN_BATTLE], "facing": gb.FACING.get(m[gb.PLAYER_FACING]),
            "walk": m[gb.WALK_COUNTER], "joy_ignore": m[gb.JOY_IGNORE],
            "tiles_stable": mask(t40) == mask(t), "sprites_stable": spr50 == spr and spr40 == spr,
            "box": gb.dialogue_box(t), "arrows": gb.arrows(t), "screen_text": gb.screen_text(t),
            "sprites": spr, "oam_visible": oam,
            "img_sha": hashlib.sha256(img.tobytes()).hexdigest()[:16],
        }
        if rec["box"]:
            rec["dialogue"] = gb.dialogue_text(t)
        if rec["arrows"]:
            rec["cursor"] = [gb.cursor_label(t, r, c) for r, c in rec["arrows"]]
        if rec["battle"]:
            rec["hud"] = gb.battle_hud(t)
            rec["enemy_hp"], rec["enemy_max_hp"] = gb.word(m, gb.ENEMY_HP), gb.word(m, gb.ENEMY_MAX_HP)
            rec["enemy_level_ram"] = m[gb.ENEMY_LEVEL]
        overworld = (not rec["battle"] and not rec["box"] and not rec["arrows"] and rec["walk"] == 0
                     and rec["joy_ignore"] == 0 and rec["tiles_stable"])
        rec["overworld"] = overworld
        state = snapshot(pb)
        if overworld:
            a = {d: can_step(pb, state, d, 0) for d in DIRS}
            b = {d: can_step(pb, state, d, 30) for d in DIRS}
            rec["can_step"] = {d: a[d] for d in DIRS if a[d] == b[d]}
        return rec
    except Exception as e:  # a corrupt or foreign state: skip it, say so
        return {"src": str(path), "error": repr(e)}


def game_of(path):
    name = path.relative_to(RUNS).parts[0]
    return re.sub(r"-block-\d+$", "", name)


def census(a):
    files = sorted(RUNS.glob("*/states/step-*.state"))
    games = defaultdict(list)
    for f in files:
        if game_of(f).startswith(("qwen38", "glm53f")):   # real Pokemon Red games (not e2e / toy / probe runs)
            games[game_of(f)].append(f)
    rng = random.Random(a.seed)
    per_game = max(1, a.states // len(games))
    chosen = []
    for g in sorted(games):
        fs = games[g]
        chosen.extend(rng.sample(fs, min(per_game, len(fs))))
    rng.shuffle(chosen)
    chosen = chosen[:a.states]
    print(f"{len(files)} saved states in {len(games)} games; census of {len(chosen)} ({per_game} a game at most)", flush=True)
    WORK.mkdir(exist_ok=True)
    n = 0
    with (WORK / "census.jsonl").open("w") as fh, mp.Pool(a.workers) as pool:
        for rec in pool.imap_unordered(census_one, chosen, chunksize=8):
            rec["game"] = game_of(RUNS / rec["src"]) if "error" not in rec else None
            fh.write(json.dumps(rec) + "\n")
            n += 1
            if n % 500 == 0:
                print("census", n, flush=True)
    print("census done", n)


# ---------------------------------------------------------------- selection

def norm_place(rec):
    return gb.PLACE.get(rec["map"])


def text_ok(s):
    """Non-empty, and no PK / MN ligature glyphs inside names (tiny 'PK' tiles: not transcribable unambiguously)."""
    return (bool(s.strip()) and not re.search(r"PK(?!MN)|(?<!PK)MN", s)
            and re.fullmatch(r"[A-Za-z0-9é .,!?'\n:-]+", s) is not None)   # no [ ] ; ( ) ♂ ♀ glyph soup from odd player names


def candidates(recs):
    """category -> list of (record, question fields). Every candidate already passed its truth checks."""
    c = defaultdict(list)
    for r in recs:
        if "error" in r or not r["tiles_stable"]:
            continue
        # 1 text: transcribe a settled dialogue box
        if r["box"] and text_ok(r.get("dialogue", "")) and not r["arrows"]:
            c["text"].append((r, {"answer": r["dialogue"]}))
        # 2 cursor: exactly one filled cursor, a plain label, no naming keyboard
        if (len(r["arrows"]) == 1 and "NAME" not in r["screen_text"] and "lower case" not in r["screen_text"]
                and "TEXT SPEED" not in r["screen_text"]):
            lab = r["cursor"][0]
            if re.fullmatch(r"[A-Za-z0-9é .'-]{2,12}", lab):
                c["cursor"].append((r, {"answer": lab}))
        # 3-6 battle HUD reads
        if r["battle"] and r.get("hud"):
            h = r["hud"]
            if "enemy_name" in h:
                c["enemy_name"].append((r, {"answer": h["enemy_name"]}))
                if h["enemy_level"] == r["enemy_level_ram"]:
                    c["enemy_level"].append((r, {"answer": h["enemy_level"]}))
            if "player_hp" in h and "enemy_name" in h:   # the battle HUD, not a status / summary page
                c["player_hp"].append((r, {"answer": h["player_hp"]}))
            if "enemy_bar_px" in h and r["enemy_max_hp"]:
                px = h["enemy_bar_px"]                          # what is drawn; memory must agree (no bar animating)
                ram_px = 48 * r["enemy_hp"] / r["enemy_max_hp"]
                bucket = ("full" if px == 48 else "more_than_half" if 28 <= px <= 43 else
                          "less_than_half" if 4 <= px <= 20 else "empty" if px == 0 else None)
                if bucket and abs(px - ram_px) <= 1.5:
                    c["enemy_hp_bar"].append((r, {"answer": bucket, "bar_px": px}))
        if not r["overworld"]:
            continue
        # 7 facing
        if r["facing"]:
            c["facing"].append((r, {"answer": r["facing"]}))
        # 8 count of people / Pokemon on screen (game memory and drawn sprites agree; no still objects)
        spr = r["sprites"]
        # (Pokemon Centers: the man on the bench is drawn into the background, not a sprite -> left out)
        if r["tileset"] != 6 and r["sprites_stable"] and r["oam_visible"] == 4 * (len(spr) + 1) and all(s["picture"] < gb.FIRST_OBJECT_SPRITE for s in spr):
            inside = all(0 <= s["x"] <= 144 and 0 <= s["y"] <= 124 for s in spr)
            if inside:
                c["npc_count"].append((r, {"answer": len(spr)}))
        # 9 can the player step in one direction (two press timings agree; scenes with no way out are scripted: dropped)
        cs = r.get("can_step", {})
        if len(cs) == 4 and any(cs.values()) and r["sprites_stable"]:
            for d, v in cs.items():
                c["walkable"].append((r, {"direction": d, "answer": v}))
        # 10 kind of place
        if norm_place(r):
            c["place"].append((r, {"answer": norm_place(r)}))
    return c


TARGET = {"text": 36, "cursor": 36, "enemy_name": 30, "enemy_level": 30, "player_hp": 30, "enemy_hp_bar": 32,
          "facing": 36, "npc_count": 36, "walkable": 36, "place": 35}
MAP_CAP = {"place": 8, "walkable": 2, "facing": 2}   # same-map, same-answer screens allowed per cap step (default 3)


def pick(cands, n, key, rng, map_cap=3):
    """Draw n candidates: one screen at most once, at most 2 a game (relaxed if short), spread over answer values for `key`."""
    rng.shuffle(cands)
    groups = defaultdict(list)
    for r, q in cands:
        groups[str(q[key]) if key else "all"].append((r, q))
    out, seen_img, per_game, per_map = [], set(), Counter(), Counter()
    order = sorted(groups)
    rng.shuffle(order)
    for cap in (1, 2, 4, 1000):
        progress = True
        while len(out) < n and progress:
            progress = False
            for g in order:
                if len(out) >= n:
                    break
                for i, (r, q) in enumerate(groups[g]):
                    if r["img_sha"] in seen_img or per_game[r["game"]] >= cap or per_map[(r["map"], str(q.get("answer")))] >= map_cap * cap:
                        continue
                    out.append((r, q))
                    seen_img.add(r["img_sha"])
                    per_game[r["game"]] += 1
                    per_map[(r["map"], str(q.get("answer")))] += 1
                    groups[g].pop(i)
                    progress = True
                    break
    return out


def select(a):
    recs = [json.loads(x) for x in (WORK / "census.jsonl").open()]
    cands = candidates(recs)
    for k, v in sorted(cands.items()):
        print(f"{k:13s} candidates {len(v):5d}  answers {Counter(str(q['answer']) for _, q in v).most_common(8)}")
    if DATA.exists():
        shutil.rmtree(DATA)
    (DATA / "frames").mkdir(parents=True)
    (DATA / "states").mkdir()
    items = []
    for cat, n in TARGET.items():
        rng = random.Random(f"{a.seed}-{cat}")   # one stream a category: changing one category leaves the others as they are
        chosen = pick(list(cands[cat]), n, "answer", rng, MAP_CAP.get(cat, 3))
        for i, (r, q) in enumerate(sorted(chosen, key=lambda x: (x[0]["game"], x[0]["src"]))):
            iid = f"{cat}-{i:03d}"
            img, state = settled(r["src"])     # re-rendered from ../runs: the census keeps no pictures
            if hashlib.sha256(img.tobytes()).hexdigest()[:16] != r["img_sha"]:
                raise SystemExit(f"{iid}: {r['src']} does not settle to the census screen")
            img.save(DATA / "frames" / (iid + ".png"))     # native 160x144; run.py sends it 3x (480x432)
            with lzma.open(DATA / "states" / (iid + ".state.xz"), "wb", preset=9) as fh:
                fh.write(state)                            # ~167 KB raw, ~1-2 KB xz
            item = {"id": iid, "category": cat, **q, "source": r["src"], "game": r["game"], "map": r["map"],
                    "x": r["x"], "y": r["y"], "img_sha": r["img_sha"]}
            if cat == "npc_count":
                item["sprites"] = r["sprites"]
            if cat == "walkable":
                item["can_step"] = r["can_step"]
            items.append(item)
        print(f"{cat:13s} selected {len(chosen):3d}  {Counter(str(q['answer']) for _, q in chosen).most_common(10)}")
    with (DATA / "items.jsonl").open("w") as fh:
        for it in items:
            fh.write(json.dumps(it) + "\n")
    print("items", len(items))


def verify(_):
    """Re-derive every truth from the shipped data/states/<id>.state.xz and compare with items.jsonl and the frame."""
    from PIL import Image
    if not (DATA / "states").is_dir():
        raise SystemExit("data/states/ is not committed (it holds game data): run `build.py census` + `select` first")
    pb = emulator()
    bad = 0
    items = [json.loads(x) for x in (DATA / "items.jsonl").open()]
    for it in items:
        with lzma.open(DATA / "states" / (it["id"] + ".state.xz")) as fh:
            state = io.BytesIO(fh.read())
        pb.load_state(state)
        screen = pb.screen.image.convert("RGB").tobytes()   # the saved screen buffer
        m, t = pb.memory, gb.tiles(pb.memory)
        frame = Image.open(DATA / "frames" / (it["id"] + ".png")).convert("RGB").tobytes()
        cat, want = it["category"], it["answer"]
        h = gb.battle_hud(t) if m[gb.IS_IN_BATTLE] else {}
        got = {"text": lambda: gb.dialogue_text(t),
               "cursor": lambda: gb.cursor_label(t, *gb.arrows(t)[0]),
               "enemy_name": lambda: h.get("enemy_name"),
               "enemy_level": lambda: h.get("enemy_level"),
               "player_hp": lambda: h.get("player_hp"),
               "enemy_hp_bar": lambda: want if h.get("enemy_bar_px") == it["bar_px"] else h.get("enemy_bar_px"),
               "facing": lambda: gb.FACING.get(m[gb.PLAYER_FACING]),
               "npc_count": lambda: len(gb.visible_sprites(m)),
               "walkable": lambda: can_step(pb, state, it["direction"], 0),
               "place": lambda: gb.PLACE.get(m[gb.CUR_MAP])}[cat]()
        same = hashlib.sha256(frame).hexdigest()[:16] == it["img_sha"] == hashlib.sha256(screen).hexdigest()[:16]
        if got != want or not same:
            bad += 1
            print("MISMATCH", it["id"], "item", repr(want), "state", repr(got), "frame ok" if same else "frame differs")
    print(f"verify: {len(items) - bad}/{len(items)} truths re-derived from data/states")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("--states", type=int, default=9000)
    c.add_argument("--workers", type=int, default=32)
    c.add_argument("--seed", type=int, default=20261118)
    c.set_defaults(fn=census)
    s = sub.add_parser("select")
    s.add_argument("--seed", type=int, default=20261118)
    s.set_defaults(fn=select)
    sub.add_parser("verify").set_defaults(fn=verify)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
