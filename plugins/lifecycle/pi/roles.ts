/**
 * roles.ts — 只在 Pi 載入（package.json 的 pi.extensions）：把 pi/roles/ 的角色註冊給 pi-herdr-agents。
 *
 * 協定是 pi-herdr-agents 的 `pi-herdr-subagents:roles:discover:v1`（docs/roles.md〈Publish a role pack〉）：
 * 收到 apiVersion 1 的請求就 register 角色目錄。沒裝 pi-herdr-agents 時沒人發這個事件，本檔不做事；
 * 派 `agent: "<plugin>-<agent>"` 會被 Pi 回報找不到角色，照 references/harness-terms.md 停下告訴使用者。
 * 角色檔由 scripts/gen-pi-roles.py 從 agents/*.md 產生，不要手改。
 */
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export const ROLES_DIR = fileURLToPath(new URL("./roles", import.meta.url));
export const DISCOVER_EVENT = "pi-herdr-subagents:roles:discover:v1";

export default function (pi: ExtensionAPI) {
  const unsubscribe = pi.events.on(DISCOVER_EVENT, (request) => {
    const discovery = request as { apiVersion?: number; register?(path: string): void };
    if (discovery.apiVersion === 1 && typeof discovery.register === "function") {
      discovery.register(ROLES_DIR);
    } else {
      console.error(`[plugharbor] 不認得的 pi-herdr-agents 角色協定版本 ${discovery.apiVersion}，${ROLES_DIR} 的角色沒有註冊`);
    }
  });
  pi.on("session_shutdown", unsubscribe);
}
