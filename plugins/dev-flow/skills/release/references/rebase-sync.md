# Rebase 同步與發版前品質閘

> 觸發時機：專案採線性歷史（develop 用 rebase 而非 merge-back 與 main 同步）、發版前要過品質閘、rebase 遇到 release-only commit 衝突。
> 預設流程（SKILL.md Step 5）是 `--no-ff` 反合 `origin/main`；專案明確要求線性歷史時才用本檔做法。

## 發版前品質閘

建 release branch 前先過專案的品質閘（依 package manager，如 bun／pnpm／npm；其他語言用專案自帶的 build／lint／test 指令）：

- type-check（例如 `bun type-check`）
- lint（例如 `bun lint`）

工作區要乾淨：`git status --short`。發版由 CI 驅動，本地觸發時用專案既有的 release script，之後確認 `origin/main` 已更新、CI pipeline 已啟動。

## release metadata 檔

把 `CHANGELOG.md` 與版號檔（如 `package.json`）視為 release metadata。只動這些檔的 commit（例如 `chore(release): ...`）由 CI 產生。

## 線性歷史的 rebase 路徑

main 發版（CI 完成、`origin/main` 出現 `chore(release): x.y.z`）後同步 develop：

1. `git fetch origin`
2. `git checkout develop`
3. `git pull --ff-only origin develop`
4. `git rebase origin/main`
5. 驗證無誤後 `git push origin develop --force-with-lease`

`--force-with-lease` 仍屬 force push：執行前列出確切指令與目標分支，取得使用者明確同意。

## rebase 衝突處理

rebase 中斷時：

- 衝突 commit 是 release-only（只動 `CHANGELOG.md` 與版號檔）：`git rebase --skip`
- 其他：手動解衝突 → `git add <檔>`（逐檔指名）→ `git rebase --continue`

## Semantic Release 預期行為

- `main` 產出 stable release。
- `develop` 為 prerelease（`beta`），不該把 release metadata 衝突留進分支歷史。
- prerelease 執行不該覆蓋屬於 stable main release 歷史的 `CHANGELOG.md`／版號檔內容。

不手動改版本號、不手打 git tag，版本交給 Semantic Release／CI。
