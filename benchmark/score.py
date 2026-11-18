#!/usr/bin/env python3
"""Score results/*.jsonl against data/items.jsonl -> results/SCORES.md + results/scores.json.

Accuracy counts every item (errors, no-final replies and invalid JSON are wrong); they are also reported separately.
The headline is the macro mean over categories (each category weighs the same); 95% Wilson intervals per cell.
usage: python score.py [results/a.jsonl ...]   (default: every results/*.jsonl)
"""
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from questions import cer, correct  # noqa: E402

CATS = ["text", "cursor", "enemy_name", "enemy_level", "player_hp", "enemy_hp_bar", "facing", "npc_count", "walkable", "place"]
# what guessing the most common answer (or a uniform choice) would score, from the item set itself
GROUP = {"reading": ["text", "cursor", "enemy_name", "enemy_level", "player_hp"],
         "graphics": ["enemy_hp_bar", "facing", "npc_count"],
         "scene": ["walkable", "place"]}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    items = {i["id"]: i for i in map(json.loads, (HERE / "data" / "items.jsonl").open())}
    files = [Path(f) for f in sys.argv[1:]] or sorted((HERE / "results").glob("*.jsonl"))
    by_cat = {c: [i for i in items.values() if i["category"] == c] for c in CATS}
    majority = {}
    for c, its in by_cat.items():
        counts = {}
        for i in its:
            counts[str(i["answer"])] = counts.get(str(i["answer"]), 0) + 1
        majority[c] = max(counts.values()) / len(its)
    table = {}
    for f in files:
        rows = {}
        for x in f.open():
            r = json.loads(x)
            rows[r["id"]] = r  # last row of an id wins (resumed runs)
        s = {"file": f.name, "cats": {}, "n_rows": len(rows)}
        for c in CATS:
            its = by_cat[c]
            got = [rows.get(i["id"]) for i in its]
            ok = [bool(r) and "error" not in r and correct(items[r["id"]], r.get("parsed")) for r in got]
            k, n = sum(ok), len(its)
            done = [r for r in got if r and "error" not in r]
            cell = {"k": k, "n": n, "acc": k / n, "ci": wilson(k, n), "missing": sum(r is None for r in got),
                    "errors": sum(1 for r in got if r and "error" in r),
                    "invalid": sum(1 for r in done if r.get("parsed") is None),
                    "no_final": sum(1 for r in done if r.get("finish") == "length"),
                    "median_s": round(statistics.median([r["seconds"] for r in done]), 1) if done else None,
                    "median_out_tokens": statistics.median([(r.get("usage") or {}).get("completion_tokens") or 0 for r in done])
                    if done and any(r.get("usage") for r in done) else None}
            if c == "text":
                cers = [min(1.0, cer(str(r.get("parsed") or ""), items[r["id"]]["answer"])) if r and "error" not in r else 1.0
                        for r in got]
                cell["mean_cer"] = sum(cers) / len(cers)
            s["cats"][c] = cell
        s["macro"] = sum(s["cats"][c]["acc"] for c in CATS) / len(CATS)
        s["groups"] = {g: sum(s["cats"][c]["acc"] for c in cs) / len(cs) for g, cs in GROUP.items()}
        s["micro"] = (sum(s["cats"][c]["k"] for c in CATS), sum(s["cats"][c]["n"] for c in CATS))
        table[f.stem] = s
    order = sorted(table, key=lambda m: -table[m]["macro"])
    out = ["# PokeVision scores", "",
           f"{len(items)} questions in {len(CATS)} categories; one 480x432 screenshot a question, no history. "
           "Accuracy %, every item counts (no answer = wrong). Macro = mean of the 10 category accuracies.", "",
           "| model | macro | reading | graphics | scene | correct/all | " + " | ".join(CATS) + " |",
           "|---|---:|---:|---:|---:|---:|" + "---:|" * len(CATS)]
    for m in order:
        s = table[m]
        out.append(f"| {m} | **{100 * s['macro']:.1f}** | " + " | ".join(f"{100 * s['groups'][g]:.1f}" for g in GROUP)
                   + f" | {s['micro'][0]}/{s['micro'][1]} | "
                   + " | ".join(f"{100 * s['cats'][c]['acc']:.0f}" for c in CATS) + " |")
    out.append("| *majority-answer baseline* | " + f"{100 * sum(majority.values()) / len(CATS):.1f} | | | | | "
               + " | ".join(f"{100 * majority[c]:.0f}" for c in CATS) + " |")
    out += ["", "## Per category: k/n, 95% Wilson interval, invalid / no-final / errors, median seconds and output tokens", ""]
    for c in CATS:
        out += [f"### {c} (n={len(by_cat[c])})", "", "| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |"
                + (" mean CER |" if c == "text" else ""), "|---|---:|---:|---|---:|---:|---:|---:|---:|" + ("---:|" if c == "text" else "")]
        for m in order:
            x = table[m]["cats"][c]
            out.append(f"| {m} | {x['k']}/{x['n']} | {100 * x['acc']:.1f} | {100 * x['ci'][0]:.0f}-{100 * x['ci'][1]:.0f} | "
                       f"{x['invalid']} | {x['no_final']} | {x['errors'] + x['missing']} | {x['median_s']} | {x['median_out_tokens']} |"
                       + (f" {x['mean_cer']:.3f} |" if c == "text" else ""))
        out.append("")
    (HERE / "results" / "SCORES.md").write_text("\n".join(out) + "\n")
    (HERE / "results" / "scores.json").write_text(json.dumps(table, indent=1))
    print("\n".join(out[:8 + len(order)]))


if __name__ == "__main__":
    main()
