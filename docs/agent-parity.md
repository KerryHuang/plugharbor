# 各 CLI 對照

plugharbor 同時服務 Claude Code、Codex、pi、agy。來源只有一份（本 repo），各 CLI 讀的東西與更新方式不同。

## 各 CLI 讀什麼

| CLI | plugin（skills／agents） | user 層規則 | hooks | 更新方式 |
|---|---|---|---|---|
| Claude Code | marketplace `plugharbor`，`claude plugin install <name>@plugharbor` | `~/.claude/CLAUDE.md`、`shared/`、`rules/`（install.sh 複製） | plugin 內 `hooks/hooks.json` 自動註冊；herdr 的 `herdr-parent-tag` 在 settings 範本 | `claude plugin marketplace update plugharbor`，install.sh 版號不同時自動做 |
| Codex | `codex plugin add <name>@plugharbor` | adapter 產生 `~/.codex/AGENTS.md`、`~/.codex/agents`（reviewer 轉 TOML，read-only sandbox） | adapter 合併進 `~/.codex/hooks.json`；另外 Codex 也會載入 plugin 內的 `hooks/hooks.json`（toolkit 的 hooks，需經 `/hooks` 信任，見下） | 快照安裝；`codex plugin marketplace upgrade plugharbor` 後重裝 |
| agy | `agy plugin install <repo>/plugins/<name>` | adapter 產生 `plugharbor-home` plugin（`rules/plugharbor-root.md`，`trigger: always_on`；path-scoped rule 轉 globs） | 該 plugin 根目錄的 `hooks.json` | 快照安裝；重跑 install.sh |
| pi | 只有 `package.json` 帶 `pi` 欄位的 plugin 會寫進 `~/.pi/agent/settings.json` 的 packages | `~/.pi/agent/APPEND_SYSTEM.md`；`~/.claude/rules` 需外部 pi-code 套件（`claude-rules.ts`）載入，須先把 pi-code 加進 `~/.pi/agent/settings.json` 的 `packages` | 無（見下） | 重跑 install.sh |

adapter 是 `setup/adapters/sync-user.mjs`，用 manifest 記錄自己產生的檔，不覆蓋使用者的其他檔案。
Codex 另有 user `SessionStart` hook（`session-start.mjs`）：session 開始時若 repo 有更新，自動重新同步副本。
Codex 與 agy 的 Claude 專用操作對應見 `setup/adapters/runtime.md`。

## toolkit hook 對照

Claude 欄是 `plugins/toolkit/hooks/hooks.json` 實際註冊的事件。adapter 替 Codex／agy 註冊 `setup/adapters/` 下的三支精簡 hook
（`session-start.mjs`、`tool-policy.mjs`、`notify.mjs`），不是把 Python hook 搬過去。

**注意（Codex）**：Codex（0.164 起）會載入 plugin 的 `hooks/hooks.json`，並替換 `CLAUDE_PLUGIN_ROOT`；`codex plugin add toolkit@plugharbor` 後會快取該檔。
因此下表 Codex 欄的「無」是指 adapter 沒有另外移植；toolkit 的 hook 一旦在 Codex 經 `/hooks` 信任，實際上可能也會跑。已知後果：
Stop 可能同時跑 toolkit 的 `notification.sh` 與 adapter 的 `notify.mjs`（重複通知）；`feedback-capture.py` 可能把 Codex 的 prompt 寫進 Claude 回饋佇列。
實際行為尚未驗證，切換（cutover）時要用 `/hooks` 確認哪些 hook 生效，再決定是否在 Codex 端關掉。

| Hook | Claude | Codex | agy | pi |
|---|---|---|---|---|
| `guard.py`（分層 guard） | ✅ PreToolUse | 部分：`tool-policy.mjs`（PreToolUse `^Bash$`）只擋直接 git 命令與常見 `sh -c`，涵蓋 `git add -A`、force push 等；不讀 `guards/*.md`，也不管 Write／Edit | 無：adapter 只替 agy 註冊 Stop | 無：pi 沒有 hook 機制 |
| `agent-model-guard.py` | ✅ PreToolUse `Agent` | 無：Codex 的 subagent 沿用 runtime 預設模型，沒有 `sonnet`／`opus` 參數可檢查 | 無：未接 agy 的 hook（adapter 只註冊 Stop） | 無：pi 沒有 hook 機制 |
| `ask-question-guard.py` | ✅ PreToolUse `AskUserQuestion` | 無：Codex 沒有 `AskUserQuestion`，提問規則改寫在 `AGENTS.md` | 無：同左，規則靠 `plugharbor-root.md` | 無：規則靠 `APPEND_SYSTEM.md` |
| `auto-session-title.py` | ✅ UserPromptSubmit | 無：Codex 用自己的 session 標題，可 `/rename`；不為產標題背景啟動 Claude，也不寫 Codex 內部 session DB | 無：未接 agy 的 hook（adapter 只註冊 Stop） | 無：沒有 hook；`setup/herdr/pi/session-title-prompt.md` 只是命名用提示詞，不是 hook |
| `feedback-capture.py` | ✅ UserPromptSubmit | 無：回饋佇列只在 Claude 收集；未接 Codex 的 UserPromptSubmit | 無 | 無 |
| `feedback-reminder.py` | ✅ SessionStart `startup` | 無：同上，佇列只有 Claude 端會寫入 | 無 | 無 |
| `context-size-reminder.py` | ✅ Stop | 無：依賴 Claude transcript 格式與 context 級距；Codex 自己管理 context | 無 | 無 |
| `notification.sh` | ✅ Notification、Stop | ✅ Stop：`notify.mjs` 把 stdin 轉給 repo 內的 `notification.sh`，通知規則只維護一處（無 Notification 事件） | ✅ Stop：同一支 `notify.mjs`，經 `hooks.json` 的 `plugharbor-notify` | 無：pi 沒有 hook 機制 |

「無」的原因是該 CLI 沒有對應事件，或該 hook 讀的資料（Claude transcript、`~/.claude/feedback-loop/`）只有 Claude 會產生。
要補的話是各 CLI 自己寫 adapter，不是搬 Python hook。

## 已知落差

- **pi 載入不到多數舊 plugin**：legacy 的 7 個 plugin（sa-flow、dev-flow、backend-dotnet、frontend-vue、database-sqlserver、ui-ux、desktop-avalonia）
  只有 sa-flow 有 `package.json`，pi 才載入得到它；其餘 6 個 pi 看不到（install.sh 會印 `SKIP: pi <name>（沒有 pi package 設定）`）。
  新 plugin（toolkit、research、blog、kid-ui）都有 `package.json`。
- **Codex／agy 是快照安裝**：plugin 內容在安裝當下複製，repo 更新或 bump 版號後要重跑 `install.sh`（版號不同才重裝）。Claude 走 marketplace，同樣靠 `marketplace update` 取新版。
- **sa-flow 與 toolkit 的 `agent-model-guard` 重複註冊**：兩者都在 PreToolUse `Agent` 掛了 agent-model-guard，同時安裝時會跑兩次；
  它只補預設模型、冪等，無害。
- **Codex hook 需信任**：Codex 以內容雜湊記錄信任，hook 指令一變就失效；install.sh 之後要在 Codex 執行 `/hooks` 重新信任，否則 `tool-policy.mjs` 不會跑。
- **skillOverrides 對 plugin skill 的 key 寫法未驗證**：settings 範本想關掉 `handoff`、`ai-radar`，實測沒有任何 key 寫法能讓 plugin 的 skill 消失（可能是 `--plugin-dir` 的 inline plugin 不吃 override）。細節與測法見 `setup/README.md`「skillOverrides」。
- **升級流程只用 stub 測過**：`install.sh` 更新 marketplace 再重裝的行為，真 CLI 的結果在切換步驟才實機驗證。
