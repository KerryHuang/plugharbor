# 審查遠端 PR／MR

審查遠端 MR／PR、驗證變更、通過則 merge。支援 GitLab（`glab`）與 GitHub（`gh`）。

## 參數

| 參數 | 說明 |
|---|---|
| `<ID>` | 直接審查指定 MR／PR（例如 `!15` 或 `15`） |
| `next` | 列出開啟中的 MR／PR 讓使用者選 |
| 空 | 完整流程：列出 → 選擇 → 審查 |

## CLI 對照（依專案 remote 選一套）

| 動作 | GitLab（`glab`） | GitHub（`gh`） |
|---|---|---|
| 列出 | `glab mr list` | `gh pr list` |
| 檢視 | `glab mr view <id>` | `gh pr view <id>` |
| Diff | `glab mr diff <id>` | `gh pr diff <id>` |
| Checkout | `glab mr checkout <id>` | `gh pr checkout <id>` |
| 留言 | `glab mr note <id> -m "…"` | `gh pr comment <id> -b "…"` |
| Merge | `glab mr merge <id>` | `gh pr merge <id>` |

`glab mr list` 預設就列開啟中的，不要加 `--state=opened`（無此 flag）。

## 流程

1. **選 MR／PR**：有給 ID 直接用；沒給就列出開啟中的，用 AskUserQuestion 讓使用者選。選定後先 `view <id>`：已 closed／merged 就停下告知，不審。
2. **讀 description 與 diff**：`view`、`diff`，並 `checkout <id>` 切到該分支。
3. **跑品質閘**：建置、型別檢查、lint、測試，用專案自帶的指令（見 `quality-check`）。
4. **讀變更檔**，對照 description 逐項驗證。
5. **過濾發現**：依 SKILL.md「發現驗證與誤報排除」。
6. **決策**：通過 → `merge <id>`；需修改 → 留言 request changes，結束，等對方修。

專案有技術棧專屬的審查檢查（如前端分層、i18n、composable 模式），一併對照該領域 skill 的附錄（如有裝 `frontend`，可選）。

## 留言規則

- 每個問題只留一則，不在多處重複同一件事。
- 指到程式碼用帶完整 40 碼 head commit SHA 的連結，前後各多帶一行；不用分支名或短 SHA，避免之後的 push 讓行號跑掉。SHA 取法：`gh pr view <id> --json headRefOid`、`glab mr view <id> -F json` 的 `sha`。
  - GitHub：`https://github.com/<owner>/<repo>/blob/<SHA>/<路徑>#L10-L12`
  - GitLab：`https://<host>/<group>/<repo>/-/blob/<SHA>/<路徑>#L10-12`
- 只有「套用後就完全修好、不需其他步驟」的小改動（約 6 行內）才附 suggestion 區塊；其餘只描述問題與修法。

## 決策與收尾

| 結果 | 動作 |
|---|---|
| 通過 | merge `<id>` |
| 需修改 | 留言 request changes → 結束 |

merge 是對共享分支的動作：執行前確認使用者同意 merge。
