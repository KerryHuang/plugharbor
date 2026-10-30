/**
 * herdr-tree.ts — 讓 herdr 側欄把 pi 子智慧體掛在 launcher 底下（只寫 token，排序與樹枝由側欄 plugin（plugharbor.sidebar）算）。
 *
 * herdr 不知道哪個 pane 是誰開的，pi-herdr-agents 也沒把 parent pane 傳給子 pane，只在子程序 env 留下
 * PI_SUBAGENT_ACTIVITY_FILE＝<parent sessionDir>/artifacts/<parent sessionId>/subagent-activity/<id>.json。
 * 所以每個 pi 在自己的 pane 寫 pi_sid＝自己的 sessionId；子智慧體另寫 parent_sid（從上面路徑解出）與 sub_name，
 * 側欄 plugin 再用 parent_sid 對 pi_sid 找到 parent pane。
 * 另外把 pi 的終端機標題（預設「π - <cwd>」，側欄第二行沒資訊量）改成跟 Claude 一樣的「✳ <任務>」：
 * 任務取 session 名稱（/name），沒有就取第一則使用者訊息的第一行；子智慧體取 PI_SUBAGENT_NAME（它的第一則訊息是
 * pi-herdr-agents 包的 <file …>）。session_start／agent_start 時使用者訊息還沒進 branch，所以在 turn_start 套；
 * pi 改名時會寫回自己的格式，每個 turn 重套剛好蓋回來。
 * 自動命名：照 Claude Code 內建 ai-title 的做法——只拿第一則使用者訊息，用它的 prompt（session-title-prompt.md，
 * 2026-10-27 從 claude binary 的 generate_session_title 抄出；Claude Code 升版改了 prompt 要自己重抄）交給 Haiku 產 JSON 標題。
 * 第一個 turn 時使用者訊息還沒進 branch，所以在 input 事件拿原文就產（不等回覆）；agent_end 再從 branch 補一次。
 * 已有名稱（含 /name）或子智慧體不做。
 * 版面（仿 Claude 的 herdr 派工版型）：pi-herdr-agents 設 panes.mode="split" 後子智慧體從 parent pane 切出，
 * 子智慧體啟動時重排（主 session 最大、標 ★）：環境變數 HERDR_TREE_LAYOUT 指向自訂重排腳本
 * （python3 <腳本> --main <parent pane>）就用它；沒設就用內建版型（主 session 佔左半、worker 在右半等高堆疊）；同 tab 超過 6 個就把自己搬到新 tab。
 * 平行啟動時以 lock 目錄排隊，避免兩支 layout 同時搬 pane。不在同一個 tab（worktree、grouped／tab 模式）就不動。
 * 掛載：~/.pi/agent/settings.json 的 "extensions"。不在 herdr 裡（HERDR_ENV≠1）什麼都不做。
 */
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { uuidv7 } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const SOURCE = "plugharbor-herdr-tree";
const herdr = process.env.HERDR_BIN_PATH || "herdr";

const run = (args: string[]) =>
  new Promise<string>((done, fail) =>
    execFile(herdr, args, { encoding: "utf8", timeout: 5000 }, (e, out) => (e ? fail(e) : done(out))));

const HERE = dirname(fileURLToPath(import.meta.url));
// 自訂重排腳本（選填）；沒設就用下面的內建版型
const LAYOUT = process.env.HERDR_TREE_LAYOUT;
const MAX_WORKERS = 6;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const runPy = (args: string[]) =>
  new Promise<void>((done, fail) => execFile("python3", args, { timeout: 60000 }, (e) => (e ? fail(e) : done())));

/** 同一個 tab 一次只有一支在重排；mkdir 是原子的，超過 90 秒的 lock 當成殘留 */
async function withTabLock(tab: string, fn: () => Promise<void>) {
  const lock = join(tmpdir(), `herdr-layout-${tab.replace(/[^\w-]/g, "_")}.lock`);
  for (let i = 0; i < 120; i++) {
    try {
      mkdirSync(lock);
      try { return await fn(); } finally { rmSync(lock, { recursive: true, force: true }); }
    } catch (e: any) {
      if (e?.code !== "EEXIST") throw e;
      try { if (Date.now() - statSync(lock).mtimeMs > 90000) rmSync(lock, { recursive: true, force: true }); } catch {}
      await sleep(500);
    }
  }
}

/** 內建預設版型：worker 全搬到暫存 tab，再依序放回——第一個在主 session 右半，其餘在右半往下切成等高 */
async function defaultLayout(main: string) {
  const panes: any[] = JSON.parse(await run(["pane", "layout", "--pane", main]))?.result?.layout?.panes ?? [];
  const workers = panes.map((p) => p.pane_id as string).filter((p) => p !== main);
  const n = workers.length;
  if (!n) return;
  const tab = JSON.parse(await run(["pane", "get", main]))?.result?.pane?.tab_id;
  const move = async (pane: string, tabId: string, target: string, dir: string, ratio: number) =>
    JSON.parse(await run(["pane", "move", pane, "--tab", tabId, "--split", dir, "--target-pane", target,
      "--ratio", String(ratio), "--no-focus"]));
  const hold = JSON.parse(await run(["pane", "move", workers[0], "--new-tab", "--label", "layout-hold", "--no-focus"]))
    ?.result?.move_result?.pane?.tab_id;
  for (const w of workers.slice(1)) await move(w, hold, workers[0], "right", 0.5);
  await move(workers[0], tab, main, "right", 0.5);
  for (let i = 1; i < n; i++) await move(workers[i], tab, workers[i - 1], "down", 1 / (n - i + 1));
}

/** 子智慧體：重排 parent 所在的 tab（自訂腳本或內建版型） */
async function arrange(self: string, parentSid: string, name: string | undefined) {
  if (LAYOUT && !existsSync(LAYOUT)) return;
  const agents = JSON.parse(await run(["agent", "list"]))?.result?.agents ?? [];
  const parent = agents.find((a: any) => a.tokens?.pi_sid === parentSid)?.pane_id;
  if (!parent) return;
  const tabOf = async (p: string) => JSON.parse(await run(["pane", "get", p]))?.result?.pane?.tab_id;
  const tab = await tabOf(parent);
  if (!tab || tab !== (await tabOf(self))) return;
  await withTabLock(tab, async () => {
    const panes = JSON.parse(await run(["pane", "layout", "--pane", parent]))?.result?.layout?.panes ?? [];
    if (panes.length - 1 > MAX_WORKERS) {
      // 第 7 個起開新 tab，該 tab 不重排（同派工版型）
      await run(["pane", "move", self, "--new-tab", "--label", name || "agents", "--no-focus"]);
      return;
    }
    if (LAYOUT) await runPy([LAYOUT, "--main", parent]);
    else await defaultLayout(parent);
  });
}

/** 從 activity file 路徑解出 parent sessionId：…/artifacts/<sid>/subagent-activity/<id>.json */
export const parentSid = (activityFile: string | undefined) => {
  if (!activityFile) return undefined;
  const dir = dirname(activityFile);
  return basename(dir) === "subagent-activity" ? basename(dirname(dir)) : undefined;
};

const text = (content: unknown) =>
  typeof content === "string" ? content
    : Array.isArray(content) ? content.map((c) => (c?.type === "text" ? c.text : "")).join(" ") : "";

/** session 名稱優先，否則第一則使用者訊息的第一個非空行；都沒有回 undefined（保留 pi 自己的標題） */
function task(ctx: any): string | undefined {
  const name = ctx.sessionManager.getSessionName?.() || process.env.PI_SUBAGENT_NAME;
  if (name) return name;
  for (const e of ctx.sessionManager.getBranch?.() ?? []) {
    if (e?.type !== "message" || e.message?.role !== "user") continue;
    const line = text(e.message.content).split("\n").map((l) => l.trim()).find(Boolean);
    if (line) return line.length > 60 ? `${line.slice(0, 60)}…` : line;
  }
}

// 前綴照 Claude Code：執行中輪轉 ◐◓◑◒，閒置 ✳
const SPIN = ["◐", "◓", "◑", "◒"];
let frame = -1;  // -1＝閒置
let spinner: ReturnType<typeof setInterval> | undefined;

const retitle = (ctx: any) => {
  try {
    const t = task(ctx);
    if (t) ctx.ui?.setTitle?.(`${frame < 0 ? "✳" : SPIN[frame % SPIN.length]} ${t}`);
  } catch {
    // 標題只影響側欄顯示
  }
};

const spin = (ctx: any, on: boolean) => {
  clearInterval(spinner);
  spinner = undefined;
  frame = on ? 0 : -1;
  retitle(ctx);
  if (!on) return;
  spinner = setInterval(() => { frame++; retitle(ctx); }, 500);
  spinner.unref?.();
};

const NAMER = ["claude-bridge", "claude-haiku-5-5"] as const;
const TITLE_PROMPT = readFileSync(join(HERE, "session-title-prompt.md"), "utf8");
// Claude 在未指定語言時附的那句；我們一律指定繁中
const TITLE_LANG = "Write the title in Traditional Chinese (Taiwan). Keep technical terms and code identifiers in their original form.";

/** 第一則使用者訊息（Claude 也只看這個），截 4000 字 */
function firstUser(ctx: any): string | undefined {
  for (const e of ctx.sessionManager.getBranch?.() ?? []) {
    if (e?.type !== "message" || e.message?.role !== "user") continue;
    const t = text(e.message.content).trim();
    if (t) return t.slice(0, 4000);
  }
}

let naming = false;
async function autoName(pi: ExtensionAPI, ctx: any, input?: string) {
  if (naming || process.env.PI_SUBAGENT_NAME || pi.getSessionName()) return;
  const first = firstUser(ctx) ?? input?.trim().slice(0, 4000);
  const model = ctx.modelRegistry?.find(...NAMER);
  if (!first || !model) return;
  naming = true;
  try {
    const res = await ctx.modelRegistry.complete(model, {
      systemPrompt: TITLE_PROMPT,
      messages: [{ role: "user", content: [{ type: "text", text: `<session>\n${first}\n</session>\n${TITLE_LANG}` }], timestamp: Date.now() }],
    }, { cacheRetention: "none", sessionId: uuidv7() });
    const raw = text(res.content);
    const json = raw.slice(raw.indexOf("{"), raw.lastIndexOf("}") + 1);
    const name = String(JSON.parse(json)?.title ?? "").trim().slice(0, 40);
    if (name && !pi.getSessionName()) {
      pi.setSessionName(name);
      retitle(ctx);
    }
  } catch {
    // 命名失敗不打擾 session，下一次 agent_end 再試
  } finally {
    naming = false;
  }
}

export default function (pi: ExtensionAPI) {
  // 不 await：命名不擋 turn
  pi.on("input", async (event, ctx) => { void autoName(pi, ctx, event.text); });
  pi.on("agent_end", async (_event, ctx) => { void autoName(pi, ctx); });
  if (process.env.HERDR_ENV === "1") {
    pi.on("turn_start", async (_event, ctx) => retitle(ctx));
    pi.on("agent_start", async (_event, ctx) => spin(ctx, true));
    pi.on("agent_end", async (_event, ctx) => spin(ctx, false));
    pi.on("session_shutdown", async () => { clearInterval(spinner); spinner = undefined; });
  }
  pi.on("session_start", async (_event, ctx) => {
    if (process.env.HERDR_ENV !== "1") return;
    // pi -p／--mode json 是被別的 agent 一次性呼叫，所在 pane 不是它的（例如 Claude 的 Bash），不寫 pi_sid 免得側欄誤判
    if (ctx.mode === "print" || ctx.mode === "json") return;
    retitle(ctx);
    try {
      // HERDR_PANE_ID 在 pane 搬動後會過期，pane current 由 herdr 依呼叫端終端機解出現在的 pane
      const pane = JSON.parse(await run(["pane", "current", "--current"]))?.result?.pane?.pane_id;
      if (!pane) return;
      const parent = parentSid(process.env.PI_SUBAGENT_ACTIVITY_FILE);
      const name = process.env.PI_SUBAGENT_NAME;
      await run(["pane", "report-metadata", pane, "--source", SOURCE,
        "--token", `pi_sid=${ctx.sessionManager.getSessionId()}`,
        ...(parent ? ["--token", `parent_sid=${parent}`] : ["--clear-token", "parent_sid"]),
        ...(parent && name ? ["--token", `sub_name=${name}`] : ["--clear-token", "sub_name"])]);
      if (parent) await arrange(pane, parent, name);
    } catch {
      // 只影響側欄顯示，失敗不打擾 session
    }
  });
}
