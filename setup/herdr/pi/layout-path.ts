/**
 * layout-path.ts — 解出子智慧體重排要跑的腳本（herdr_layout.py）；拆成獨立檔是為了測試能單獨 import。
 * 順序：HERDR_TREE_LAYOUT（覆寫）→ 由本檔真實路徑（realpath，穿過 symlink）往上找 toolkit 的 herdr_layout.py → null。
 * 指定了覆寫但檔案不存在也回 null，不退回預設。
 */
import { existsSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT = join("plugins", "toolkit", "skills", "agent-dispatch", "scripts", "herdr_layout.py");

export function resolveLayout(): string | null {
  const override = process.env.HERDR_TREE_LAYOUT;
  if (override) return existsSync(override) ? override : null;
  let dir = dirname(realpathSync(fileURLToPath(import.meta.url)));
  for (;;) {
    const cand = join(dir, SCRIPT);
    if (existsSync(cand)) return cand;
    const up = dirname(dir);
    if (up === dir) return null;
    dir = up;
  }
}
