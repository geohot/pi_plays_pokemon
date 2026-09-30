/**
 * game.ts - pi plays a Game Boy game: screenshots in, button presses out.
 *
 * The emulator sidecar (emu.py) owns the Game Boy and the web UI. This
 * extension starts it on demand and points it at a fresh run directory, so
 * playing is just:  pi -a "Beat the game."
 *
 * Environment:
 *   EMU_URL     sidecar address (default http://127.0.0.1:8341)
 *   RUN_NAME    evidence directory under runs/ (default: run-<timestamp>)
 *   PI_FRESH    set to boot the ROM from scratch instead of resuming the
 *               campaign state
 *   REQUEST_LOG where to log model-visible actions (default: the run dir)
 *   PI_IMAGE_SCALE  screenshot scale sent to the model (default 4)
 */
import { spawn } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, openSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const EMU = process.env.EMU_URL ?? "http://127.0.0.1:8341";
const IMAGE_SCALE = Number(process.env.PI_IMAGE_SCALE ?? 4);

let requestLog = process.env.REQUEST_LOG ?? "";
let chain: Promise<unknown> = Promise.resolve();
let ready: Promise<void> | null = null;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function up(): Promise<boolean> {
  try {
    return (await fetch(`${EMU}/status`)).ok;
  } catch {
    return false;
  }
}

// First tool call in a session starts the sidecar if needed and resets it
// into this session's run directory. Everything the model does lands under
// runs/<run>/.
function ensureEmu(): Promise<void> {
  ready ??= (async () => {
    if (!(await up())) {
      mkdirSync(join(ROOT, "runs"), { recursive: true });
      const fd = openSync(join(ROOT, "runs", "emu.log"), "a");
      const python = existsSync(join(ROOT, ".venv/bin/python"))
        ? join(ROOT, ".venv/bin/python")
        : "python3";
      const child = spawn(python, [join(ROOT, "emu.py")], {
        cwd: ROOT, detached: true, stdio: ["ignore", fd, fd],
      });
      child.unref();
      writeFileSync(join(ROOT, "runs", "emu.pid"), String(child.pid));
      for (let i = 0; i < 100 && !(await up()); i++) await sleep(200);
      if (!(await up())) {
        throw new Error(`emulator sidecar did not start - see ${join(ROOT, "runs", "emu.log")}`);
      }
    }
    const name = process.env.RUN_NAME ??
      `run-${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}`;
    const fresh = process.env.PI_FRESH ? "&fresh=1" : "";
    const res = await fetch(`${EMU}/reset?name=${name}${fresh}`, { method: "POST" });
    if (!res.ok) throw new Error(`emulator reset failed: ${res.status}`);
    requestLog ||= join(ROOT, "runs", name, "model_requests.jsonl");
  })();
  return ready;
}

function logRequest(line: object) {
  try {
    mkdirSync(dirname(requestLog), { recursive: true });
    appendFileSync(requestLog, JSON.stringify({ ts: new Date().toISOString(), ...line }) + "\n");
  } catch { /* logging must never break play */ }
}

async function screen(): Promise<{ type: "image"; data: string; mimeType: string }> {
  const res = await fetch(`${EMU}/screen.png?scale=${IMAGE_SCALE}`);
  if (!res.ok) throw new Error(`emulator screenshot failed: ${res.status}`);
  const data = Buffer.from(await res.arrayBuffer()).toString("base64");
  return { type: "image", data, mimeType: "image/png" };
}

async function status(): Promise<{ step: number }> {
  const res = await fetch(`${EMU}/status`);
  return await res.json() as { step: number };
}

const BUTTONS = ["a", "b", "up", "down", "left", "right", "start", "select", "wait"] as const;

const look = defineTool({
  name: "look",
  label: "Look",
  description: "Return the current Game Boy screen without pressing anything.",
  parameters: Type.Object({}),

  async execute(_id, _params, _signal, _onUpdate, _ctx) {
    const run = chain.then(async () => {
      await ensureEmu();
      const s = await status();
      return {
        content: [
          { type: "text" as const, text: `Current screen (step ${s.step}):` },
          await screen(),
        ],
        details: { step: s.step },
      };
    });
    chain = run.catch(() => undefined);
    return run;
  },
});

const act = defineTool({
  name: "act",
  label: "Act",
  description:
    "Press one Game Boy button held `frames` frames at 60fps, release it, let the game " +
    "settle, then return the new screen and how much it changed. " +
    'Use button "wait" to let `frames` frames pass without input. One act = one step.',
  parameters: Type.Object({
    button: Type.Union(
      BUTTONS.map((b) => Type.Literal(b)),
      { description: 'Button to press, or "wait" for no input' },
    ),
    frames: Type.Optional(Type.Integer({
      description: "Hold duration in frames at 60fps (1-120), default 8.",
      minimum: 1, maximum: 120, default: 8,
    })),
    presses: Type.Optional(Type.Integer({
      description: "Tap the button this many times (1-4), default 1. For mashing through dialogue.",
      minimum: 1, maximum: 4, default: 1,
    })),
  }),

  async execute(_id, params, _signal, _onUpdate, _ctx) {
    const run = chain.then(async () => {
      await ensureEmu();
      const res = await fetch(`${EMU}/act`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          button: params.button === "wait" ? null : params.button,
          frames: params.frames ?? 8,
          presses: params.presses ?? 1,
        }),
      });
      const entry = await res.json() as {
        step: number; button: string | null; frames: number; presses: number; changed: number; error?: string;
      };
      if (!res.ok || entry.error) throw new Error(`emulator rejected act: ${entry.error ?? res.status}`);
      logRequest({ kind: "act", ...entry });
      const pct = (entry.changed * 100).toFixed(1);
      const summary = `step ${entry.step}: ${entry.button ?? "wait"} ${entry.frames}f x${entry.presses}, screen change ${pct}%`;
      return {
        content: [{ type: "text" as const, text: summary }, await screen()],
        details: entry,
      };
    });
    chain = run.catch(() => undefined);
    return run;
  },
});

const report = defineTool({
  name: "report",
  label: "Report",
  description:
    "Record your verdict and end the run. `done` is true only when the game is BEATEN - " +
    "the whole game completed. Call it the moment that happens, or with done=false and a " +
    "note on how far you got when you decide to stop playing.",
  parameters: Type.Object({
    done: Type.Boolean({
      description: "True only when the game is completely beaten",
    }),
    note: Type.String({ description: "One short sentence on what happened during the run" }),
  }),

  async execute(_id, params, _signal, _onUpdate, _ctx) {
    const run = chain.then(async () => {
      await ensureEmu();
      const s = await status();
      const outcome = {
        step: s.step, done: params.done, note: params.note, ts: new Date().toISOString(),
      };
      logRequest({ kind: "report", ...outcome });
      try {
        writeFileSync(join(dirname(requestLog), "result.json"),
                      JSON.stringify(outcome, null, 2));
      } catch { /* the request log stays the source of truth */ }
      return {
        content: [{
          type: "text" as const,
          text: `Recorded: done=${params.done} at step ${s.step}. Run over.`,
        }],
        details: outcome,
        terminate: true,
      };
    });
    chain = run.catch(() => undefined);
    return run;
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(look);
  pi.registerTool(act);
  pi.registerTool(report);

  pi.on("session_start", () => {
    pi.setActiveTools(["look", "act", "report"]);
    chain = Promise.resolve();
    ready = null;
    requestLog = process.env.REQUEST_LOG ?? "";
  });
}
