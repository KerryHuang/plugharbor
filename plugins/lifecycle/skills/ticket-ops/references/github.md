# GitHub Issues backend

送出內文（建票、留言、改描述、附圖說明）前先照 SKILL.md §2 做外洩檢查。

用 `gh` CLI，repo 取自 `ticket.repo`（所有指令帶 `--repo <owner/repo>`）。先 `gh auth status`，未登入就停下請使用者登入。

## 操作對映

| 操作 | 指令 |
|---|---|
| `create` | `gh issue create --repo R --title T --body-file F --label L[,L2]`；`stage` 轉成 `labels_add` 併入 `--label`。帶 `parent` 時加 `--parent p`（原生 sub-issue，見「父子票」） |
| `set_stage` | `gh issue edit N --repo R --add-label … --remove-label …`；`close` 為真時再 `gh issue close N --repo R --reason completed｜"not planned"` |
| `comment` | `gh issue comment N --repo R --body-file F` |
| `attach` | 見下 |
| `query` | `gh issue list --repo R --state all --label … --search "…" --json number,title,state,stateReason,labels,updatedAt,createdAt,closedAt,assignees,url,parent --limit 1000`（`parent` 取 `.parent.number`；依 parent 篩選在取回後自己過濾，`--search "parent-issue:…"` 實測查不到）；時間範圍用 `--search "created:A..B"`、`--search "closed:A..B"`、`--search "updated:A..B"`，**一次只放一個時間欄位**——同一個 search 裡的多個條件是 AND，`created:… closed:…` 只會回窗內建立且窗內關閉的票。**不得靜默截斷**，見下「查詢不截斷」。`階段` 由 `stage:*` label 與 `state` 還原，label 不在 `ticket.states` 對照內時回 `unmapped:<name>`（叫用端列為未分類，不計入任何階段） |
| `get` | `gh issue view N --repo R --json number,title,body,state,stateReason,labels,url,updatedAt,parent,subIssues`；`parent` 取 `.parent.number`（null 即無），`children` 取 `.subIssues.nodes[].number`（`totalCount` 比 nodes 多時改用 `gh api repos/R/issues/N/sub_issues --paginate`）；`stage` 由 `stage:*` label 與 `state` 還原 |
| `link_blocked_by` | `gh issue edit m --repo R --add-blocked-by n`（原生，見下「blocked-by」） |

`query` 欄位對映：`closedAt` 且 `stateReason` 為 `COMPLETED` 才填 `completedAt`；以 not planned 關閉的票 `completedAt` 為 null，不算交付。`createdAt`、`url` 直接取；`assignee` 取 `assignees` 陣列第一位的 `login`，陣列為空則 null。`priority` 取自 label `priority:<level>`（level 為 urgent／high／medium／low），無此 label 為 `none`。`dueDate` 恆為 null（GitHub 不支援）。

## 查詢不截斷

`gh issue list` 不回「還有更多」的訊號，筆數到 `--limit` 就停；帶 `--search` 時走 search API，單次查詢上限 1000 筆。所以：

1. 每次查詢帶 `--limit 1000`，並比對回傳筆數。
2. 筆數 **< 1000** → 視為完整。筆數 **＝ 1000**（或剛好等於所下的 limit）→ 視為可能截斷，**不得直接使用**：把時間窗對半切（以 `created:A..B` 或 `updated:A..B`），逐段重查再合併，並依票號去重；每一段都 < 1000 才算查完。
3. 切到單日仍 ≥ 1000，或改不了窗（例如只有存量、沒有時間條件）→ 改 `gh api --paginate "search/issues?q=…"` 逐頁取；仍拿不全就停止，並**在回傳與報表明寫「查詢可能被截斷：實際取得 N 筆，已達上限」**，數字一律標「下限」，不得當完整結果交出。
4. 回傳要附一行 `query 完整性：完整｜已分段合併（N 段）｜可能截斷`。報表要把這一行帶進來。

階段 label 要先存在：`gh label create "stage:todo" --repo R`（已存在會報錯，忽略即可）。重新開啟已關閉的票改階段時，先 `gh issue reopen`。`body` 一律用 `--body-file`，避免 shell 跳脫。

## 父子票

用 GitHub 原生 sub-issue（2026-11-14 在公開 repo 實測，gh 2.98）：

- 建子票：`gh issue create … --parent p`；既有票掛上：`gh issue edit n --repo R --parent p`。
- 換 parent：先 `gh issue edit n --repo R --remove-parent` 再 `--parent q`。對同一個 parent 重掛會報錯「Issue may not contain duplicate sub-issues」，先讀 `.parent.number` 一樣就跳過。
- 讀回：`gh issue view n --json parent,subIssues,subIssuesSummary`；改完一定讀回確認。
- 父票的 `subIssuesSummary` 把 not planned 關閉的子票也算進完成，進度不等於交付，報表不拿它當完成數。
- 沒有自動 rollup：父票不會因子票全關而自動關，由叫用端照規則關。

退路：`gh issue create --help` 沒有 `--parent`（舊版 gh），或 API 回錯時，改用內文慣例並在回報寫明降級：子票 body 加一行 `parent: #p`，全部子票建完後在父票 body 回填 `- [ ] #n` 清單（`gh issue view` 讀回原文、附加、`gh issue edit --body-file`）；`get` 的 parent／children 改從 body 解析。

## blocked-by

用原生 issue dependencies：`gh issue edit m --repo R --add-blocked-by n`（建票當下可用 `gh issue create … --blocked-by n`）；移除用 `--remove-blocked-by n`。讀回 `gh issue view m --json blockedBy`，blocker 那邊 `gh api repos/R/issues/n/dependencies/blocking`。

限制（實測）：blocker 關閉後，被擋票的 timeline 沒有新事件、關係也不會自動移除（`blockedBy` 仍列出已關的 blocker），等於沒有「可以開工了」的通知。要通知就在關閉 blocker 時對被擋票留言 `@` 下一關；判斷是否仍被擋要看 blocker 的 `state`。

退路：gh 沒有 `--add-blocked-by` 或 API 回錯時，被擋票 body 加一行 `blocked-by: #n`、掛 `blocked` label（無此 label 先 `gh label create blocked --repo R`），對 blocker 留言 `blocks #m`；回報寫明降級。

## 附圖

GitHub 沒有官方的圖片上傳 API（網頁拖放走的是未公開端點，`gh` 與 REST 都不支援）。唯一做法是把圖存進 repo，用連結內嵌。連結**只有檔案 push 到預設分支後才有效**，所以步驟不可跳：

1. 取得計畫：`cd ${CLAUDE_SKILL_DIR}/scripts && python3 -c "import json,ticket_backend as t; print(json.dumps(t.github_attach_plan('<owner/repo>', '<圖檔路徑>'), ensure_ascii=False))"`，得 `{"method":"commit","location","markdown"}`。
2. 把圖複製到 repo 的 `location`（`.github/ticket-assets/<檔名>`）。
3. commit（逐檔 `git add`）。
4. **徵得使用者確認後** push 到預設分支（會往 repo 加檔案、公開或對所有有權限者可見）。
5. push 成功才把 `markdown` 貼進 issue 描述或留言。

硬規則：push 沒發生或使用者拒絕時，不貼 markdown（會是壞圖），回報「圖仍在本機 <path>，未附」。不得在 push 成功以外的情況回報「已附圖」；回報要寫明圖的實際位置與連結是否有效。

限制：私有 repo 的連結只有登入且有權限的人看得到圖。

## 其他落差

- 沒有 priority、estimate、dueDate 原生欄位；需要時用 label（例如 `priority:high`）。
- 編輯描述：`gh issue edit N --body-file F` 整份取代，同樣先 `gh issue view N --json body` 讀回原文再改。
