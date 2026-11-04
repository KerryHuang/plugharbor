---
name: release
description: 分關卡發版：建 release branch、品質閘、merge 回 main 等 CI 建 tag、反合 develop、清理；處理線上急修（hotfix）；中斷後從第一個沒過的關卡接續，merge 前驗 HEAD 沒被推新 commit。前提是專案採 Git Flow＋Semantic Release（tag／版號由 CI 依 Conventional Commits 產生）。Use when 「發版」「出 release」「跑 hotfix」「合回 develop」「release flow」「semantic release」「發版到一半斷了」。
argument-hint: "[release|hotfix] [版本號或說明]"
---

# 分關卡發版

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

適用 **Git Flow＋Semantic Release**：`feature/` → `develop` → `release/` → `main`，外加 `hotfix/`。

## 重要前提

- **不手動建 tag、不手動 bump 版號**：都由 CI（semantic-release）依 Conventional Commits 產生。
- **子模組有改動**：先 commit 並 push 子模組，再回主 repo 更新 ref（見 `references/submodules.md`）。
- **長流程**：release／hotfix 含多段 merge 與等 CI，常超過 5 分鐘。每關開始與結束都回報一行，等 CI 時定時回報，別讓使用者以為卡住。
- force push、`reset --hard`、刪遠端分支：先列出確切指令與目標，取得使用者明確同意。

## 關卡與續做

發版拆成關卡，每關有可重跑的檢查指令。狀態記在 `.tmp/release/<版本>/gates.md`（不進 git），一關一列：`關卡｜通過／未過｜時間｜證據（指令輸出或 SHA）`，另記 R2 的「已檢查 SHA」。

**續做規則**：進入本 skill 時若 `gates.md` 已存在，或使用者說發版中斷了，從 R1 起依序重跑各關的檢查指令，**第一個沒過的關卡就是接續點**；不憑 `gates.md` 的舊紀錄直接跳關（檔案可能過時）。

| 關卡 | 內容 | 通過檢查 |
|---|---|---|
| R0 | 選路徑（Fast／Full） | `gates.md` 有記錄 |
| R1 | develop 乾淨、未重複發版 | `git status --short` 空；`git submodule status` 無 `+`；`git ls-remote --tags origin vx.y.z` 無輸出 |
| R2 | 品質閘 | 對 release branch HEAD 跑 build／lint／test 全綠；記下該 HEAD 為「已檢查 SHA」 |
| R3 | 建 release branch | `git rev-parse --verify release/x.y.z` 成功；Full Path 另驗 `origin/release/x.y.z` 存在 |
| R4 | （Full）QA 驗 rc | QA 對「已檢查 SHA」的 rc 回報通過，記進 `gates.md` |
| R5 | merge 到 main | merge 前 release branch HEAD 等於「已檢查 SHA」；`origin/main` 含 `merge release/x.y.z` |
| R6 | CI 建正式 tag | `git ls-remote --tags origin vx.y.z` 有輸出；`origin/main` 頭是 `chore(release): x.y.z` |
| R7 | 反合 develop | `git merge-base --is-ancestor vx.y.z origin/develop` 成功 |
| R8 | 清理 | `release/x.y.z` 本地（Full 含遠端）已刪 |

R2 之後 release branch 若有新 commit（例如 R4 修 rc bug），「已檢查 SHA」失效：回 R2 對新 HEAD 重跑。這是 merge 前防止「檢查後有人推新 commit」的唯一依據，細節與 `--match-head-commit` 用法見 `references/merge-to-main.md`。

## R0：選路徑

進任何動作前先問使用者：**本次需要 QA 測 rc 版嗎？**（推薦 Fast，除非專案要求 QA）

| 項目 | Fast Path | Full Path |
|---|---|---|
| release branch push 到 origin | 不 push | 要 |
| rc tag（`vx.y.z-rc.N`） | 不產 | 產 |
| QA 階段（R4） | 跳過 | 有 |
| R8 清理 | 只刪本地 | 刪本地＋遠端＋多餘 rc tag |

## R1：確認 develop

```bash
git checkout develop && git pull origin develop
git status --short
git submodule status
git fetch --tags origin
git tag --sort=-creatordate | grep -v "beta\|rc" | head -5
```

- main 已有預計發版的正式 tag → **停止，已發版完成**。
- 有未提交變更 → 先問使用者處理。
- 子模組 `+`：本次要發子模組的新 commit → 先 commit 子模組再更新主 repo ref；不納入本次 → 問使用者，不納入就忽略。

## R2：品質閘

用 `workspace:quality-check`（可選；沒裝就跑專案自帶的 type-check、lint、build、test）對 release branch 的 HEAD 跑（R3 之前則對 develop HEAD 跑，R3 建出的分支 HEAD 必須同 SHA）。全綠才記「已檢查 SHA」＝`git rev-parse HEAD`。失敗 → 停下，不建 release branch；要追根因時用 `workspace:debugging`（可選；沒裝就先寫重現失敗的測試再修）。

## R3：建 release branch

```bash
git checkout -b release/x.y.z develop
git push origin release/x.y.z        # 只有 Full Path；推送後 CI 產 rc.1
```

Fast Path 不 push（release branch 只在本地，CI 不觸發 rc），直接到 R5。

## R4：（Full Path）QA 與修 rc bug

等 QA 在 rc 環境測。修 rc bug：

```bash
git add <檔>                         # 逐檔指名，不用 git add -A
git commit -m "fix(scope): 修復 rc 測試發現的問題"
git push origin release/x.y.z        # CI 產 rc.N+1
```

修完 HEAD 已變 → 回 R2 重驗，QA 對新 rc 再回報通過才算 R4 過。

## R5–R6：merge 到 main、等 CI 建 tag

merge 前先驗 HEAD 等於「已檢查 SHA」，merge commit **不加 `[skip ci]`**，push 後等 CI 建正式 tag。衝突處理（版號檔／CHANGELOG）、CI 情境 A／B 判別、CI 失敗 rollback 都在 `references/merge-to-main.md`。

## R7：反合 develop

> **前提**：R6 已過（`origin/main` 可見 `chore(release): x.y.z`）。否則反合拿不到 CI 產的 release commit，正式 tag 不在 develop ancestry，**下一輪 beta 會卡在舊序列**（版號異常最常見的根因）。

```bash
git fetch origin --tags
git checkout develop && git pull --ff-only origin develop
git merge --no-ff origin/main -m "chore: sync develop after release/x.y.z [skip ci]"
git push origin develop
git merge-base --is-ancestor vx.y.z origin/develop && echo "R7 通過" || echo "R7 未過"
```

- merge 來源**只能是 `origin/main`**：`release/x.y.z` 缺 CI 產的 release commit，本地 `main` 可能落後。
- 加 `[skip ci]`：避免 develop CI 因反合進來的 release commit 重複觸發而跳號。push 後 develop CI 不觸發 beta 是正確結果。
- 專案要求線性歷史（develop rebase 到 `origin/main`）→ 改照 `references/rebase-sync.md`。

## R8：清理

```bash
git branch -d release/x.y.z
# 只有 Full Path：
git push origin --delete release/x.y.z
git tag -d vx.y.z-rc.1 && git push origin --delete vx.y.z-rc.1   # 多餘的 rc tag
```

全部關卡通過後，經使用者同意刪 `.tmp/release/<版本>/`。

## Hotfix、子模組與疑難排解

命中才讀：

- **Hotfix**（從 main 開 hotfix branch，預設 Fast Path 不問 QA；同樣分關卡、merge 前驗 HEAD）→ `references/hotfix.md`
- **含子模組的 repo** → `references/submodules.md`
- **版號異常、tag 指向錯誤 commit** → `references/troubleshooting.md`
- **線性歷史、rebase 遇 release-only commit 衝突** → `references/rebase-sync.md`

## Red Flags — STOP

- 「直接 commit 到 main／develop 就好」→ 所有修復與功能**必須**走 branch，版號由 CI 從 branch merge 觸發。
- 「直接 merge 到 main，不用等 QA」（Full Path）→ rc 測試是必要關卡。
- 「我手動建 tag 比較快」→ 會跟 Semantic Release 衝突。
- 「子模組沒改什麼，不用處理」→ dirty submodule ref 會讓別人拉 code 出問題。
- 「檢查過了，後來那個 commit 很小，直接 merge」→ HEAD 不等於「已檢查 SHA」就回 R2。
- 「`gates.md` 寫通過，直接跳到下一關」→ 續做一律重跑檢查指令，不信舊紀錄。
- 「R5 merge 要加 `[skip ci]`」→ 不加；`[skip ci]` 只用於 R7 反合與衝突情境 A。
- 「R7 用 release branch 或本地 main 反合就好」→ 只能用 `origin/main`。
- 「force push 一下就好」→ 先列出確切指令與目標分支，取得使用者明確同意。

## 快速參考

| 動作 | 指令 |
|---|---|
| 最新正式 tag | `git tag --sort=-creatordate \| grep -v "beta\|rc" \| head -5` |
| 遠端有沒有該 tag | `git ls-remote --tags origin vx.y.z` |
| 現有 release branch | `git branch -a \| grep release` |
| submodule 狀態 | `git submodule status` |
| main 目前版本 | `git show origin/main:package.json \| grep '"version"'` |
