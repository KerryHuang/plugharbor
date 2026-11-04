# Hotfix 流程

**Hotfix 預設走 Fast Path，不問 QA**（線上急修，通常不需 rc 測試）。罕見情境需 QA 時才轉 Full。衝突與 CI 完成邏輯同 Release Step 4。

```
main → hotfix/描述 (CI: 正式版 patch tag) → main + develop
```

### Step 1：從 main 建立 hotfix branch

```bash
git checkout main && git pull origin main
git checkout -b hotfix/描述
```

### Step 2：修復並 commit

```bash
git add <files>          # 逐檔指名 add
git commit -m "fix(scope): 修復描述"
git push origin hotfix/描述
```

### Step 3：merge 到 main

```bash
git checkout main
git merge --no-ff hotfix/描述 -m "chore: merge hotfix/描述 to main"
git push origin main
```

CI 自動建立 patch tag（如 `vx.y.z+1`）。

### Step 4：merge 回 develop

```bash
git checkout develop && git pull origin develop
git merge --no-ff hotfix/描述 -m "chore: sync develop after hotfix/描述 [skip ci]"
git push origin develop
```

### Step 5：清理

```bash
git branch -d hotfix/描述
git push origin --delete hotfix/描述
```
