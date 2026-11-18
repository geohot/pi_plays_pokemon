#!/usr/bin/env python3
"""Contact sheets for eye review: data/frames at 2x with the item id and (optionally) the truth / model answers under each.
usage: python sheet.py <category> [--no-truth] [--answers results/<model>.jsonl ...] [--ids a,b,c] -> work/sheets/<name>.png"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("--no-truth", action="store_true")
    ap.add_argument("--answers", nargs="*", default=[])
    ap.add_argument("--ids", default="")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    items = [json.loads(x) for x in (HERE / "data" / "items.jsonl").open()]
    if a.category != "all":
        items = [i for i in items if i["category"] == a.category]
    if a.ids:
        want = set(a.ids.split(","))
        items = [i for i in items if i["id"] in want]
    answers = []
    for f in a.answers:
        rows = {}
        for x in open(f):
            r = json.loads(x)
            rows[r["id"]] = r
        answers.append((Path(f).stem, rows))
    font = ImageFont.load_default()
    w, h, pad = 320, 288, 16 * (2 + len(answers))
    cols = a.cols
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 8), rows * (h + pad + 8)), "white")
    d = ImageDraw.Draw(sheet)
    for k, it in enumerate(items):
        x, y = (k % cols) * (w + 8), (k // cols) * (h + pad + 8)
        im = Image.open(HERE / "data" / "frames" / (it["id"] + ".png")).resize((w, h), Image.Resampling.NEAREST)
        sheet.paste(im, (x, y))
        q = f" {it['direction']}" if "direction" in it else ""
        d.text((x + 2, y + h + 1), f"{it['id']}{q}", fill="black", font=font)
        if not a.no_truth:
            d.text((x + 2, y + h + 15), "T: " + json.dumps(it["answer"], ensure_ascii=False)[:60], fill="blue", font=font)
        for j, (name, rows_) in enumerate(answers):
            r = rows_.get(it["id"], {})
            col = "green" if r.get("correct") else "red"
            d.text((x + 2, y + h + 29 + 14 * j), f"{name[:10]}: {str(r.get('parsed'))[:48]}", fill=col, font=font)
    out = HERE / "work" / "sheets" / ((a.name or a.category) + ".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
