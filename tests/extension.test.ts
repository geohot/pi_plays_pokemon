// Unit tests for the pi game extension (look / act / report) against a stub
// emulator sidecar over HTTP. Run: npm test
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import http from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, beforeEach, test } from "node:test";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PNG_1PX = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);

interface ActBody { button: string | null; frames: number; presses: number }

const state = { step: 0, acts: [] as ActBody[] };

const server = http.createServer((req, res) => {
  const url = new URL(req.url ?? "/", "http://stub");
  const json = (obj: unknown) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(obj));
  };
  if (url.pathname === "/status") return json({ step: state.step });
  if (url.pathname === "/reset" && req.method === "POST") return json({ run: "stub", step: 0 });
  if (url.pathname === "/screen.png") {
    res.writeHead(200, { "content-type": "image/png" });
    return res.end(PNG_1PX);
  }
  if (url.pathname === "/act" && req.method === "POST") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      const parsed = JSON.parse(body) as ActBody;
      state.acts.push(parsed);
      state.step += 1;
      json({
        step: state.step, button: parsed.button, frames: parsed.frames,
        presses: parsed.presses, emulated_frames: parsed.frames, changed: 0.25, ts: 0,
      });
    });
    return;
  }
  res.writeHead(404);
  res.end();
});

type AnyTool = { name: string; execute: (...args: any[]) => Promise<any> };
const tools = new Map<string, AnyTool>();
const handlers = new Map<string, (event?: any) => unknown>();
const pi = {
  registerTool: (tool: AnyTool) => tools.set(tool.name, tool),
  on: (event: string, fn: (event?: any) => unknown) => handlers.set(event, fn),
} as unknown as ExtensionAPI;

const logDir = mkdtempSync(join(tmpdir(), "pi-plays-"));
process.env.REQUEST_LOG = join(logDir, "model_requests.jsonl");

before(async () => {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as { port: number };
  process.env.EMU_URL = `http://127.0.0.1:${port}`;
  const { default: register } = await import("../.pi/extensions/game.ts");
  register(pi);
});

after(() => server.close());

beforeEach(() => {
  state.step = 0;
  state.acts = [];
  handlers.get("session_start")?.();
});

const NO_ARGS = ["call-1", undefined, undefined, {}] as const;

function settleEvent(content: Array<{ type: string }>) {
  return { outcome: "settled", context: { contextMessages: [{ role: "assistant", content }] } };
}

test("registers look, act and report", () => {
  assert.deepEqual([...tools.keys()].sort(), ["act", "look", "report"]);
});

test("look returns the screen and does not act", async () => {
  state.step = 7;
  const result = await tools.get("look")!.execute(...NO_ARGS, {});
  assert.equal(result.content[0].type, "text");
  assert.match(result.content[0].text, /step 7/);
  assert.equal(result.content[1].type, "image");
  assert.equal(Buffer.from(result.content[1].data, "base64").compare(PNG_1PX), 0);
  assert.equal(state.acts.length, 0);
});

test("act posts the press and returns summary + screen", async () => {
  const result = await tools.get("act")!.execute(
    "call-1", { button: "right", frames: 16, presses: 2 }, undefined, undefined, {});
  assert.deepEqual(state.acts, [{ button: "right", frames: 16, presses: 2 }]);
  assert.match(result.content[0].text, /step 1: right 16f x2, screen change 25\.0%/);
  assert.equal(result.content[1].type, "image");
});

test('act maps "wait" to a null button', async () => {
  const result = await tools.get("act")!.execute(
    "call-1", { button: "wait", frames: 60, presses: 1 }, undefined, undefined, {});
  assert.deepEqual(state.acts, [{ button: null, frames: 60, presses: 1 }]);
  assert.match(result.content[0].text, /wait 60f/);
});

test("concurrent acts are serialized in order", async () => {
  const act = tools.get("act")!;
  const [r1, r2] = await Promise.all([
    act.execute("call-1", { button: "up", frames: 8, presses: 1 }, undefined, undefined, {}),
    act.execute("call-2", { button: "down", frames: 8, presses: 1 }, undefined, undefined, {}),
  ]);
  assert.deepEqual(state.acts.map((a) => a.button), ["up", "down"]);
  assert.match(r1.content[0].text, /step 1/);
  assert.match(r2.content[0].text, /step 2/);
});

test("act logs every request", async () => {
  await tools.get("act")!.execute(
    "call-1", { button: "a", frames: 16, presses: 1 }, undefined, undefined, {});
  const log = readFileSync(process.env.REQUEST_LOG!, "utf8").trim().split("\n");
  const entry = JSON.parse(log[log.length - 1]);
  assert.equal(entry.kind, "act");
  assert.equal(entry.button, "a");
});

test("report writes result.json and terminates", async () => {
  const result = await tools.get("report")!.execute(
    "call-1", { done: false, note: "gave up" }, undefined, undefined, {});
  assert.equal(result.terminate, true);
  const written = JSON.parse(readFileSync(join(logDir, "result.json"), "utf8"));
  assert.equal(written.done, false);
  assert.equal(written.note, "gave up");
});

test("a text-only reply gets nudged back to tools, at most 5 times", async () => {
  const settle = handlers.get("agent_before_settle")!;
  const event = settleEvent([{ type: "text" }]);
  for (let i = 0; i < 5; i++) {
    const nudge = settle(event) as { continue: boolean; entries: unknown[] };
    assert.equal(nudge.continue, true);
    assert.equal(nudge.entries.length, 1);
  }
  assert.equal(settle(event), undefined);  // gives up after 5 nudges
});

test("no nudge when the last message already calls a tool", () => {
  const settle = handlers.get("agent_before_settle")!;
  assert.equal(settle(settleEvent([{ type: "toolCall" }])), undefined);
});

test("no nudge after report or when aborted", async () => {
  const settle = handlers.get("agent_before_settle")!;
  const event = settleEvent([{ type: "text" }]);
  await tools.get("report")!.execute(
    "call-1", { done: true, note: "done" }, undefined, undefined, {});
  assert.equal(settle(event), undefined);

  handlers.get("session_start")?.();
  assert.equal(settle({ ...event, outcome: "aborted" }), undefined);
});

test("request log file was created", () => {
  assert.ok(existsSync(process.env.REQUEST_LOG!));
});
