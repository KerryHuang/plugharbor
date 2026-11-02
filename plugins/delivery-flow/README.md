# delivery-flow

專案交付流程——票務工具層與日報週報、會議記錄、訪談準備、issue 分流、QA 實機驗收、操作手冊、HTML 原型。

目前版本提供骨架、共用 references、設定載入與 `report-writer` agent；各流程 skill 陸續加入。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install delivery-flow@plugharbor
```

## 依賴

需要 `browser-docs`（實機驅動、截圖標註、PDF 轉檔）。

- **Claude Code**：`plugin.json` 宣告 `dependencies: ["browser-docs"]`，安裝與更新時自動補裝並啟用。
- **Codex、pi**：沒有依賴機制，需一併安裝 `browser-docs`。`setup/install.sh` 預設安裝全部 plugin，會一起裝好。

## 設定

專案根建立 `.plugharbor/delivery-flow.yml`，鍵說明與範例見 `references/config.md`。缺檔或缺鍵時：

```bash
python3 scripts/config.py get ticket.tool   # 退出碼 2，stderr 一行建檔指引
```

票務工具支援 Linear 與 GitHub Issues；Jira 只有設定對照範例，未實測。

## skills 與 agents

| 類型 | 名稱 | 說明 |
|------|------|------|
| agent | `report-writer` | 吃備妥的資料集、範本與輸出路徑，產一份報表檔；不下查詢、不發布 |
