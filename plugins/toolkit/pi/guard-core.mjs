// pi 用的 guard 轉接：把 pi 的工具呼叫換成 Claude 形狀，交給 hooks/guard.py 判定（guard 只維護一份）。
// fail-open 與 Claude 端一致：找不到 python、逾時、輸出看不懂，一律放行。
import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const PLUGIN_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GUARD = resolve(PLUGIN_ROOT, "hooks", "guard.py");

/** pi 工具 → guard.py 認得的 {tool_name, tool_input}；不需判定的工具回 undefined。 */
export function toClaude(toolName, input) {
  const i = input ?? {};
  if (toolName === "bash" || toolName === "powershell") return { tool_name: "Bash", tool_input: { command: String(i.command ?? "") } };
  if (toolName === "write") return { tool_name: "Write", tool_input: { content: String(i.content ?? "") } };
  if (toolName === "edit") {
    const edits = Array.isArray(i.edits) ? i.edits : [];
    return { tool_name: "MultiEdit", tool_input: { edits: edits.map((e) => ({ new_string: String(e?.newText ?? "") })) } };
  }
  return undefined;
}

function run(cmd, args, input, env, timeoutMs) {
  return new Promise((done) => {
    const out = [];
    let settled = false;
    const finish = (r) => { if (!settled) { settled = true; clearTimeout(timer); done(r); } };
    const child = spawn(cmd, args, { env, stdio: ["pipe", "pipe", "ignore"] });
    const timer = setTimeout(() => { child.kill("SIGKILL"); finish({ code: null }); }, timeoutMs);
    child.on("error", () => finish({ code: null, spawnFailed: true }));
    child.on("close", (code) => finish({ code, stdout: Buffer.concat(out).toString("utf8") }));
    child.stdout.on("data", (c) => out.push(c));
    child.stdin.on("error", () => undefined);
    child.stdin.end(input, "utf8");
  });
}

/** 回傳 {action: "deny"|"ask", reason} 或 undefined（放行）。 */
export async function judge(toolName, input, cwd, { pythons = ["python3", "python"], timeoutMs = 10_000 } = {}) {
  const payload = toClaude(toolName, input);
  if (!payload) return undefined;
  const env = { ...process.env, CLAUDE_PLUGIN_ROOT: PLUGIN_ROOT, CLAUDE_PROJECT_DIR: cwd };
  for (const py of pythons) {
    const r = await run(py, ["-X", "utf8", GUARD], JSON.stringify({ ...payload, cwd }), env, timeoutMs);
    if (r.spawnFailed) continue;
    if (r.code !== 0 || !r.stdout?.trim()) return undefined;
    try {
      const o = JSON.parse(r.stdout).hookSpecificOutput;
      return o?.permissionDecision ? { action: o.permissionDecision, reason: o.permissionDecisionReason ?? "" } : undefined;
    } catch {
      return undefined;
    }
  }
  return undefined;
}
