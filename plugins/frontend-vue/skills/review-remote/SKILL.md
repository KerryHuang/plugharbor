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
   - 選定後先看狀態（`view <id>`）：已 closed／merged → 停下告知，不審
2. 讀 description 與 diff
   - view <id> → 讀說明
   - diff <id> → 看變更
   - checkout <id> → 切到該分支
3. 跑品質閘（依專案 package manager）
   - type-check（例如 bun type-check）
   - lint（例如 bun lint）
4. 讀變更檔，對照 description 逐項驗證
5. 過濾發現（見下節「誤報排除與驗證」）
6. 決策：
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

## 誤報排除與驗證

要求修改的每一條發現，先過這一關：

1. **排除**：這次 diff 沒碰到的既有問題；type-check／lint 會抓的（第 3 步已跑過）；
   已用 ignore 註解靜音的；不影響正確性、也不違反上面 checklist 的風格偏好。
2. **驗證**：剩下的每條派一個獨立唯讀 subagent（`model: sonnet`），只給發現與 `file:line`，
   回答「成立／不成立＋一句依據」；不成立就丟。同一則訊息平行派出。
3. 全部被剔除 → 視為通過。

## 決策與收尾

| 結果 | 動作 |
|--------|------|
| 通過 | merge `<id>` |
| 需修改 | 留言 request changes → 結束，等對方修 |

**留言規則**：

- 每個問題只留一則，不在多處重複同一件事。
- 指到程式碼用帶完整 40 碼 head commit SHA 的連結，前後各多帶一行；不用分支名或短 SHA，避免之後的 push 讓行號跑掉。
  SHA 取法：`gh pr view <id> --json headRefOid`／`glab mr view <id> -F json` 的 `sha`。
  - GitHub：`https://github.com/<owner>/<repo>/blob/<SHA>/<路徑>#L10-L12`
  - GitLab：`https://<host>/<group>/<repo>/-/blob/<SHA>/<路徑>#L10-12`
- 只有「套用後就完全修好、不需其他步驟」的小改動（約 6 行內）才附 suggestion 區塊；其餘只描述問題與修法。
