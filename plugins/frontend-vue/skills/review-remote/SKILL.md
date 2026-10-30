---
name: review-remote
description: 審查遠端 MR/PR、跑品質閘與前端最佳實踐檢查、通過後 merge 收尾。支援 GitLab（glab）與 GitHub（gh）。Use when reviewing a remote MR/PR and completing the merge；觸發：「審查 MR」「review PR」「幫我看這個 PR」「MR 收尾 merge」。
---

# Review Remote MR/PR

審查遠端 MR/PR、驗證變更、通過則 merge。

**Arguments:** "$ARGUMENTS"

## Arguments

| Argument | 說明 |
|----------|-------------|
| `<ID>` | 直接審查指定 MR/PR（例如 `!15` 或 `15`） |
| `next` | 直接列出開啟中的 MR/PR 讓使用者選 |
| _(空)_ | 完整流程：列出 → 選擇 → 審查 |

## CLI 對照（依專案 remote 選一套）

| 動作 | GitLab（`glab`） | GitHub（`gh`） |
|------|------------------|----------------|
| 列出 | `glab mr list` | `gh pr list` |
| 檢視 | `glab mr view <id>` | `gh pr view <id>` |
| Diff | `glab mr diff <id>` | `gh pr diff <id>` |
| Checkout | `glab mr checkout <id>` | `gh pr checkout <id>` |
| 留言 | `glab mr note <id> -m "…"` | `gh pr comment <id> -b "…"` |
| Merge | `glab mr merge <id>` | `gh pr merge <id>` |

> ⚠️ `glab mr list` 預設就列開啟中的，**不要**加 `--state=opened`（無此 flag）。

## 工作流程

```
1. 選 MR/PR
   - 有給 ID → 直接用
   - 沒給 → 列出開啟中的，用 AskUserQuestion 讓使用者選
2. 讀 description 與 diff
   - view <id> → 讀說明
   - diff <id> → 看變更
   - checkout <id> → 切到該分支
3. 跑品質閘（依專案 package manager）
   - type-check（例如 bun type-check）
   - lint（例如 bun lint）
4. 讀變更檔，對照 description 逐項驗證
5. 決策：
   - 通過 → merge <id>
   - 需修改 → 留言 request changes → 結束
```

## 前端最佳實踐檢查（有動到 Vue 檔時）

對照 `vue-composables` 模式：

| 檢查 | 準則 |
|-------|------|
| 邏輯抽取 | 業務邏輯 >50 行 → 應抽成 composable |
| 單一職責 | 一個 composable 一個關注點 |
| Reactive 參數 | 接 `Ref<T>` 取得反應性 |
| Side effect 隔離 | Loading / Notify / API 收在 composable 內 |
| 型別安全 | 明確 params interface + 回傳型別 |

## 審查 checklist

- [ ] type-check 通過
- [ ] lint 通過
- [ ] 變更符合 MR/PR description
- [ ] 無硬寫字串（i18n）
- [ ] 遵守分層規則（Presentation 不直接 import Infrastructure）
- [ ] 用語意化主題 token（無硬寫顏色）
- [ ] 遵守 composable 模式（如適用）

## 決策與收尾

| 結果 | 動作 |
|--------|------|
| 通過 | merge `<id>` |
| 需修改 | 留言 request changes（附 `file:line`）→ 結束，等對方修 |
