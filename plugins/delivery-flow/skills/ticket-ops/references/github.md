# GitHub Issues backend

用 `gh` CLI，repo 取自 `ticket.repo`（所有指令帶 `--repo <owner/repo>`）。先 `gh auth status`，未登入就停下請使用者登入。

## 操作對映

| 操作 | 指令 |
|---|---|
| `create` | `gh issue create --repo R --title T --body-file F --label L[,L2]`；`stage` 轉成 `labels_add` 併入 `--label` |
| `set_stage` | `gh issue edit N --repo R --add-label … --remove-label …`；`close` 為真時再 `gh issue close N --repo R --reason completed｜"not planned"` |
| `comment` | `gh issue comment N --repo R --body-file F` |
| `attach` | 見下 |
| `query` | `gh issue list --repo R --state all --label … --search "…" --json number,title,state,labels,updatedAt --limit 200` |
| `link_blocked_by` | 見下 |

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

GitHub 沒有官方的圖片上傳 API（網頁拖放走的是未公開端點，`gh` 與 REST 都不支援）。退路：

```bash
cd ${CLAUDE_SKILL_DIR}/scripts && python3 -c "import json,ticket_backend as t; print(json.dumps(t.github_attach_plan('<owner/repo>', '<圖檔路徑>', 'commit'), ensure_ascii=False))"
```

`github_attach_plan` 回 `{"method", "location", "markdown"}`：

- `commit`（預設）：圖存進 repo 的 `.github/ticket-assets/<檔名>`，`markdown` 是指向該檔的圖片連結。要先把檔案 commit 並 push 到預設分支，連結才有效；commit 前先跟使用者確認，因為會往 repo 加檔案。
- `gist`：`gh gist create <檔案>`，把回傳的 raw URL 替換 `markdown` 裡的佔位字串 `gist:<檔名>`。

限制：私有 repo 的連結只有登入且有權限的人看得到圖；兩種做法都會留下公開或 repo 內的檔案，敏感截圖不要用 gist（預設為 secret gist，知道網址的人仍可看）。把 `markdown` 放進 issue 描述或留言。

## 其他落差

- 沒有 priority、estimate、dueDate 原生欄位；需要時用 label（例如 `priority:high`）。
- 編輯描述：`gh issue edit N --body-file F` 整份取代，同樣先 `gh issue view N --json body` 讀回原文再改。
