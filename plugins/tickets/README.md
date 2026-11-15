# tickets

票務：建票、改階段、回覆、日報週報、分流、清單對帳。票務工具可換（Linear／GitHub／Jira），所有動作經 `ticket-ops`。
自 `lifecycle` 3.0.0 拆出（1.0.0），命名空間一律 `tickets:`。

## 定位

`[workflow]` 專案層 plugin，用 `setup/install-project.sh <專案根> tickets` 依專案安裝；可單獨使用，不需要 lifecycle。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
cd <專案> && claude plugin install tickets@plugharbor --scope local
```

## 設定

專案根 `.plugharbor/lifecycle.yml` 的 `ticket:` 區塊，鍵與預設值見 `references/config.md`。重點：

- `ticket.tool`：`linear`、`github`、`jira`。

## 可選依賴

`lifecycle`（triage、ticket-create 建議的下一步 `spec`、`spec-check`、`implement`）、`superpowers`、`browser-docs`、`toolkit` 都是可選，沒裝時照 `references/shared-preludes.md`「可選依賴」降級。

## Skills（5）

| Skill | 用途 |
|-------|------|
| `ticket-create` | 依自然語言描述開票：預設一張票，使用者要拆或已有父票時才建子票 |
| `ticket-ops` | 票務工具層：對 Linear 或 GitHub Issues 做建票（含父子）、改階段、留言、附圖、查詢、blocked-by，依 ticket.tool 設定 |
| `ticket-reply` | 票上有 Dev 或 AI 的未回覆留言需 PM／SA 回應時使用：讀取未答留言、判角色、逐題預覽草稿確認後回票，並更新對應規格再建議跑 spec-check |
| `ticket-report` | 票務進度報表：daily 列今天變壞的事、weekly 上週回顧＋本週計劃（手動） |
| `triage` | 分流：給一張票號，先判有效性再判型，Feature／CR 引導進規格，Bug 找根因，確認後回票並視情況開票；給一批回饋（會議記錄、需求清單）則逐項對照現況分類 |

## Agents（3）

| Agent | 用途 |
|-------|------|
| `report-writer` | 報表撰寫：吃備妥的資料集、範本與輸出路徑，產一份報表檔 |
| `silent-failure-hunter` | 靜默失敗獵手：審查程式路徑中「錯誤被吞掉、資料悄悄流失」的模式，回答「為什麼欄位空了／資料少了但沒有任何錯誤」 |
| `tickets-scout` | 證據蒐集：codebase／DB／文件勘察結果，只列證據不解讀（lifecycle `scout` 的副本，供 triage 派發） |
