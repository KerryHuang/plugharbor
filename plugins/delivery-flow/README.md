# delivery-flow

專案交付流程——票務工具層與日報週報、會議記錄、訪談準備、issue 分流、QA 實機驗收、操作手冊、HTML 原型。

目前版本提供骨架、共用 references、設定載入、`report-writer` agent，以及票務工具層、日報週報、會議記錄、訪談準備、issue 分流、QA 實機驗收、操作手冊、HTML 原型九個 skill；其餘流程 skill 陸續加入。

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
| skill | `ticket-ops` | 票務工具層：Linear、GitHub Issues 的建票、改階段、留言、附圖、查詢、blocked-by；Jira 僅設定範例 |
| skill | `ticket-daily-report` | 每日票務進度報表：走看板找卡點、只列今天變壞的事；資料經 `ticket-ops` 的 `query`，成品存 `.tmp/` 或 `--out-dir` |
| skill | `ticket-weekly-report` | 每週票務進度報表：週會簡報 HTML（數字可點開明細）、週報、票務明細三份，發布前複驗數字與清單一致 |
| skill | `meeting-minutes` | 即時記錄或會後整理會議記錄；依 `publish-target` 存本機或發布到自架 HedgeDoc |
| skill | `interview-prep` | 多場素材彙整成已知／未知盤點，或產出訪談大綱；每條標已確認／待確認／可能推測並附出處 |
| skill | `qa-verify` | 依驗收案例檔（markdown 或 YAML，格式見 `skills/qa-verify/references/acceptance-format.md`）或票號，對實機逐條驗收，機械判定並產 `qa-report.md`；環境與可寫性讀設定 `qa.environments` |
| skill | `operation-manual` | 操作手冊與教育訓練簡報：實機探索、標註截圖、撰寫、審查，產 PDF／PPTX／Word；規格落差依類型分流。封面品牌讀 `--brand` 或設定 `manual-brand`，都沒有就不印；第一次使用先跑 `scripts/ensure-tools.sh` |
| skill | `prototype-html` | 需求描述產出單檔、可點切換多畫面的 HTML 原型；可套用使用者的設計系統（URL 或檔案），沒給就用無品牌的 `neutral-style.css`；資料用寫實組合加假識別值；需求有歧義時先用具體例子問 |
| skill | `issue-triage` | 回饋逐項對照現況 codebase，分類 Bug／Enhancement／Feature 並標既有票，產出可開票的問題清單 |
| agent | `manual-explorer` | 用瀏覽器逐畫面記錄可操作元素與預設值到 inventory 並截乾淨圖；第二模式叫用 `browser-docs:annotate-screenshot` 加紅框；不寫手冊 |
| agent | `manual-writer` | 讀 inventory 與截圖清單，依範本產手冊 markdown 與 Marp 簡報；不開瀏覽器 |
| agent | `manual-reviewer` | 操作手冊交付前七項審查（圖文比、內部資訊、個資、圖片完整、與 inventory 一致、模式純度、整批一致）；唯讀 |
| agent | `qa-planner` | 讀驗收案例或票面，開畫面對欄位，產可執行的 plan；不執行、不判定 |
| agent | `qa-fixture` | 判定環境可寫性（讀 `qa.environments`）、備妥前置資料、查核資料斷言；不跑案例 |
| agent | `qa-runner-ui` | 照 steps-only 計畫逐條操作並結構化記錄觀察；只觀察不判定 |
| agent | `report-writer` | 吃備妥的資料集、範本與輸出路徑，產一份報表檔；不下查詢、不發布 |
