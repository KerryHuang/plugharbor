---
name: dual-tool-mirror
description: 讓 Claude Code 與 Codex 共用同一份專案設定——`.claude/` 是單一來源，用腳本鏡像 skills／agents／rules 到 Codex 讀得到的位置並在 SessionStart 注入 rules；副本不手改，指示內容只寫 AGENTS.md。Use when 專案要同時給 Claude Code 與 Codex 用、「Codex 看不到 skill／rule」「同步 .agents/skills」「AGENTS.md 要不要跟 CLAUDE.md 對齊」「設定鏡像」。
---

# 多工具設定鏡像（Claude Code ↔ Codex）

**原則：事實來源只有 `.claude/`，Codex 讀到的檔案全是產出物。** 動手之前先確認自己在改的是來源還是副本。

手抄副本一定會漂移：機械替換工具名會產生不存在的路徑，漏同步一版就整份過期。所以副本只能由腳本產生。

## 誰是來源、誰是副本

| 來源（改這裡） | 副本（別手改） | 產生者 |
|---|---|---|
| `.claude/skills/` | `.agents/skills/`（逐檔複製） | `scripts/sync-codex-mirror.mjs` |
| `.claude/agents/*.md` | `.codex/agents/*.toml`（轉成 Codex agent 格式；`tools`／`model` 不帶） | 同上 |
| `.claude/rules/*.md` | `.agents/rules/*.md`（補 `trigger: always_on`，給讀這個目錄的工具） | 同上 |
| `.claude/rules/*.md`＋`~/.claude/CLAUDE.md`＋`~/.claude/rules/` | 不落檔，Codex SessionStart 時注入 context | `scripts/codex-rules.mjs` |

為什麼兩支都要：Codex 只讀 `.agents/skills` 與 `AGENTS.md`，**不會**自動載入 `.claude/rules` 與 user 層 `~/.claude/CLAUDE.md`
（可用 `codex debug prompt-input` 實測 skill roots 與載入內容）。副本解決 skill 看不到，注入解決 rule 看不到，缺一不可。

`codex-rules.mjs` 的行為：無 `paths:` 的 rule 整份內嵌；有 `paths:` 的只列一行「動到哪些路徑前必讀」，不內嵌（對齊 Claude Code 的懶載入）。

## 安裝

1. 把兩支腳本複製進專案（建議 `.claude/scripts/`）並版控——Codex 的 hook 拿不到 plugin 安裝路徑，引用專案內的副本最穩：
   ```bash
   mkdir -p .claude/scripts
   cp "${CLAUDE_SKILL_DIR}/scripts/sync-codex-mirror.mjs" "${CLAUDE_SKILL_DIR}/scripts/codex-rules.mjs" .claude/scripts/
   ```
2. 兩邊的 SessionStart hook 都掛鏡像，Codex 另掛注入（`--root` 指向專案根；省略時依序取 `CLAUDE_PROJECT_DIR`、目前工作目錄）：
   - Claude Code（`.claude/settings.json`）：`node .claude/scripts/sync-codex-mirror.mjs --root "$CLAUDE_PROJECT_DIR"`
   - Codex（`.codex/hooks.json`）：`node .claude/scripts/sync-codex-mirror.mjs`、`node .claude/scripts/codex-rules.mjs`
   - user 層規則已由別的機制（如另行生成的 `~/.codex/AGENTS.md`）載入時，`codex-rules.mjs` 加 `--no-user` 避免重複注入。
3. 副本（`.agents/`、`.codex/agents/`）**要 commit**，讓沒跑過 hook 的 clone 也拿得到；鏡像有變動時腳本會在 session 開場提示。
4. 驗收：
   - 在 Claude Code 開新 session 後 `git status` 看到副本更新、內容與來源一致。
   - Codex 端 `codex debug prompt-input` 的 skill roots 含 `<專案>/.agents/skills`，且 context 裡出現 rule 內文。
   - 改 hook 後 Codex 會要求重新信任（`trusted_hash` 失效），這是預期行為。

兩支腳本都 **fail-open**：同步／讀取失敗只寫 stderr、exit 0，不擋 session。代價是壞了不會大聲叫——第 4 步的驗收要真的做。

## 腳本行為細節

- 來源目錄為空（不存在或 checkout 中途）時**跳過刪除階段**，不會把副本清光；來源刪掉某檔才刪對應副本，並清空目錄。
- 例外：`.claude/agents/` 刪光時仍會清 `.codex/agents/*.toml`（最後一支 agent 移走的情況）。
- 認得 CRLF frontmatter（Windows `autocrlf` checkout）。
- 不用 `process.exit()`：pipe stdout 在 macOS／Windows 是非同步的，硬退會截斷 hook 輸出。

## 專案指示：內容只寫在 AGENTS.md

專案指示只寫一份 `AGENTS.md`，兩個工具不同的地方並列寫（「Claude Code 用 X；Codex 用 Y」）。`CLAUDE.md` 只放一行 `@AGENTS.md`，不放副本。

Claude Code 自動載入 `AGENTS.md` 有前提：從專案根往上的整條路徑上，都沒有任何 `CLAUDE.md` 或 `CLAUDE.local.md`。只要出現其中一個，`AGENTS.md` 就不會載入，而且不會提示（2.1.322 實測，上層目錄的 `CLAUDE.local.md` 也一樣會擋）。所以不要直接刪掉 `CLAUDE.md`：留一行 import，有 `CLAUDE.local.md` 或 Claude Code 版本較舊也讀得到，內容只會載入一次。

既有專案有兩份平行檔時，照這個順序切換：

1. **先查讀取端**：在 plugin、腳本、hook 裡 grep，看有沒有寫死去讀專案 `CLAUDE.md` 的內文，例如 grep 設定鍵。腳本不會展開 `@AGENTS.md`，有這種讀取端時，先讓它也讀 `AGENTS.md` 並發版，或者那些鍵先留在 `CLAUDE.md`。
2. 把兩份的差異併進 `AGENTS.md`，`CLAUDE.md` 改成只有一行 `@AGENTS.md`。
3. 寫著「兩份人工同步」的 rule、README 要一起改寫。
4. 驗收要在真實專案跑：有 `CLAUDE.local.md` 的專案就保留它。用 `claude -p` 搭配 `--disallowedTools Read Bash Grep Glob`，問一句只寫在 `AGENTS.md` 的內容，答得出來才算通過。

不要用腳本機械替換工具名來產生另一份：替換會波及路徑與指令，產出不存在的路徑。

## 其餘兩邊各自維護、容易漏的

| 項目 | Claude Code | Codex |
|---|---|---|
| plugin | `settings.json` `enabledPlugins` 指向 marketplace，可 autoUpdate | `codex plugin add` 複製**快照**到本機快取；plugin bump 後要重跑 add 才更新 |
| MCP | `~/.claude.json`、專案 `.mcp.json` | `~/.codex/config.toml`、專案 `.codex/config.toml` |
| 寫入類工具的人工確認 | permissions／hook | 各 MCP tool 的 `approval_mode = "prompt"`（設在各機 user 層，路徑各機不同時別寫進專案層） |

- 新增 MCP server 要兩邊都加。
- 移除或改名 Claude 端 marketplace 前，先在 Codex 端移除引用它的 plugin 與 marketplace——若 Codex 的 marketplace root 指著 Claude 的目錄，刪掉後 Codex 會整個列不出 plugin。
- `<plugin>@<marketplace>` 用的是該 repo `marketplace.json` 宣告的 `name`，不是你取的別名；**啟用不等於安裝**，改完一定實測 skill 清單真的出現。

## 規則該放哪一層

鏡像只解決「兩個工具讀同一份」，不解決「該寫在哪」。落 user／專案／plugin 哪一層、rule 與 refs 怎麼分，見 `context-hygiene` 的 [config-layering](../context-hygiene/references/config-layering.md)。
