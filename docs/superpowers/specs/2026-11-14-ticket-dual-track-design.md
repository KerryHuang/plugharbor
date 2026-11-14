# ticket skill 雙軌示範：設計

日期：2026-11-14。功能清單：`docs/feature.md` 的「lifecycle：ticket skill 雙軌示範」一節。

## 起因與目標

lifecycle 的 ticket skill（`ticket-ops`、`ticket-create`、`triage`、`ticket-report`、`qa-verify`）的 GitHub 後端從沒實測過，CHANGELOG 沒有任何實測紀錄。拿真實專案雙軌並行來驗：

- repo 裡的 `docs/feature.md`、`docs/todo.md`（有 `docs/roadmap.md` 時含它）為準。
- GitHub Issues 與 Projects 看板跟著同步。
- 兩邊對不上就算 skill 的 bug，修 skill，不改資料遷就。

目標：

- 7 個操作（`create`、`set_stage`、`comment`、`attach`、`query`、`get`、`link_blocked_by`）加看板同步，在真實 repo 上各跑過且讀回一致。
- 修掉過程中發現的 bug，讓 GitHub 後端可以放心給其他專案用。

非目標：

- 不改 Linear 後端。
- 不做雙向同步：GitHub 上手改的狀態不回寫 repo 文件，對帳時列為差異。
- 不做 Jira。

反目標（做到也算失敗）：

- 公開 repo 的 issue 出現 `.leak-denylist` 命中的字串。
- 對帳腳本為了湊出 0 差異而放寬比對（例如忽略未分類項）。

## 範圍與階段

| 階段 | repo | 期間 |
|---|---|---|
| 第一階段 | plugharbor、xiaoxiao（都是公開 repo） | 補開完起算兩週 |
| 第二階段 | Formwright（產品化） | 第一階段過關後 |

第二階段才驗 `qa-verify --sweep`（只有 Formwright 有網頁 Demo）與大量票的報表速度。Formwright 正在跑自動駕駛，第一階段不碰它。

## 對應方式（已拍板）

| repo 文件 | GitHub |
|---|---|
| roadmap 的段 | 父票 |
| feature.md 項目 | 子票，清單那一行附 `#n` |
| todo.md 的一行 | 掛 `todo` label 的票，那一行附 `#n` |
| 外部回饋 | 先開 issue 走 `triage`，確定要做才進 feature.md |

階段對應：

| feature.md 標記 | 票 |
|---|---|
| `[x]` | 關閉（completed） |
| `[ ] 🚧` | `stage:in-progress` |
| `[ ] 📋` | `stage:todo` |
| `[ ] 💡` | `stage:backlog` |
| `[-]` | 關閉（not planned） |

todo.md 沒有勾選標記，一行就是一張開著的 `stage:todo` 票；照 todo 慣例「做完就刪」，刪行時同步以 completed 關票。

現有項目全部補開，已完成的開完直接關。第一週週報會被大量補開污染，對帳時扣除、不列入過關判斷。

**我的決定：沒有 roadmap 時用 feature.md 的 `##` 節當父票。** 兩個示範 repo 都沒有 `docs/roadmap.md`；feature.md 的節（plugharbor 的「lifecycle：ticket skill 雙軌示範」、xiaoxiao 的「v0.3.0「對話更順」」）本來就是一段工作的分組。節標題行尾附 `#n`（例如 `## v0.3.0「對話更順」 #12`）。「不做」這類集中節不開父票，裡面的項目以 not planned 關閉、不掛父票。

## 前置修改

全部在 `plugins/lifecycle`。實作順序是 1 → 4 → 2 → 3 → 對帳腳本：外洩檢查先上，之後每一次實測建票都受保護；sub-issue 調查的結論會決定 `create` 的父子做法，所以排在 Projects 之前。每個改到 `skills/`、`references/` 的 commit 各自附 CHANGELOG 和 bump（照 `.claude/rules/version-consistency.md`），功能是 minor、調查結論只改文件是 patch，不累積成一次 bump。

### 1. 送出前外洩檢查

`ticket_backend.py` 加子命令：

```
python3 ticket_backend.py leak <檔案>
```

- 讀 repo 根目錄的 `.leak-denylist`（在 worktree 裡找不到就讀主 checkout 那份，同 `scripts/ci/validate.py` 的 `load_denylist`）。格式同 validate.py：一行一個字串、`regex:` 開頭為正規式、`#` 開頭為註解、不分大小寫。
- 沒命中：退出碼 0。命中：退出碼 4，stdout 每個命中一行 `L<行號> <命中字串>`。找不到 denylist：退出碼 5，stderr 一行說明。
- `ticket-ops` 在 `create`、`comment`、改描述（`create` 回填父票、`link_blocked_by`）與 `attach` 的 caption 送出前，把要送的內文寫成檔案跑一次。退出碼 4 → 停下，把命中列給叫用端，不送出、不自動改寫。退出碼 5 → 查 `gh repo view --json visibility`，公開 repo 停下請使用者建 denylist，私有 repo 警告後繼續。
- parser 是從 validate.py 複製的一小段（plugin 要能單獨安裝，不能 import repo 腳本）；`scripts/ci/validate.py` 加一條檢查，確認兩份解析規則一致（同一組樣本輸入，結果相同）。

前置：xiaoxiao 目前沒有 `.leak-denylist`，補開前要建（從 plugharbor 那份挑適用的行）。

### 2. 同步 GitHub Projects

設定（`.plugharbor/lifecycle.yml`，`config.md` 補說明）：

```yaml
ticket:
  tool: github
  repo: KerryHuang/xiaoxiao
  states: { backlog: stage:backlog, todo: stage:todo, in-progress: stage:in-progress, in-review: stage:in-review, done: closed, canceled: closed }
  project:            # 選填；沒設就不碰看板，行為同現在
    owner: KerryHuang
    number: 3
    field: Status     # 預設 Status
    options:          # 抽象階段 → 單選欄位的選項名
      backlog: Backlog
      todo: Todo
      in-progress: In Progress
      in-review: In Review
      done: Done
      canceled: Canceled
```

行為：

- `create` 建完票後 `gh project item-add <number> --owner <owner> --url <issue url> --format json` 取得 item id，再設 Status。
- `set_stage` 改完 label／開關後，同步改 Status：`gh project item-edit --id <item> --project-id <id> --field-id <id> --single-select-option-id <id>`。field id 與 option id 每次用 `gh project field-list --format json` 查，不快取。
- 票還不在看板上（例如手動建的）→ 先 `item-add` 再改，回報寫明補加了。
- 對照表缺該階段的 option、或看板上找不到那個 option 名 → 退出碼 2，列出看板上實際有的 option，不自行對映。
- `ticket_backend.py` 加純函式 `project_option(cfg, stage)` 回傳 option 名（沒設 `ticket.project` 回 None），有單元測試；`gh` 呼叫步驟寫在 `github.md` 新的「看板」一節。
- `get`、`query` 加讀回 Status：`gh project item-list` 取看板上各 issue 的 Status，看板與 label 不一致時回 `board_mismatch: true`。這是對帳要用的。

看板本身（建立、欄位選項）由補開步驟手動建一次，不由 skill 建。GitHub Projects 內建的 workflow（Item closed → Done、Auto-add）要關掉，避免和 skill 搶著改 Status、蓋掉 canceled。

前置：使用者先跑 `gh auth refresh -s project`（目前 token 缺 `project` scope）。

### 3. 改清單時同步票

範圍不只打勾：只要 `ticket.tool` 有設，任何流程（brainstorming、spec、implement、手動）改 feature.md 或 todo.md，都照下表同步。規則寫進 `references/feature-checklist.md` 新的「同步票」一節，`implement/references/after.md` 指過去。沒設 `ticket.tool` 時照舊，不問。

| 清單的變動 | 票 |
|---|---|
| 新增 feature 項目 | `create`（`parent` 為所在節的票、`stage` 照標記），行尾附 ` #n` |
| 新增 `##` 節 | 建父票，節標題尾附 ` #n` |
| 改項目標記 | `set_stage` |
| 項目換節 | 改 parent（做法依前置修改 4 的結論） |
| 刪 feature 項目 | `set_stage canceled`，留言寫明「清單已刪除此項」 |
| 新增 todo 行 | `create`，label `todo`、`stage: todo`，行尾附 ` #n` |
| 刪 todo 行 | `set_stage done` |
| todo ↔ feature 搬移 | 同一張票：加或移除 `todo` label、補或移除 parent，不另開 |

**父票的階段**：建立時 `todo`；節內有任一 🚧 子票就改 `in-progress`；節內全部子票關閉時關父票（有任一 completed 就 completed，全部 not planned 就 not planned）。這一步由同步票的流程在改完子票後順手檢查。

`feature_checklist.py` 要改兩處：

- `item_name()` 與節名解析先剝掉行尾的 ` #n`（`\s+#\d+$`），否則沒有「 — 」的行會把 `#n` 當成功能名的一部分，`⛔ 等：<功能名>` 的比對、節小計都會壞。加對應測試：有「 — 」、沒有「 — 」、節標題三種。
- 加 `--tickets`：輸出 JSON，每個項目一筆 `{name, stage, ticket, section, section_ticket}`（`ticket` 取行尾 `#n`，沒有為 null；`stage` 用上表的抽象階段，未分類為 `unclassified`）。加 `--todo <檔>` 解析 todo.md。同步票與對帳共用這份解析，不各寫一份。

### 4. 調查 GitHub 原生 sub-issue 與 blocked-by

現行 `github.md` 用內文慣例（`parent: #p`、task list、`blocked-by: #n`）。GitHub 已有 sub-issues 與 issue dependencies 的 REST API（`/repos/{o}/{r}/issues/{n}/sub_issues`、`/issues/{n}/parent`、`/issues/{n}/dependencies/blocked_by`），要確認：

1. 兩個示範 repo 能不能用（個人帳號的公開 repo、目前 gh token 的權限夠不夠）。
2. `gh` 指令與 API 實際參數：sub-issue 要用 issue 的 `id` 不是 `number`、能否跨 repo、一張票的上限。
3. 讀回：`get` 拿得到 parent 與 children、`query` 能否用 `parent` 篩選。
4. 有無通知語意（blocker 關閉時被擋票有沒有提示）。

交付：在 `github.md` 寫結論。都能用就改成原生為主、內文慣例降為退路（API 失敗時用，回報寫明降級）；不能用就維持內文慣例，寫明原因。調查在示範 repo 開臨時票驗，驗完以 not planned 關閉並在標題標「[測試]」，對帳時扣除。

## 對帳腳本

`plugins/lifecycle/skills/ticket-ops/scripts/reconcile.py`：

```
python3 reconcile.py --repo <owner/repo> [--feature docs/feature.md] [--todo docs/todo.md] [--exclude-label test] [--log <jsonl>]
```

- repo 這邊：呼叫 `feature_checklist.py --tickets` 與 `--todo`。
- GitHub 這邊：`gh issue list --state all --json number,state,stateReason,labels,title --limit 1000`（照 `github.md`「查詢不截斷」，筆數 = 1000 就停並回報可能截斷），有設 `ticket.project` 再讀看板 Status。
- 輸出三部分：
  1. 各階段數量兩邊對照與差異，分三組分開計，不混算：feature 子票（backlog、todo、in-progress、done、canceled）、父票（open、closed）、todo 票（open、closed）。
  2. 逐項差異：repo 有 `#n` 但票的階段不同、repo 項目沒有 `#n`、項目所在節的 `#n` 與票的 parent 不同、孤兒票、看板 Status 與 label 不一致、未分類項目（`[ ]` 沒帶 emoji）。
  3. 一行結論：`差異 0` 或 `差異 N`。
- 比對規則：
  - 🚧 對 `in-progress` 或 `in-review` 都算一致（清單沒有 in-review 標記）。
  - 未分類項目一律算差異，補開時不建票，先請使用者補標記。
- 不算孤兒、不計入任何數量的票，一律在輸出裡分開列出數量：
  - 標「[測試]」或掛 `--exclude-label` 的票。
  - 已關閉的 `todo` 票（行刪了是正常的）。
  - 開著、掛 `triage` label 或沒有任何 `stage:*` label 的票：外部回饋，還在等 triage。
- 開著、有 `stage:*` label 卻沒被任何一行引用的票才算孤兒。bug 追蹤票照 feature-checklist 慣例進 todo.md，所以有行可引用，不另設例外。
- `--log` 時追加一行 `{date, repo, counts, diff_total}` 到 JSONL；過關條件 2 讀這份 log 判斷「最後連續 5 天差異 0」。log 放 plugharbor 的 `.tmp/ticket-dual-track/`（gitignore），每天由使用者或排程跑一次（**留給 builder**：用 `/schedule` 還是每天開 session 手動跑）。
- 退出碼：差異 0 回 0，有差異回 1，查詢可能截斷回 3。

## 補開順序

每個 repo 各做一次，plugharbor 先、xiaoxiao 後（plugharbor 的 issue 先暴露 bug，xiaoxiao 跟著受益）：

1. 寫 `.plugharbor/lifecycle.yml` 的 `ticket` 設定並 commit。
2. 建 label：`stage:backlog`、`stage:todo`、`stage:in-progress`、`stage:in-review`、`todo`、`blocked`。
3. 建 Projects 看板，Status 選項照設定的 `options`，關掉內建 workflow。
4. 建父票：每個非「不做」的 `##` 節一張，經 `ticket-ops create`。
5. 建子票：每個 feature 項目一張，帶 `parent` 與 `stage`；`[x]` 與 `[-]` 建完立刻 `set_stage done`／`canceled`。todo.md 每行一張 `todo` 票。
6. 回填 `#n`：feature.md 每行與每個節標題、todo.md 每行附 `#n`，commit（不改其他文字）。
7. 回填父票的子票清單（若調查結論是用原生 sub-issue 就跳過）。
8. 跑 `reconcile.py --log`，第一次就要差異 0；不是 0 就是 bug。

補開走 `ticket-ops`，不直接打 `gh`，這樣補開本身就是 `create`、`set_stage` 的實測。`comment`、`attach`、`link_blocked_by` 在兩週內的正常工作中找真實場景各跑至少一次；兩週內沒遇到就在示範 repo 開「[測試]」票補跑。

## 過關條件（已拍板）

第一階段跑兩週，以下全部達成才進第二階段：

1. 7 個操作加看板同步各實跑過，`get` 讀回一致。紀錄寫進 lifecycle 的 CHANGELOG（第一筆 GitHub 後端實測紀錄）。
2. 各階段數量最後連續 5 天差異 0（讀 reconcile log）。
3. 外洩掃描 0：兩個 repo 所有 issue 標題、內文、留言跑一次 `ticket_backend.py leak`。
4. 第二份週報（`ticket-report` 週報）的數字對得上 reconcile 的數量。第一週扣除。比的是週報產生當天的各階段存量，對同一天跑的 reconcile 的 feature 子票各階段數量；兩邊都排除「[測試]」票。週報的流量數字（新增、完成）沒有 reconcile 可對照，只檢查有沒有把補開的票算成新增（第二週不該出現）。
5. 發現的 bug 都已處理（修好或寫明不修的理由），每個 bug 在 plugharbor 開票追蹤。

## 考慮過的做法

看板同步放哪：

| 做法 | 取捨 |
|---|---|
| 擴充 ticket-ops 同步（採用） | 每次改階段都經同一條路，對帳能抓到 skill 的 bug；代價是每個操作多 2～3 次 `gh` 呼叫 |
| 用 Projects 內建 workflow 或 GitHub Actions 由 label 推 Status | skill 不用改；但看板對錯變成 GitHub 的事，驗不到 skill，canceled 也會被內建的 closed → Done 蓋掉 |
| 不用看板，只用 label | 最省；但使用者要看板（2026-11-14 裁決） |

驗證場地：只在私有沙盒 repo 驗被排除（使用者要拿真實專案示範）；直接上 Formwright 被排除（它在跑自動駕駛與新規則驗證，ticket bug 會拖慢它）；只補開未完成項目被排除（使用者選全部都開）。

## 驗收

- 前置修改 1～3 與 `reconcile.py`、`feature_checklist.py --tickets` 都有單元測試，過 `python3 scripts/ci/validate.py`。
- push 前用 `claude -p --plugin-dir plugins/lifecycle` 對 plugharbor 跑一次 `create`＋`set_stage`，確認看板 Status 與 label 都改到。
- 前置修改 4 的結論寫進 `github.md`。

## 撰寫時自行決定的事（待使用者確認）

使用者沒裁決過、由撰寫者定的：

- 沒有 roadmap 時用 feature.md 的 `##` 節當父票，「不做」節不開父票。
- 同步範圍擴到所有改清單的流程，不只打勾（否則新項目永遠沒有 `#n`，連續 5 天差異 0 做不到）。
- 父票階段由子票推導，整節關完就關父票。
- 對帳的分組計數、🚧 對 in-review 也算一致、triage 中的票與已關的 todo 票不算孤兒。
- 週報只比存量。
- 外洩檢查找不到 denylist 時，公開 repo 停下、私有 repo 警告後繼續。

## 留給 builder

- `github.md` 新「看板」一節的確切寫法與 `gh project` 指令參數細節。
- reconcile 每天怎麼跑（`/schedule` 或手動）。
- `feature_checklist.py --tickets` 的 JSON 細欄位名（上面是建議）。
