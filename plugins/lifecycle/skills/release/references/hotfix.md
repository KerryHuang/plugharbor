# Hotfix 流程

**Hotfix 預設走 Fast Path，不問 QA**（線上急修，通常不需 rc 測試）。罕見情境需 QA 時才轉 Full。衝突、等 CI、rollback 同 `merge-to-main.md`。

同樣分關卡記在 `.tmp/release/hotfix-<ascii-slug>/gates.md`（slug 只用小寫 ASCII 與 `-`）：H1 建分支、H2 修復＋品質閘（記「已檢查 SHA」）、H3 merge 到 main＋CI 建 patch tag、H4 合回 develop、H5 清理。續做時依序重跑各關檢查，從第一個沒過的接續。
無 remote／無 CI 時同主流程 R0 的本機模式：H3 改手動建 annotated patch tag，push 與等 CI 記「本機模式跳過」。

```
main → hotfix/描述 (CI: 正式版 patch tag) → main + develop
```

### H1：從 main 建立 hotfix branch

```bash
git checkout main && git pull origin main
git checkout -b hotfix/描述
```

### H2：修復、品質閘並 commit

```bash
git add <files>          # 逐檔指名 add
git commit -m "fix(scope): 修復描述"
git push origin hotfix/描述
```

跑品質閘（同 SKILL.md 的 R2），全綠後記 `git rev-parse HEAD` 為「已檢查 SHA」。

### H3：merge 到 main

merge 前驗 `git rev-parse origin/hotfix/描述` 等於「已檢查 SHA」（用 PR 合時改帶 `gh pr merge --match-head-commit <SHA>`）；不符回 H2。

```bash
git checkout main
git merge --no-ff hotfix/描述 -m "chore: merge hotfix/描述 to main"
git push origin main
```

CI 自動建立 patch tag（如 `vx.y.z+1`）；`git ls-remote --tags origin <tag>` 有輸出才算 H3 過。

### H4：merge 回 develop

```bash
git checkout develop && git pull origin develop
git merge --no-ff hotfix/描述 -m "chore: sync develop after hotfix/描述 [skip ci]"
git push origin develop
```

### H5：清理

```bash
git branch -d hotfix/描述
git push origin --delete hotfix/描述
```
