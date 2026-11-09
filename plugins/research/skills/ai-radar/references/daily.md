# ai-radar 每日版（`--daily`）

工作日由 launchd 叫 `scripts/daily.py run`，它準備好環境後用 `claude -p`（sonnet、權限白名單）帶一段 JSON 執行背景叫你照這份做。
重點是**消化**採納待辦：每天把 1 項做成 plugharbor 的本機 branch 草稿等使用者審；**蒐集**只是輔助，最多 3 條。
社群文章、plugin 深讀、設定反查都留在週版，這裡不做。

步驟 1–3 **每次都要做完**，不是可選：沒做草稿（草稿滿、候選都不適合）也照樣做步驟 2 蒐集；某一步真的做不了，報告要寫出被什麼擋下（哪個工具、什麼錯誤），不能只寫「沒跑」。

## 執行背景（JSON 欄位）

| 欄位 | 意思 |
|---|---|
| `date`、`report` | 今天日期、報告要寫的路徑（`<out_dir>/<date>-daily.md`） |
| `backlog`、`backlog_rules`、`work_profile` | 採納待辦檔、它的對帳規則、工作模式統計 |
| `worktree`、`main_repo` | 專用 worktree（你的 cwd，已切到 detached `main`）、plugharbor 主 checkout（只讀、不碰） |
| `pending_drafts`、`drafts_full` | 還沒 merge 進 main 的 `radar/*` branch；滿 `max_pending` 個時 `drafts_full` = true |
| `candidates` | daily.py 依分數排好的候選（open、沒被每日版處理過、沒有對應 branch） |
| `tech_snapshot`、`blog_note` | 當天官方發布資料（JSON 檔路徑，可能是 null）與原因說明 |
| `last_daily_report` | 上一份每日報告的日期，蒐集的時間窗從它的隔天算起（null＝近 3 天） |

## 權限邊界

能用的只有：讀檔、Glob／Grep、WebSearch／WebFetch、在 `out_dir` 與 `worktree` 裡寫檔，以及 worktree 內的
`git status`／`git diff`／`git log`／`git switch -c radar/…`／`git add <檔>`／`git commit`。

- **絕不 `git push`**，也不用其他任何指令（沒有 python、沒有 rm、沒有 cd 到別處）；被擋就停，把要做的事寫進報告。
- `git commit` 只用 `-m "<單行>"`（可多個 `-m`），不要用 `$(...)` 或 heredoc——那會變成白名單外的指令。
- 不改 `main_repo` 的任何檔、不改 backlog 既有項的**狀態**欄、不刪任何 branch。
- 需要使用者決定的事（設計取捨、要不要裝某工具、要不要對外操作）不猜，寫進報告「需要你決定」。

## 步驟 1：消化（做草稿）

- `drafts_full` 為 true → 不做草稿，跳到步驟 2；報告開頭寫「⚠ 待審草稿已滿 N 個，先審」並列出 `pending_drafts`。
- 否則依 `candidates` 順序逐項判斷（最多看 3 項），挑第一個「**能在 plugharbor repo 內以檔案修改完成、不需要使用者先做決定**」的：
  - 適合：改 skill／agent／references／README／`docs/`、repo 根的 CI 驗證腳本這類 repo 內的文字或程式。
  - 不適合：要在本機執行或實測（跑 mesh check、升級 CLI、開網頁設定）、要裝外部工具、需求還是「待研究」、改動會跨三個以上 plugin。
  - 不適合的項目：在 backlog 該列的**決策備註**最後補 `每日版略過 <date>：<一句理由>`（只動這一格），之後 daily.py 不會再排它。
- 選定後：
  1. `git switch -c radar/<date>-<#>`（`#` 是 backlog 編號）。
  2. 先讀 worktree 的 `AGENTS.md` 與要改的檔，照 repo 慣例做**最小可審的一步**（建議 150 行以內）；項目有多個子項就只做一個，其餘寫進報告。
  3. 改到 `skills/`、`agents/`、`references/`、`templates/` 時，同一個 commit 內補該 plugin 的 `CHANGELOG.md` 條目，並 bump `plugin.json`、`package.json`（有的話）、`.claude-plugin/marketplace.json`、根 `README.md` 版本欄（AGENTS.md「版號同步」）。
  4. 逐檔 `git add <檔>`，`git status` 確認暫存區只有這次的檔，再 `git commit -m "<type>(<scope>): <摘要>（radar #<#>）"`。
     pre-commit 會跑 validate.py；失敗就修到過，修不過就停下，把錯誤寫進報告（不用 `--no-verify`）。
  5. 在 backlog 該列決策備註最後補 `每日草稿 radar/<date>-<#>（<date>）`；**狀態不動**，由使用者審完再改。
- 三項都不適合 → 今天不做草稿，報告寫明各項略過理由。

## 步驟 2：蒐集（必做，最多 3 條）

- 範圍只限 `work_profile` 列到的工具（skill 所屬的 CLI／plugin、CLI、MCP server）的**官方** changelog／release notes。
- 先讀 `tech_snapshot`（有的話）的 `official.items`；`official.unavailable` 列到、又在工作模式裡的工具，才用 WebFetch 查它的官方 changelog。沒有 snapshot 就直接查 Claude Code 與工作模式前幾名工具的官方 changelog。
- 只取時間窗內、會影響現行設定或 plugharbor 的條目，挑最重要的最多 3 條；沒有就寫「今天沒有」。
- 值得追的條目照 `backlog_rules` 的 triage 評分與 dedup 規則 append 進 backlog（狀態 `待評估`）。

## 步驟 3：報告

寫到 `report`，格式：

```markdown
# ai-radar 每日 — YYYY-MM-DD

> （草稿滿時）⚠ 待審草稿已滿 N 個，先審：radar/…、radar/…

## 今日草稿
- branch：`radar/<date>-<#>`（backlog #<#>，<分數>：<摘要>）
- 改了什麼：<2–4 行>；沒做完的子項：<…>
- diff 摘要：<`git diff main...HEAD --stat` 的結果>
- 審查與合併（在 plugharbor 主 checkout）：
  `git diff main...radar/<date>-<#>` → 同意就 `git merge --no-ff radar/<date>-<#>`、`git push`，不要就 `git branch -D radar/<date>-<#>`
- 合併後到 backlog 把 #<#> 的狀態改成已完成（或你判斷的狀態）

（沒做草稿時改寫「今日沒有草稿」與原因；略過的項目逐條列 `#編號：理由`）

## 官方更新（最多 3 條）
| 工具 | 更新 | 來源（連結＋日期） | 對我們的影響 |
|---|---|---|---|

## 需要你決定
- <停下來的事、被權限擋下的動作、要使用者判斷的取捨；沒有就寫「無」>

## backlog 異動
- 新增 #…；決策備註補記 #…
```

daily.py 收尾會在報告最後附「收尾檢查」（validate.py 結果、worktree 殘留），你不用寫這段。
