---
name: submodule-relay
description: git submodule 容器的提交與同步接力——子模組 commit → push → 上層 pointer bump，以及 pull／rebase 後驗 pointer 沒倒退。含 `M` 的方向判讀（何時 bump、何時該 pull、何時別動）。Use when 在 submodule 容器 repo 提交或同步、「bump pointer」「commit submodule」「push 子模組」「pull submodule」「submodule 顯示 M」「上層 repo 要不要更新 ref」。
---

# Submodule 接力

容器 repo（上層）只記每個子模組的 commit pointer；真正的變更在子模組裡。接力順序固定：
**子模組 commit → 子模組 push 成功 → 上層 bump pointer**。順序反了或中間斷了，上層就會記一個遠端不存在的 commit，別人 clone 直接壞。

提交訊息格式、逐檔暫存、多 agent 並行安全一律照 `commit`；本 skill 只管子模組特有的部分。

## 子模組清單：從 `.gitmodules` 讀，不寫死

```bash
git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}'
git config -f .gitmodules --get-regexp '^submodule\..*\.branch$'   # 有設才有，沒設就看該子模組 origin/HEAD
```

任何掃描（哪些子模組有變更、哪些落後遠端）都以這份清單為準，不在文件或 skill 裡維護靜態對照表——子模組增刪時靜態表一定會漂移。

## 1. 看懂 `git status` 上的子模組狀態

`.gitmodules` 的 `ignore` 級別決定上層 `git status`／`git diff` 看得到什麼：

| `ignore` | 會報 |
|---|---|
| `none` | `?` ＋ `m` ＋ `M` |
| `untracked` | `m` ＋ `M` |
| `dirty` | `M` |
| `all` | 全部沉默——**連 `M` 都藏** |

`?` 子模組有未追蹤檔｜`m` 子模組有已追蹤改動｜`M` 子模組 HEAD 與上層記錄的 pointer 不一致。

- **只有 `M` 是 bump 的訊號**；`?`、`m` 多半是別人進行中的工作，不是你該收的。
- 設成 `all` 時 pointer 倒退也是隱形的。要看全貌用 `git status --ignore-submodules=none`。
- 自查目前級別：`git config -f .gitmodules --get-regexp ignore`。

## 2. 看到 `M`：先分方向，兩種處置相反

取值：

```bash
idx=$(git ls-tree HEAD <path> | awk '{print $3}')    # 上層記錄的 pointer（index）
co=$(git -C <path> rev-parse HEAD)                    # 子模組目前 checkout
git -C <path> fetch --quiet origin
```

| 方向 | 判準 | 動作 |
|---|---|---|
| index 落後 checkout | `git -C <path> log --oneline $idx..$co` 有東西 | **且** checkout 已在遠端 → bump |
| index 超前 checkout | `git -C <path> log --oneline $co..$idx` 有東西 | `git -C <path> pull` 讓工作目錄追上，**不要 bump**——bump 等於把別人推上去的 commit 靜默 revert |
| 兩邊分叉 | 兩向都有 | 先查是誰的工作，不要自行收斂 |
| checkout 領先但未推遠端 | `git -C <path> branch -r --contains $co` 為空 | **不要 bump**，先 push 子模組（或交給它的主人） |

「pointer 不一致就 bump」是錯的直覺：index 超前時照做會把上層 pointer 寫回舊 commit，而在 `ignore = all` 下這個倒退連 `git status` 都看不到。

## 3. 提交接力

1. **子模組 commit**：照 `commit` 流程，用 `git -C <path> ...` 操作，不 `cd` 進去（shell 停在子模組裡，後續指令容易打錯 repo）。
2. **詢問是否 push**。否 → 結束，明說「上層 pointer 尚未 bump」。
3. **push 子模組**：`git -C <path> push`，**單獨一次呼叫**，讀它的 exit code。
   - 失敗 → 顯示原始錯誤，**不 bump**、不自動修。
   - ❌ 不要 `git -C <path> push 2>&1 | tail -2 && git add <path> && git commit ...`：管線的 exit code 是 `tail` 的 0，push 被拒也照樣往下 bump。要串就 `set -o pipefail` 或乾脆分兩步。
4. **bump 前驗遠端**：`git -C <path> branch -r --contains $(git -C <path> rev-parse HEAD)` 必須非空。
5. **上層 bump**（逐檔指名，複驗暫存區獨立一步）：
   ```bash
   git add <path>
   git diff --cached --name-only        # 只該有這個子模組；多的 git restore --staged 移出
   git commit -m "chore: bump <name> pointer (<子模組 commit 主旨>)"
   ```
6. 上層要不要 push 依專案慣例；容器 repo 常是私人備份或需另行同意，**不預設自動 push**。

## 4. 同步（pull）

- 先 fetch 再看誰落後：對上層與清單中每個子模組 `git -C <path> fetch` 後 `git -C <path> status -sb`，找 `behind`。
- 上層 fetch 用 `git fetch --no-recurse-submodules`：預設會連帶抓子模組，遇到 "not our ref" 時整個 exit 1，但上層 fetch 本來就不需要子模組。
- 子模組逐一 `git -C <path> pull`，逐一回報結果；衝突顯示原始錯誤，不自動解。

### 🔴 根目錄禁 `git submodule update --recursive`

子模組本身可能是自帶大量巢狀 submodule 的 monorepo，`--recursive` 會全部 clone（量級可達數百 MB），
錯誤又常被管線吞掉，事後才發現工作目錄變髒。只更新指名子模組：

```bash
git submodule update --init <path>     # 不加 --recursive
```

誤拉後，在該子模組內 deinit 不該 init 的巢狀子模組（zsh 不會把換行拆成多參數，走 `xargs`）：

```bash
git config --file .gitmodules --get-regexp path | awk '{print $2}' | xargs git submodule deinit -f --
```

`deinit` 不清 `.git/modules/.../modules/` 下的 gitdir，要騰空間另外刪。

### 上層有本機領先 commit 時：rebase 前後比對

只改 pointer 的 commit 曾在 rebase 時被**靜默丟掉**（沒報錯、todo 裡也沒有 pick），`git diff` 看不出來。只要 `@{u}..HEAD` 非空：

1. pull 前記兩樣：`git log --format=%s @{u}..HEAD`（領先 commit 標題）、每個子模組的 `git ls-tree HEAD <path>`。
2. pull 後比兩樣：
   - 每個舊標題都還在新的 `@{u}..HEAD` 裡（rebase 改 SHA，比標題不比 SHA）。
   - 每個子模組新 pointer 等於舊 pointer 或是其後代：`git -C <path> merge-base --is-ancestor <舊> <新>`。
3. 任一不成立 → **停下，不 push**。列出掉的 commit 與倒退的 pointer，從 `git reflog` 找回或補 bump，修法由使用者決定。

### pointer 衝突

先 `git -C <path> merge-base --is-ancestor <a> <b>` 判新舊，再用較新的那個：
`git update-index --cacheinfo 160000,<sha>,<path>`。

## Red Flags

| 念頭 | 實際上 |
|---|---|
| 「status 顯示 M，bump 一下就好」 | 先分方向；index 超前時 bump 是 revert |
| 「push 應該成功了，接著 bump」 | 沒讀到 push 的 exit code 就不算成功 |
| 「pull 完順手 `submodule update --init --recursive`」 | 只 init 指名子模組，不遞迴 |
| 「rebase 沒報錯，直接 push」 | 先比領先 commit 數與 pointer |

## 與其他 skill 銜接

- `commit` — 訊息格式、逐檔暫存、並行安全
- `worktree` — 別的 session 有未推 commit 時另開
- `release` — 發版時子模組的處理見 [../release/references/submodules.md](../release/references/submodules.md)
