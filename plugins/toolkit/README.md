# toolkit

通用 hooks 與分層 guard。安裝後自動註冊，不需改 `settings.json`。另附 7 個 skills 與 5 支 reviewer agents（見下）。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install toolkit@plugharbor
```

需要 `python3`（或 `python`）與 bash；找不到 python 時 hook 一律靜默 exit 0，不影響主流程。

## Hooks

| 事件 | Hook | 作用 |
|------|------|------|
| PreToolUse `Agent` | `agent-model-guard.py` | 檢查派 subagent 時的 model 參數 |
| PreToolUse `Bash\|Write\|Edit\|MultiEdit` | `guard.py` | 依 guard 規則檔攔截（deny／ask） |
| PreToolUse `AskUserQuestion` | `ask-question-guard.py` | 題目太短、選項沒說明、沒標（推薦）就退回 |
| Notification、Stop | `notification.sh` | 等你回應／完工時的桌面通知與音效（macOS、Linux、Windows Git Bash） |
| Stop | `context-size-reminder.py` | context 越過級距時提醒 |
| UserPromptSubmit | `auto-session-title.py` | 套用上一回合建議的 session 標題，不覆寫手動命名 |
| UserPromptSubmit | `feedback-capture.py` | 收集使用者糾正，寫入 `~/.claude/feedback-loop/queue.jsonl` |
| SessionStart `startup` | `feedback-reminder.py` | 佇列積壓或久未回顧時提醒 |

所有狀態寫在 `~/.claude/`（`feedback-loop/`、`context-reminder/`、`notification-sound.wav`），不寫進 plugin 目錄。

## 分層 guard

每個 `guards/*.md` 是一條規則，frontmatter 欄位 `tool`、`pattern`（regex）、`action`（`deny`／`ask`）、`evidence`（為什麼有這條，缺了不載入），內文是被攔時給 agent 看的修法。

讀取順序：`plugin/guards` → `~/.claude/guards` → `<專案>/.claude/guards`，同名檔由後讀的覆寫；
專案想放寬內建規則，放一個同名檔即可。命中多條時 deny 優先。內建規則：

- `git-add-all`（deny）：擋 `git add -A` / `.` / `--all`
- `git-destructive`（ask）：force push、`reset --hard`、`clean -f`

## 測試

```bash
python3 -m pytest plugins/toolkit/hooks/tests -v
for t in plugins/toolkit/hooks/tests/*.sh; do bash "$t" || exit 1; done
```
