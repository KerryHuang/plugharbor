# research

探索與研究用的三個 skill。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install research@plugharbor
```

## Skills

| Skill | 用途 |
|-------|------|
| `graphify` | 把任何資料夾（程式碼、文件、論文、圖片、影音）建成知識圖譜，輸出互動 HTML、GraphRAG JSON 與 `GRAPH_REPORT.md`；支援 `--update` 增量與 `query`／`path`／`explain` 查詢。需自行安裝 `graphifyy`（Python 套件）。只能手動 `/graphify` 觸發。 |
| `ai-radar` | 每週掃描大廠更新、社群實踐，反查現行 agent 設定的最佳化機會，並把建議對帳進跨週的採納待辦；週報的 plugin 排行與深讀交給 `plugin-harvest --lean`。只能手動觸發。 |
| `plugin-harvest` | 給一個領域就搜尋最多人用的 plugin，深讀對照自家 plugin（裝用／借鑒／不理），把值得借的寫成「改哪個 skill 哪一段」的提案，逐條核准後才改檔；採納時寫 `harvest-lock.json`（來源、commit、授權），`--check-lock` 檢查上游更新與授權變動。只能手動觸發。 |

`ai-radar` 的輸出目錄：專案 `CLAUDE.md` 宣告 `ai-radar-output: <路徑>` 就寫在專案內，否則寫到 `~/.claude/ai-radar/`（不進版控）。
`plugin-harvest` 用同一個輸出目錄：評估卡在 `plugin-eval/`、提案在 `plugin-harvest/`。
單獨評估一個 repo：`/research:plugin-harvest https://github.com/<owner>/<repo>`（舊的 `/research:ai-radar --plugin <網址>` 仍可用，會轉交）。
`ai-radar` 的設定健檢步驟會交給 toolkit plugin 的 `config-doctor`；沒裝就略過該步。

## ai-radar 每日版（macOS）

工作日 09:00 由 launchd 在本機背景跑 `skills/ai-radar/scripts/daily.py run`，以消化採納待辦為主：

- 從 `adoption-backlog.md` 挑分數最高、能在 repo 內改檔完成的 1 項，在專用 worktree（預設 `~/Work/projects/plugharbor-radar`）從本機 `main` 切 `radar/<日期>-<編號>` branch 做成草稿並 commit，**不 push**。待審的 `radar/*`（還沒 merge 進 main 的）已有 3 個就不做新草稿。
- 少量蒐集：只看 `work-profile.md` 裡工具的官方 changelog，最多 3 條；有 blog repo 當天的 `data/tech-snapshots/<日期>.json` 就先讀它。`work-profile.md` 由 `skills/ai-radar/scripts/work_profile.py` 統計近 30 天 transcript 用到的 skill、CLI、MCP server、副檔名，每週重算。
- 報告寫到 `<OUT>/<日期>-daily.md`，log 在 `<OUT>/logs/`。只在新草稿、草稿滿 3 個、執行失敗時跳 macOS 通知。
- `claude -p --model sonnet --permission-mode dontAsk`，白名單只有讀檔、Web 搜尋與抓取、在 `<OUT>` 與專用 worktree 寫檔、worktree 內的 `git status`／`diff`／`log`／`switch -c radar/*`／`add`／`commit`；push 明確禁止，不用 `--dangerously-skip-permissions`。

```bash
# 從 plugharbor 主 checkout 安裝（排程跑的是這份 daily.py，跟著本機 main）
plugins/research/skills/ai-radar/scripts/install-daily.sh --print      # 先看 plist
plugins/research/skills/ai-radar/scripts/install-daily.sh              # 寫入 ~/Library/LaunchAgents 並載入
plugins/research/skills/ai-radar/scripts/install-daily.sh --uninstall
# 手動跑一次（同一天已有報告會跳過）
python3 plugins/research/skills/ai-radar/scripts/daily.py run
```

路徑可用環境變數覆寫：`AI_RADAR_OUT`、`RADAR_REPO`（plugharbor 主 checkout）、`RADAR_WORKTREE`、`RADAR_BLOG`、`RADAR_CLAUDE`；安裝時有設定就一併寫進 plist。
