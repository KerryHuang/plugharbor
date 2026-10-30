# 子模組處理

子模組有改動時，**必須先 commit 並 push 子模組、再 bump 主 repo pointer**：

```bash
# Step 1：commit 並 push 子模組（逐檔指名，勿 git add -A）
git -C <submodule-path> add <檔1> <檔2>
git -C <submodule-path> commit -m "fix(scope): 修復描述"
git -C <submodule-path> push origin <branch>     # 單獨一步，讀 exit code；失敗就停

# Step 2：回主 repo，更新 submodule ref
git add <submodule-path>
git commit -m "chore: 更新 <submodule> submodule ref"
```

`M` 的方向判讀（何時該 bump、何時該 pull）、push 失敗不得接 bump、rebase 後驗 pointer，見 `submodule-relay` skill。
