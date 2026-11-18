#!/usr/bin/env python3
"""Ask a model every PokeVision question: one screenshot (480x432 PNG data URL), one question, no history.

  python run.py --model moonshotai/Kimi-K3.1-Pro                 # OpenAI-compatible endpoint (default llm.tinygrad.win)
  python run.py --pi anthropic/claude-opus-5-5 --name claude     # any pi provider, through the pi CLI (calibration)

Output: results/<name>.jsonl, one row a question (resumable: rows without an error are kept and skipped);
the model's thinking text goes to work/reasoning/<name>.jsonl (large, not part of the benchmark).
The API key is read from ~/.pi/agent/models.json (provider 'tinygrad') or $PV_API_KEY, never printed or written.
"""
import argparse
import base64
import concurrent.futures as cf
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from questions import SYSTEM, correct, parse, question  # noqa: E402

DEFAULT_URL = "https://llm.tinygrad.win/v1"


def api_key():
    if os.environ.get("PV_API_KEY"):
        return os.environ["PV_API_KEY"]
    cfg = json.loads((Path.home() / ".pi/agent/models.json").read_text())
    return cfg["providers"]["tinygrad"]["apiKey"]


def wire_png(item):
    """The native 160x144 frame, 3x nearest-neighbour = 480x432 (the harness's / PokeBench's wire size)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.open(HERE / "data" / "frames" / (item["id"] + ".png")).resize((480, 432), Image.Resampling.NEAREST).save(buf, "PNG")
    return buf.getvalue()


def ask_openai(a, key, item):
    img = base64.b64encode(wire_png(item)).decode()
    body = {"model": a.model, "max_tokens": a.max_tokens, "stream": False,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + img}},
                                                      {"type": "text", "text": question(item)}]}]}
    if a.temperature is not None:
        body["temperature"] = a.temperature
    if a.reasoning_effort:
        body["reasoning_effort"] = a.reasoning_effort
    req = urllib.request.Request(a.url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=a.timeout) as fh:
        r = json.load(fh)
    ch = r["choices"][0]
    msg = ch["message"]
    return {"reply": msg.get("content") or "", "reasoning": msg.get("reasoning_content") or msg.get("reasoning"),
            "finish": ch.get("finish_reason"), "usage": r.get("usage")}


def ask_pi(a, _key, item):
    provider, model = a.pi.split("/", 1)
    with tempfile.TemporaryDirectory() as d:   # empty cwd: no project context files or extensions
        img = Path(d) / "screen.png"
        img.write_bytes(wire_png(item))
        cmd = ["pi", "-p", "--no-session", "--no-tools", "-ne", "-ns", "-np", "-nc", "--no-mcp", "--offline",
               "--provider", provider, "--model", model, "--thinking", a.thinking, "--system-prompt", SYSTEM,
               "@screen.png", question(item)]
        p = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=a.timeout)
    if p.returncode != 0:
        raise RuntimeError(f"pi rc {p.returncode}: {p.stderr[-300:]}")
    return {"reply": p.stdout.strip(), "reasoning": None, "finish": None, "usage": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="model id on the OpenAI-compatible endpoint")
    ap.add_argument("--pi", help="provider/model through the pi CLI instead (e.g. anthropic/claude-opus-5-5)")
    ap.add_argument("--thinking", default="off", help="pi thinking level (with --pi)")
    ap.add_argument("--name", help="results file name (default: model id with / -> _)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--temperature", type=float, default=None, help="default: the server's / model's own")
    ap.add_argument("--reasoning-effort", default=None)
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="first N items of each category (dry run)")
    ap.add_argument("--categories", default="")
    a = ap.parse_args()
    if not (a.model or a.pi):
        ap.error("--model or --pi")
    if a.pi:
        provider, model = a.pi.split("/", 1)
        p = subprocess.run(["pi", "--offline", "--provider", provider, "--model", model, "--list-models"],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0 or p.stderr.strip():
            ap.error(p.stderr.strip() or f"pi --list-models exited with status {p.returncode}")
    name = a.name or (a.model or a.pi).replace("/", "_")
    items = [json.loads(x) for x in (HERE / "data" / "items.jsonl").open()]
    if a.categories:
        items = [i for i in items if i["category"] in a.categories.split(",")]
    if a.limit:
        per = {}
        items = [i for i in items if per.setdefault(i["category"], []).append(i) or len(per[i["category"]]) <= a.limit]
    out = HERE / "results" / f"{name}.jsonl"
    out.parent.mkdir(exist_ok=True)
    (HERE / "work" / "reasoning").mkdir(parents=True, exist_ok=True)
    done = {}
    if out.exists():
        for x in out.open():
            r = json.loads(x)
            if "error" not in r:
                done[r["id"]] = r
    with out.open("w") as fh:
        for r in done.values():
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    todo = [i for i in items if i["id"] not in done]
    print(f"{name}: {len(items)} items, {len(done)} done, {len(todo)} to ask", flush=True)
    key = api_key() if a.model else None
    ask = ask_pi if a.pi else ask_openai
    lock = threading.Lock()

    def one(item):
        row = {"id": item["id"], "category": item["category"], "model": a.model or a.pi}
        for attempt in range(a.retries + 1):
            t = time.time()
            try:
                row.update(ask(a, key, item))
                row.pop("error", None)
                break
            except urllib.error.HTTPError as e:
                row["error"] = f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"
            except Exception as e:  # noqa: BLE001 - timeouts, resets: retried, then recorded
                row["error"] = repr(e)[:300]
            finally:
                row["seconds"] = round(time.time() - t, 2)
            time.sleep(5 * (attempt + 1))
        row["attempts"] = attempt + 1
        reasoning = row.pop("reasoning", None)
        if reasoning:
            row["reasoning_chars"] = len(reasoning)
            with lock:
                with (HERE / "work" / "reasoning" / f"{name}.jsonl").open("a") as f:
                    f.write(json.dumps({"id": item["id"], "reasoning": reasoning}, ensure_ascii=False) + "\n")
        row["parsed"] = parse(row.get("reply"))
        row["correct"] = correct(item, row["parsed"]) if "error" not in row else None
        with lock:
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    n = ok = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futures = [ex.submit(one, item) for item in todo]
        for future in cf.as_completed(futures):
            row = future.result()
            n += 1
            ok += bool(row.get("correct"))
            print(f"{name}: {n}/{len(todo)} asked, {ok} correct so far, {row['id']} {row['seconds']}s"
                  f"{' ERROR ' + row['error'][:80] if 'error' in row else ''}", flush=True)


if __name__ == "__main__":
    main()
