---
name: commit
description: 建立符合 Conventional Commits 規範的語義化提交訊息，支援 Git Flow + Semantic Release 工作流程。Use when creating git commits, "commit 這些變更", "幫我提交", "建立 commit", "semantic commit".
---

# 建立語義化提交

產生並建立遵循 Conventional Commits 規範的提交訊息。

## 工作流程

1. **檢查狀態** - `git status && git branch`（確認在正確分支，非 main/develop 直接提交）
2. **檢視變更** - `git diff --staged`（未 stage 則先逐檔 `git status --short` 指名 add，禁止 `git add -A`）
3. **複驗暫存區（獨立一步）** - 單獨跑 `git diff --cached --name-only`，多出非本次的檔就 `git restore --staged <檔>` 移出（見「多 agent 並行安全」）
4. **commit 前驗證** - 走 `quality-check` 的「commit 前驗證原則」，沒讀到 exit code 不提交
5. **分析並產生訊息** - 依變更內容判定 type / scope，寫成 Conventional Commits 格式
6. **使用者批准** - 提交前先出示訊息供確認
7. **建立提交** - `git commit -m "..."`

> repo 是 submodule 容器、或要提交的是子模組時，commit 後的 push 與上層 pointer bump 走 `submodule-relay`。

## 多 agent 並行安全

同一個 checkout／同一條分支常有別的 agent 或 session 同時在動，HEAD 與暫存區在兩次工具呼叫之間就可能被改過。

### 暫存

- **禁 `git add -A`／`git add .`**：一律從 `git status --short` 清單逐檔指名。全量 add 會把別人 pre-staged 的檔包進你的 commit。
- **複驗與 commit 拆成不同呼叫**：不要寫成 `add && 計數 && commit && push` 一條串完——計數印出異常也擋不住後面的步驟。
  順序固定為：① 逐檔 `git add`；② 單獨 `git diff --cached --name-only` 檢查；③ 確認後才 commit。
- 未帶路徑的 `git commit` 會提交**整個**暫存區：別人預先暫存的刪除、新增都會被一起帶走。
- **工作期間刪檔用 `rm`，不用 `git rm`**：`git rm` 立刻改暫存區，別人的 commit 會把你的刪除帶上遠端；要 commit 當下才逐檔 `git rm`／`git add`。

### 歷史改寫

- **共用分支禁 `commit --amend`、`rebase -i`**：`--amend` 不檢查 HEAD 是誰的，別的 session `pull --rebase` 後，
  你的 amend 可能塞進別人已 push 的 commit，造成本機與遠端分叉。一律開新 commit。
- 真要 amend：先 `git log -1 --format='%h %s'` 確認 HEAD 是自己剛做的，且 `git rev-list --count origin/<分支>..HEAD` ≥ 1（還沒推上去）。
- 事故訊號：`git log -1` 出現不是你寫的 commit message → 停下，別在上面疊 amend。

### 別人有未推的 commit 時

- 同一個 checkout 裡別的 session 有本機未推 commit，你不要在上面疊自己的 commit 再一起推——用 `worktree` 從 `origin/<分支>` 另開一份作業。
- push 前先 `fetch` 看 ahead／behind；被拒不要 force，`pull --rebase --autostash` 後再推。
- 誤把別人的檔包進**已 push** 的 commit：不要自行 revert／reset（會跟對方的工作打架），通知對方協調收斂。

## 提交類型

### 版本號變更

| 類型 | 說明 | 版本影響 |
|------|------|----------|
| `feat` | 新功能 | MINOR |
| `fix` | Bug 修復 | PATCH |
| `perf` | 效能改進 | PATCH |
| `feat!` | 破壞性變更 | MAJOR |

### 無版本號變更

| 類型 | 說明 |
|------|------|
| `docs` | 文件變更 |
| `style` | 格式調整 |
| `refactor` | 重構 |
| `test` | 測試 |
| `build` | 建置系統 |
| `ci` | CI/CD |
| `chore` | 維護 |

## Scope 建議

Scope 依專案實際模組命名，取變更集中的區域。常見面向：

### 架構層級
`domain`, `application`, `persistence`, `presentation`, `api`, `ui`

### 基礎設施
`db`, `docker`, `ci`, `deps`, `tests`, `config`, `build`

> 沒有明確 scope 時可省略；不要硬套不存在的模組名。

## Git Flow 整合

```bash
# 功能開發
git flow feature start user-auth
git commit -m "feat(auth): implement JWT authentication"
git flow feature finish user-auth

# 發布版本
git flow release start auto
git flow release finish -n auto  # -n 跳過自動 tag
```

## 重要規則

- ✅ 使用英文撰寫提交訊息主體
- ✅ 使用 `-n` 跳過 Git Flow 自動 tag（版本號交給 Semantic Release / CI）
- ❌ 不要手動建立 Git tag
- ❌ 不要直接在 main/develop 提交
- ❌ 禁止 `git add -A` / `git add .`——逐檔指名 add，提交前複驗 staged 只含本次變更
- ❌ 共用分支禁止 `commit --amend` / `rebase -i`
- ❌ commit 被 pre-commit hook 擋下時，不自行加 `--no-verify` 或繞過用的環境變數重試；把 hook 訊息原文交給使用者
