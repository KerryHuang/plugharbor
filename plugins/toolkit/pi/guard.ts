/**
 * pi extension：toolkit 的 guard（git add -A、破壞性 git 等）在 pi 裡也生效。
 * 判定交給 hooks/guard.py（與 Claude Code／Codex／agy 同一份 guards/*.md）；轉接在 guard-core.mjs。
 * deny 一律擋；ask 有介面就請使用者確認，沒介面（subagent、pi -p）擋下。
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { judge } from "./guard-core.mjs";

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    const v = await judge(event.toolName, event.input, process.cwd());
    if (!v) return undefined;
    if (v.action === "ask" && ctx.hasUI) {
      if (await ctx.ui.confirm("guard 需要你確認", `${v.reason}\n\n${JSON.stringify(event.input).slice(0, 800)}`)) return undefined;
      return { block: true, reason: `使用者沒有同意。${v.reason}` };
    }
    return { block: true, reason: v.reason };
  });
}
