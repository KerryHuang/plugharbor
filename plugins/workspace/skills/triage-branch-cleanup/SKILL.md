---
name: triage-branch-cleanup
description: 適用於盤點本地 branch / worktree / 殘留資料夾哪些可清理，交叉比對遠端 PR/MR 狀態與 ticket 狀態後逐項確認再刪除。觸發語：「哪些 branch 可以刪」「清一下已合併的」「盤點分支 / worktree」「哪些 ticket 做完可以收」「branch cleanup」「清理已 merge 的 worktree」。與 worktree skill 分工：worktree 管單一 worktree 機械 create/switch/remove；本 skill 管跨 branch/worktree/PR/ticket 的 portfolio 級盤點決策。
---

# Triage Branch Cleanup

跨「遠端 PR/MR 狀態 ＋ ticket 狀態 ＋ 本地 branch / worktree / 資料夾」三方盤點，決定哪些可安全清理，逐項互動確認後執行。

> **需要的能力**：查遠端 PR/MR 狀態（`gh` / `glab` 等，取權威 merged 狀態）、查 ticket 狀態（若團隊用議題系統）、解析 JSON（`jq`）。缺哪項就在該環節明示「無此來源，狀態未知」，不靜默略過。

## 核心決策邏輯

**訊號優先序**：遠端 PR/MR 的 `state` = **權威 merged 欄**；git 本地訊號（`git branch --merged` 推測、squash 合併的模糊判斷）僅在**查無對應 PR/MR** 時作 fallback。兩者矛盾時以遠端 PR/MR 為準。

| PR/MR state | 含義 | ACTION 傾向 |
|-------------|------|-------------|
| `merged` | 已合併 | **DELETE**（主判定） |
| `closed` | 被關閉（未合併） | **REVIEW**（分支可能仍有未合併工作） |
| `open` | 進行中 | **KEEP** |
| 查無 PR/MR | 無對應 PR/MR | fallback 到 git 訊號（已 merged → DELETE 候選；未 merged → REVIEW） |

**ticket 狀態僅作警示，不阻擋刪除**。ticket 為 `In Progress` / `In Review` / `Backlog` / `Todo` 時，DELETE 標記加 `(R)` 提示「ticket 尚未關閉，確定要刪？」，但不改變 DELETE 判定——以 PR/MR merged 為主。

## 建議任務拆解

逐一 `in_progress`→`completed`：

1. Preflight：遠端指向防護 + fetch
2. 盤點：取 git baseline（branch / worktree / merged 推測）
3. 補權威狀態：PR/MR dump + ticket 補查
4. 合併呈現：三方狀態表 + folder 掃描
5. 逐項確認：per-candidate 互動確認
6. 執行 + 驗證：archive tag → remove → prune → observable end state 驗證

## Task 1：Preflight — 遠端指向防護

**Goal**：確保查到的 PR/MR 是本專案的，而非殘留 remote 劫持到別專案。

```bash
git remote -v                       # 確認 origin 指向本專案
git config --get-regexp remote      # 檢查是否有殘留、指向他專案的 remote
git fetch --all --prune --quiet
```

- 看到指向他專案的殘留 remote → 先清，否則 PR/MR 狀態整組錯 → 誤刪。
- 在 worktree 內執行時：worktree 共用主 repo 的 `.git/config`，同樣風險；必要時從主 worktree 跑。

## Task 2：盤點 — git baseline

**Goal**：對每個 local branch 取一列基準資料。

```bash
git worktree list                                   # branch ↔ worktree 對照
git branch -vv                                      # 追蹤分支 / ahead-behind / gone
git branch --merged develop                         # 已合併進整合分支的推測
```

保留 branch / worktree path / 追蹤狀態 / merged 推測，供後續合併。

## Task 3：補權威狀態 — PR/MR + ticket

**Goal**：用遠端 PR/MR 覆蓋權威 merged 狀態，用議題系統補 ticket 狀態。

**一次 dump 全部 PR/MR，記憶體比對，勿 per-branch 打 N 次**（以 `gh` 為例，`glab` 同理）：

```bash
gh pr list --state all --limit 100 --json headRefName,state,number \
  | jq -r '.[] | "\(.headRefName)|\(.state)|#\(.number)"'
```

- 用 branch 名比對本地 branch → 取 `state` + PR/MR 編號。
- **同一 branch 多筆 PR/MR**（closed 後 reopen、或分支名重用）：**任一 `merged` → 視為 merged**；否則**取最新的一筆** state。**禁止** naive last-write-wins（回傳常是新到舊，last-write 會留到最舊那筆 → 靜默誤判）。
- **`--limit 100` 上限**：只涵蓋最近 100 筆。若本地有更舊分支未匹配到 → **明文告知**「branch X 未在最近 100 筆內，狀態未知」，**禁止**當作「無 PR/MR」靜默處理。

**ticket 補查**：對 git/PR 查不到狀態的 ticket，若團隊用議題系統，查其真實 status 作警示用。

## Task 4：合併呈現 — 三方狀態表 + folder 掃描

**Goal**：產出人類可讀的決策表，並掃出殘留資料夾。

合併表格欄位：

```
BRANCH | WORKTREE(folder) | PR/MR | TICKET | GIT-SIGNAL | ACTION
```

ACTION 依「核心決策邏輯」計算（PR/MR 優先、git 訊號 fallback、ticket 加 `(R)`）。

**孤兒資料夾掃描**：

```bash
MAIN=$(git rev-parse --show-toplevel)
ls -d "$MAIN"/../*/ 2>/dev/null    # 掃 repo 同層目錄
```

- 同層有 `<repo>-xxx` 命名、但**不在** `git worktree list` 內的實體資料夾 → 標 `REVIEW（孤兒資料夾）`，**絕不自動 `rm -rf`**（非 worktree 的實體資料夾誤刪風險太高，可能是任何東西）。
- worktree list 有、但目錄已不存在（孤兒 metadata）→ 標可 `git worktree prune`。

## Task 5：逐項確認（互動）

**Goal**：對每個 DELETE / DELETE(R) 候選，逐項確認取得刪除授權。

每個候選確認前，**先跑硬 gate 1（工作樹乾淨）與硬 gate 3（當前分支）**（見下方）。gate 未過 → 該候選降級 REVIEW，不列入確認、不刪。

每題附：branch / worktree path / PR/MR state+編號 / ticket status / 為何建議刪 / gate 檢查結果。

## Task 6：執行 + 驗證

**Goal**：對已授權候選執行清理，並驗證 observable end state（不信 remove 的回傳值）。

```bash
# 1. archive tag 備份（保留 ahead commit；squash merged 用 -D 前必做）
git tag archive/<branch-slug> <branch>

# 2. 移除 worktree（含資料夾）— 走 worktree skill §「Cleanup 前 preflight 檢查」
#    （cwd / 未提交變更 / IDE lock 檢查）

# 3. 刪 branch：已 merged 用 -d（safe）；squash merged / gone 用 -D（已備份 tag）
git branch -d <branch>     # 或 -D

# 4. 清孤兒 metadata
git worktree prune -v

# 5. Post 驗證（三方）
git worktree list | grep -F "<path>" && echo "❌ 仍在" || echo "✅ 已移除"
test -d "<path>" && echo "❌ 資料夾仍在（檔案鎖）" || echo "✅ 已消失"
git branch -a | grep -F "<branch>" && echo "❌ branch 還在" || echo "✅ 已刪"
```

**驗證（binary）**：每個授權候選——worktree 不在 list、資料夾消失、branch 已刪、archive tag 存在。任一未達 → 該候選**未完成**，回報檔案鎖等原因，不假裝成功。

## 硬 Gate（動手前必查）

| # | Gate | 檢查 | 未過的動作 |
|---|------|------|-----------|
| 1 | **工作樹乾淨才可刪**（最高，防資料遺失） | `git -C "<worktree>" status --porcelain` | 非空 → 降級 REVIEW，**禁**自動 `--force`。archive tag 只備份 committed commits，救不了未 commit 的 modified/untracked |
| 2 | **遠端指向防護** | Task 1（`git remote -v`） | 有指向他專案的殘留 remote → 先清再查 PR/MR |
| 3 | **不刪當前站著的 worktree/branch** | `git rev-parse --abbrev-ref HEAD` / 當前 cwd 是否在候選 worktree 內 | 是 → 提示「先 cd 出去 / 切分支」，不硬跑（會失敗還以為成功） |
| 4 | **孤兒資料夾只 REVIEW 不 rm** | Task 4 folder 掃描 | 非 worktree 的 sibling 資料夾一律只列出，不自動 `rm -rf` |

## Red Flags — STOP

- 「PR 顯示 merged，直接 `--force` 刪掉省事」→ **先查 `git status --porcelain`**，worktree 可能有未 commit 檔（archive tag 救不了未 commit 的內容）。
- 「查到的 PR/MR 狀態就對」→ **先驗 `git remote -v`**，殘留 remote 會指到別專案 → 誤刪。
- 「這資料夾看起來是舊 worktree，rm 掉」→ 不在 `git worktree list` 內的實體資料夾**只 REVIEW**，絕不自動 rm。
- 「站在這個 worktree 內直接刪它自己」→ 先 cd 出去，否則 remove 失敗還以為成功。
- 「ticket 還在 In Review 但 PR merged，不敢刪」→ ticket 僅警示，PR merged 為主判定；問使用者但不阻擋。
- 「git 說 squash 過就是可刪」→ git 訊號只是**查無 PR/MR 時**的 fallback；有 PR/MR 時以其 state 為準。

## References

- `worktree` skill §「Cleanup 前 preflight 檢查」— 委派的實際移除執行器（cwd / 未提交變更 / IDE lock 檢查 + observable end state 驗證）。
