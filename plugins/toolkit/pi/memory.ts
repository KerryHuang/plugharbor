/**
 * memory.ts — 讓 pi 唯讀看到 Claude Code 的 auto-memory 索引（plugharbor#72）。
 * 規則同 hooks/memory-context.py：從 cwd 往上找 ~/.claude/projects/<slug>/memory/MEMORY.md
 * （slug＝絕對路徑的非英數字元換成 `-`），取前 200 行寫進 system prompt 區段。找不到就不加。
 */
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const MAX_LINES = 200;

export function findIndex(cwd: string, home = homedir()): string | undefined {
  let cur = resolve(cwd);
  for (;;) {
    const f = join(home, ".claude", "projects", cur.replace(/[^A-Za-z0-9]/g, "-"), "memory", "MEMORY.md");
    if (existsSync(f)) return f;
    const parent = dirname(cur);
    if (parent === cur) return undefined;
    cur = parent;
  }
}

export function memorySection(cwd: string, home = homedir()): string | undefined {
  const f = findIndex(cwd, home);
  if (!f) return undefined;
  const lines = readFileSync(f, "utf8").split(/\r?\n/).slice(0, MAX_LINES);
  if (!lines.some((l) => l.trim())) return undefined;
  return `[toolkit] 以下是 Claude Code 為這個專案記下的 auto-memory 索引（唯讀，來源 ${f.replace(/\\/g, "/")}）。` +
    "每行指向同目錄的一個 topic 檔，跟當前工作相關時再讀原檔；記憶是寫下當時的觀察，動手前先對照現況。" +
    "不要新增、修改或刪除這些記憶檔。\n\n" + lines.join("\n");
}

export default function (pi: ExtensionAPI) {
  // 寫進 prompt 區段；回傳整份 systemPrompt 會取代 prompt，其他 extension 的區段就失效。
  pi.on("before_agent_start", async (event, ctx) => {
    try {
      const s = memorySection(ctx.cwd ?? process.cwd());
      if (s) event.systemPromptOptions.sections["claude-memory"] = s;
    } catch { /* 讀不到就不加，不擋 agent */ }
  });
}
