# toolkit

通用 hooks 與分層 guard。安裝後自動註冊，不需改 `settings.json`。另附 9 個 skills 與 5 支 reviewer agents（見下）。

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
| PostToolUseFailure、UserPromptSubmit | `loop-guard.py` | 同一輪同一失敗第 3 次注入「停下重估」提示，之後再犯只提醒使用者；subagent 各自計數，換一則 user 訊息歸零 |
| Notification、Stop | `notification.sh` | 等你回應／完工時的桌面通知與音效（macOS、Linux、Windows Git Bash） |
| Stop | `context-size-reminder.py` | context 越過級距時提醒 |
| UserPromptSubmit | `auto-session-title.py` | 套用上一回合建議的 session 標題，不覆寫手動命名 |
| UserPromptSubmit | `feedback-capture.py` | 收集使用者糾正，寫入 `~/.claude/feedback-loop/queue.jsonl` |
| SessionStart `startup` | `feedback-reminder.py` | 佇列積壓或久未回顧時提醒 |
| SessionStart `startup` | `retro-due-reminder.py` | retrospective 待驗指標到期時提議回顧（讀 `.plugharbor/toolkit.yml`，驗過且無新證據不重提） |

所有狀態寫在 `~/.claude/`（`feedback-loop/`、`context-reminder/`、`loop-guard/`、`notification-sound.wav`），不寫進 plugin 目錄。

## 分層 guard

每個 `guards/*.md` 是一條規則，frontmatter 欄位 `tool`、`pattern`（regex）、`action`（`deny`／`ask`）、`evidence`（為什麼有這條，缺了不載入），內文是被攔時給 agent 看的修法。

讀取順序：`plugin/guards` → `~/.claude/guards` → `<專案>/.claude/guards`，同名檔由後讀的覆寫；
專案想放寬內建規則，放一個同名檔即可。命中多條時 deny 優先。內建規則：

- `git-add-all`（deny）：擋 `git add -A` / `.` / `--all`
- `git-destructive`（ask）：force push、`reset --hard`、`clean -f`

## retrospective

檢討 agent 工作流程與 plugin 本身（與 `feedback-review` 並列，共用 `references/improvement-loop.md` 的「先驗上一輪、人審、記帳」原則）。
帳本 `metrics.yml` 與報告放專案內的版控目錄，路徑設在 `.plugharbor/toolkit.yml`：

```yaml
retrospective:
  path: docs/retrospective
  units_glob: "docs/*/*"   # 選填：工作單位目錄樣式
```

附 `chain_cost.py`：統計某個工作單位花了幾個 session、幾輪、多少 token。只支援 Claude Code，只讀本機 `~/.claude/projects`。

## transcribe

本機語音轉逐字稿（`skills/transcribe/scripts/transcribe.py`）：Mac Apple Silicon 用 mlx-whisper、其他平台用 faster-whisper，輸出經 OpenCC `s2twp` 轉台灣繁體，每段 `[hh:mm:ss] 文字`。依賴（ffmpeg、轉錄套件、`opencc-python-reimplemented`）由使用者自裝，`transcribe.py doctor` 列出缺件與安裝指令。不上雲端、不分講者。另有 `record devices|start|status|stop`：背景用麥克風錄音、每 300 秒一個 16 kHz wav 分段，錄音與 session 脫鉤，`stop` 合併成 `recording.wav`；錄音需要 ffmpeg（`doctor --record` 檢查）。線上會議可用 `record start --source system|both` 一併錄系統播放的對方聲音（Mac 需 macOS 14.2+、Python 3.11+、`catap`，用 Core Audio tap，不必裝虛擬音訊驅動；Windows 尚未驗證、暫不開放），`live start` 會在錄音中逐段轉錄到 `transcript.md`。

## 測試

```bash
python3 -m pytest plugins/toolkit/hooks/tests -v
python3 plugins/toolkit/skills/retrospective/scripts/test_chain_cost.py
python3 -m pytest plugins/toolkit/skills/transcribe/tests -v   # 需 opencc-python-reimplemented
for t in plugins/toolkit/hooks/tests/*.sh plugins/toolkit/skills/agent-dispatch/tests/*.sh; do bash "$t" || exit 1; done
```
