# R5–R6 細節：merge 到 main、等 CI、衝突與 rollback

## merge 前的 HEAD 防護

R2 品質閘記下的「已檢查 SHA」必須等於要 merge 的 release branch HEAD，否則回 R2 重驗：

```bash
test "$(git rev-parse release/x.y.z)" = "<已檢查 SHA>" || echo "HEAD 已變，回 R2"
# Full Path（release branch 在遠端）另驗遠端沒人推新 commit：
git fetch origin && test "$(git rev-parse origin/release/x.y.z)" = "<已檢查 SHA>" || echo "遠端有新 commit，回 R2"
```

專案用 PR／MR 合 release branch 時，改用平台的原子檢查：

```bash
gh pr merge <n> --merge --match-head-commit <已檢查 SHA>   # GitHub
glab mr merge <n> --sha <已檢查 SHA>                        # GitLab
```

被拒＝檢查後有人推了新 commit：回 R2 對新 HEAD 重跑品質閘，不硬 merge。

## 本地 merge

```bash
git checkout main && git pull origin main
git merge --no-ff release/x.y.z -m "chore: merge release/x.y.z to main"
git push origin main
```

**不加 `[skip ci]`**：這個 merge commit 必須讓 CI 跑 semantic-release 才會建正式 tag。

## 版號檔／CHANGELOG 衝突

通用策略：保留 main 端版號（CI 會覆寫成正確版號），CHANGELOG 去掉衝突標記、兩邊內容都留。

```bash
git checkout --ours package.json                 # 或專案的版號來源檔
sed -i '/^<<<<<<< HEAD$/d; /^=======$/d; /^>>>>>>> release\/x\.y\.z$/d' CHANGELOG.md
git add CHANGELOG.md package.json
git commit --no-edit
```

commit 加不加 `[skip ci]` 看情境：

| 判斷線索 | 情境 A：CI 搶先執行 | 情境 B：main／develop 歷史分叉 |
|---|---|---|
| main 頭部 | 已有 `chore(release): x.y.z` | 只有 `merge release/x.y.z` |
| 衝突 HEAD 版號 | `x.y.z`（正式） | 上次正式版 |
| 衝突 commit 加 `[skip ci]` | 要加（tag 已建） | 不加（CI 必須跑才建 tag） |

## 等 CI（R6）

push 後等 CI 跑完 semantic-release。不能背景輪詢時，請使用者在 CI 跑完後回報，或貼 `git log origin/main -1 --oneline` 確認出現 `chore(release): x.y.z`。等待期間定時回報一行進度。

R6 通過證據：

```bash
git fetch origin --tags
git ls-remote --tags origin vx.y.z          # 有輸出
git log origin/main -1 --oneline            # chore(release): x.y.z
```

## CI 失敗的 rollback

- **push 被拒**（protected branch、hook 失敗）→ 本地還原 `git reset --hard origin/main`（`reset --hard` 先跟使用者確認）。R5 記「未過」。
- **push 成功但 CI 沒產 tag**（semantic-release 沒偵測到觸發 commit）→ 停手告知使用者，選項：
  1. 在 main 追加觸發 commit（如空的 feat）再跑 CI。
  2. 回滾 main：需要 force push，**必須先列出確切指令與目標分支、取得使用者明確同意**。

不主動 `git push --force`；只做本地 reset，遠端回滾由使用者授權。
