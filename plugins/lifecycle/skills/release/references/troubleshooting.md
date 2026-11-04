# Troubleshooting：版號異常 / tag 污染

> 觸發時機：develop 卡在舊 beta 序列、`git merge-base --is-ancestor` 誤判、tag 指向的 commit 看起來不在本 repo 歷史。

**多 remote 共用 tag 命名的污染**：若 repo 設了多個 remote，而它們都用 `vX.Y.Z` 命名 tag，`git fetch --all --tags` 時後 fetch 的 remote 會覆蓋 local tag，導致 local tag 指向別 repo 的 commit → ancestry 查詢誤判。

```bash
# Step 1：看 local tag 指向的 commit
git rev-parse vx.y.z

# Step 2：看該 commit 的內容（若指向他 repo，即被污染）
git show vx.y.z --stat --no-patch | head -10

# Step 3：比對 origin 上 tag 指向的 SHA
git ls-remote --tags origin vx.y.z

# Step 4：若不一致，刪 local 並從 origin 明確 fetch
git tag -d vx.y.z
git fetch origin "refs/tags/vx.y.z:refs/tags/vx.y.z"

# Step 5：重新驗證
git rev-parse vx.y.z
git merge-base --is-ancestor vx.y.z origin/develop && echo "ancestry OK" || echo "ancestry 仍不對"
```

| 症狀 | 可能根因 | 處理 |
|------|---------|------|
| `git rev-parse v{正式版}` 指向他 repo commit | 別的 remote tag 覆寫 local | Step 4 重 fetch |
| Local tag 正確但 `--is-ancestor` 為 false | 上次 release Step 5 用了 release branch 或沒等 CI | 重做一次正確的 Step 5 |
| Develop 持續產 `{上次正式版}-beta.N+1` 而非 `{下一版}-beta.1` | 正式版 tag 不在 develop ancestry | 同上 |
