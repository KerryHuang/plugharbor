---
name: release-workflow
description: 前端正式發版與分支同步工作流——Semantic Release 發版、develop rebase 到 main、處理 CHANGELOG.md / package.json 這類 release-only commit 的衝突。Use when preparing a production release, syncing develop with main, or resolving release/rebase conflicts；觸發：「發版」「release 到 main」「develop rebase main」「release 衝突怎麼解」。
---

# Release Workflow

Vue 3 前端專案的標準發版與分支同步流程（Git Flow + Semantic Release）。

## 使用時機

- 把變更發布到 `main`
- 完成一條 release 分支
- 把 `develop`（或 feature 分支）rebase 到 `origin/main`
- 處理 release-only commit 造成的 rebase 衝突

## 核心規則

- 發版前一律先過品質閘（依專案 package manager，bun / pnpm / npm 擇一）：
  - type-check（例如 `bun type-check`）
  - lint（例如 `bun lint`）
- 把 `CHANGELOG.md` 與 `package.json` 視為 release metadata 檔。
- rebase 時，若某 commit 只動 release metadata 檔（例如 `chore(release): ...`），**skip** 它。
- `develop` 保持線性歷史：rebase 到 `origin/main` 後用 `--force-with-lease` push。

## 標準發版路徑

1. 確認工作區乾淨：`git status --short`
2. 過品質閘：type-check、lint
3. 發版到 main（依專案設定，通常由 Semantic Release / CI 驅動；本地觸發用專案既有的 release script）
4. 確認 `origin/main` 已更新、CI pipeline 已啟動

## 標準 rebase 路徑

發版後同步 `develop` 與 `main`：

1. `git fetch origin`
2. `git checkout develop`
3. `git pull --ff-only origin develop`
4. rebase 到 main：`git rebase origin/main`
5. 驗證無誤後 push：`git push origin develop --force-with-lease`

## 衝突處理

rebase 中斷時：

- 若衝突 commit 是 release-only（只動 `CHANGELOG.md` 與 `package.json`）：
  - `git rebase --skip`
- 否則：
  - 手動解衝突
  - `git add <files>`
  - `git rebase --continue`

## Semantic-Release 預期行為

- `main` 產出 stable release。
- `develop` 為 prerelease（`beta`），不該把 release metadata 衝突留進分支歷史。
- prerelease 執行不該覆蓋屬於 stable main release 歷史的 `CHANGELOG.md` / `package.json` 內容。

> 不手動改版本號、不手打 git tag——版本交給 Semantic Release / CI。
