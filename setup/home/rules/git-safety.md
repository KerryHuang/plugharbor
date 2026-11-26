# Git 安全

## 暫存（staging）

- `git add -A` / `git add .` 由 guard `git-add-all` 擋下（理由見 toolkit plugin 的 `guards/`）；一律從 `git status --short` 清單**逐檔指名** add。
- commit 前必驗 staged：`git status` 確認暫存區只含本次要提交的檔案；
  多出來的用 `git restore --staged <檔>` 移出，不要一起提交。
- 逐檔 add 擋不住**同一個檔裡別人的 hunk**：add 前先 `git diff <檔>`，有不是自己的改動就只暫存自己那段
  （`git add -p` 不能用時：以 HEAD 版本加上自己的改動做出 blob，`git hash-object -w` 後 `git update-index --cacheinfo`），commit 前看 `git diff --cached`。
- `add`、`status`、`commit`、`push` **拆成各自獨立的工具呼叫**，不用 `&&` 串接：串在一起時 status 印出來也沒機會讀，複驗形同虛設。
- 誤掃已 push 的內容，勿自行 revert/reset 硬修（會跟並行作業打架），先協調再收斂。

## 並行作業

- 改版控檔前先 `git fetch` ＋ `git status -sb`，落後就先 pull；診斷「某某壞了」前先看該檔的 `git log --oneline -3 -- <檔>`，可能別的 session 已經修好。
- 記得有未推 commit、`origin/<分支>..HEAD` 卻是空的：先查 `git reflog`，多半是被別人 `pull --rebase` 換了 hash 一起推上去了。驗內容（`git show origin/<分支>:<路徑>`）不驗 hash，不要重做或 revert。commit 後儘快 push 以縮短這個視窗。

## 破壞性操作

- force push 任何遠端分支前，先列出確切指令與目標分支，取得使用者明確同意才執行（guard `git-destructive` 會跳確認）。
- `reset --hard`、`clean -fd`、刪遠端分支同樣先確認；不確定影響範圍就先 `git stash` 或備份。
