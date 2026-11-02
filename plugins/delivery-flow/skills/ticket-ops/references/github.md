# GitHub Issues backend

用 `gh` CLI，repo 取自 `ticket.repo`（所有指令帶 `--repo <owner/repo>`）。先 `gh auth status`，未登入就停下請使用者登入。

## 操作對映

| 操作 | 指令 |
|---|---|
| `create` | `gh issue create --repo R --title T --body-file F --label L[,L2]`；`stage` 轉成 `labels_add` 併入 `--label` |
| `set_stage` | `gh issue edit N --repo R --add-label … --remove-label …`；`close` 為真時再 `gh issue close N --repo R --reason completed｜"not planned"` |
| `comment` | `gh issue comment N --repo R --body-file F` |
| `attach` | 見下 |
| `query` | `gh issue list --repo R --state all --label … --search "…" --json number,title,state,stateReason,labels,updatedAt,createdAt,closedAt,assignees,url --limit 1000`；時間範圍用 `--search "created:>=… closed:>=…"`。**不得靜默截斷**，見下「查詢不截斷」。`階段` 由 `stage:*` label 與 `state` 還原，label 不在 `ticket.states` 對照內時回 `unmapped:<name>`（叫用端列為未分類，不計入任何階段） |
| `get` | `gh issue view N --repo R --json number,title,body,state,stateReason,labels,url,updatedAt`；`children` 解析 body 內 `- [ ] #n`／`- [x] #n` 項目的 n；`parent` 取 body 內 `parent: #n` 那一行（父子票慣例見下），沒有就是 null；`stage` 由 `stage:*` label 與 `state` 還原 |
| `link_blocked_by` | 見下 |

`query` 欄位對映：`closedAt` 且 `stateReason` 為 `COMPLETED` 才填 `completedAt`；以 not planned 關閉的票 `completedAt` 為 null，不算交付。`createdAt`、`url` 直接取；`assignee` 取 `assignees` 陣列第一位的 `login`，陣列為空則 null。`priority` 取自 label `priority:<level>`（level 為 urgent／high／medium／low），無此 label 為 `none`。`dueDate` 恆為 null（GitHub 不支援）。

## 查詢不截斷

`gh issue list` 不回「還有更多」的訊號，筆數到 `--limit` 就停；帶 `--search` 時走 search API，單次查詢上限 1000 筆。所以：

1. 每次查詢帶 `--limit 1000`，並比對回傳筆數。
2. 筆數 **< 1000** → 視為完整。筆數 **＝ 1000**（或剛好等於所下的 limit）→ 視為可能截斷，**不得直接使用**：把時間窗對半切（以 `created:A..B` 或 `updated:A..B`），逐段重查再合併，並依票號去重；每一段都 < 1000 才算查完。
3. 切到單日仍 ≥ 1000，或改不了窗（例如只有存量、沒有時間條件）→ 改 `gh api --paginate "search/issues?q=…"` 逐頁取；仍拿不全就停止，並**在回傳與報表明寫「查詢可能被截斷：實際取得 N 筆，已達上限」**，數字一律標「下限」，不得當完整結果交出。
4. 回傳要附一行 `query 完整性：完整｜已分段合併（N 段）｜可能截斷`。報表要把這一行帶進來。

階段 label 要先存在：`gh label create "stage:todo" --repo R`（已存在會報錯，忽略即可）。重新開啟已關閉的票改階段時，先 `gh issue reopen`。`body` 一律用 `--body-file`，避免 shell 跳脫。

## 父子票

- 內文 task list：父票 body 放 `- [ ] #n`，GitHub 會顯示進度；子票 body 放 `parent: #p`。
- 若 repo 啟用了 sub-issues，可改用它；啟用與否要先實測，沒把握就用 task list。
- 沒有像 Linear 那樣的自動 rollup 與自動化。

## blocked-by

GitHub 沒有穩定可用的 CLI 級 blocked-by 欄位，採慣例：

1. 被擋住的票 body 加一行 `blocked-by: #n`。
2. 被擋住的票掛 label `blocked`（若 repo 有此 label）。
3. blocker 票 body 的 task list 或留言提到被擋住的票。

限制：沒有「blocker 完成時通知」的語意。要通知就在關閉 blocker 時留言 `@` 下一關。叫用端要拿到「降級為內文慣例」的說明。

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
