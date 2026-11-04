# lifecycle

軟體交付生命週期：需求探索 → 規格 → 票務 → 實作 → 發版 → QA 實機驗收，加上操作手冊與會議記錄。
由 `sa-flow`、`delivery-flow`、`dev-flow` 合併而成（1.0.0），命名空間一律 `lifecycle:`。

## 定位

`[workflow]` 專案層 plugin，用 `setup/install-project.sh <專案根> lifecycle` 依專案安裝。
技術層面（後端、前端、資料庫、桌面）交給職責 plugin；git 與工作區工具在 `workspace`。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
cd <專案> && claude plugin install lifecycle@plugharbor --scope local
```

## 設定

專案根 `.plugharbor/lifecycle.yml`，鍵與預設值見 `references/config.md`。重點：

- `scale`：`lean`（預設，一份規格、一張票）或 `full`（FRD／SAD／BFS／FFS 與四角色票樹）。
- `spec.dir`：規格目錄，預設 `docs/specs`。
- `ticket.tool`：`linear`、`github`、`jira`；所有票務動作經 `ticket-ops`。

舊專案只有 `.plugharbor/delivery-flow.yml` 時，讀設定的 skill 會停下提示改名為 `lifecycle.yml`（鍵不變）。

## 可選依賴

`browser-docs`（畫面勘察、PDF 轉檔）、`toolkit`（herdr pane 派工、retrospective）沒裝時照 `references/shared-preludes.md`「可選依賴」降級。

## Skills（34）

| Skill | 用途 |
|-------|------|
| `consolidate-docs` | Consolidates ticket-suffixed CR spec docs (e.g. `*_ABC-395.md`) back into their  |
| `dev-feedback` | 把規格類 skill 開的票面摩擦追回產生它的那行開票規格，提出刪減清單（只做減法，--apply 才執行） |
| `dev-readiness` | BFS＋FFS 寫完、verifying-specs 之前用：對抗式獵出邊界缺口（空值／極值／狀態／並發／例外），逐項裁決並回寫規格，迴圈到零阻塞 |
| `explore` | 新功能起手、寫 FRD 前快速收斂需求：六維引導問答，產出探索摘要供 requirement 使用 |
| `feature` | 開新功能分支並做領域邊界規劃——分析受影響層級、建議檔案結構、產出實作鷹架 |
| `foxpro-analyzer` | 分析 FoxPro 舊系統（畫面、欄位、驗證規則、CRUD、資料比對），作為遷移依據 |
| `implement` | 適用於從功能規格書自動執行完整實作流程——分支前置檢查、規格品質閘門、分階段委派實作、規格系統性比對、多角色程式碼審查修正迴圈、收尾自動鏈 |
| `interview-prep` | 正式訪談前後準備：把多場會議／訪談素材彙整成已知／未知盤點，或為指定受訪者產出需求訪談大綱；每條標已確認／待確認／推測並附出處 |
| `issue-triage` | 把一批回饋（會議記錄／需求清單）逐項對照現況 codebase 分類成 Bug／Enhancement／Feature，標既有票與規格文件，產出可開票的問題清單 |
| `linear-create` | 依自然語言描述建立 Linear 票樹（Feature：PM→SA→QA→Dev；Bug：QA→Dev），票面只放重點與規格指路 |
| `linear-reply` | Linear 票有 Dev 或 AI 的未回覆留言需 PM／SA 回應時使用：讀取未答留言、自動判 PM／SA 角色、預覽草稿確認後回票，並更新對應規格文件再觸 |
| `linear-triage` | 給一張 Linear 票號決定怎麼走：Feature 引導進 SDLC 管線，Bug 依 codebase／docs／DB 找根因，確認後回票並視狀態委派 li |
| `meeting-minutes` | 記錄客戶／內部／研討會會議：即時記錄或會後整理成結構化會議記錄（結論、摘要、待辦），可選第二意見審閱，依 publish-target 設定存本機或發布到自架  |
| `operation-manual` | 產出交付客戶的操作手冊與教育訓練簡報：實機探索 → 標註截圖 → 撰寫 → 審查 → 出 PDF／PPTX，並把過程中發現的規格落差整理成待開票清單 |
| `plugin-healthcheck` | 對照 Claude Code 官方 plugin 規範，產出本 plugin 的健康報告與重構建議 |
| `prototype-html` | 需求階段要給 PO 或客戶確認畫面時，產出單一檔案、可點切換多畫面的 HTML 原型，可套用使用者給的設計系統，資料用寫實的假資料 |
| `qa-sweep` | 批次撈 Linear 指派給我的待測票，交 lifecycle:qa-verify（UI，FFS §8 先轉中性驗收格式）或後端驗證後依結果寫回狀態、通知父票或 |
| `qa-verify` | Dev 完工後依驗收案例做實機 E2E 驗收——輸入驗收案例檔（markdown 或 YAML，格式見 acceptance-format.md）或票號（從票面 |
| `release` | 適用於準備正式發版、建立 release branch、把 release 合併回 main、處理線上緊急修復（hotfix）、或將 release/hotfi |
| `requirement` | 依功能描述撰寫功能需求文件（FRD），或以 --change 產出 CR-FRD；資深 PM 視角 |
| `sample-verify` | 對照實際 codebase 行為驗證規格的正確性與完整性：分組平行取樣原始碼、識別業務邏輯區塊、檢查行為規格的覆蓋度，彙整成落差報告 |
| `spec` | 建立與管理功能規格文件——提供規格書模板、狀態追蹤、技術設計指南 |
| `spec-chain` | 跨 session 協調多棒 SA 規格鏈：每棒決定就地做、派 subagent 或開 herdr worker，並獨立驗收產出 |
| `spec-docs` | 讀、搜、改規格文件（FRD／SAD／BFS／FFS、CR、決策記錄）的共用做法 |
| `specify-backend` | 依 FRD／SAD 撰寫後端功能規格書（BFS），或以 --change 產出 CR-BFS；只做後端，前端走 specify-frontend |
| `specify-frontend` | 依 FRD／SAD／BFS 撰寫前端功能規格書（FFS），或以 --change 產出 CR-FFS；只做前端，後端走 specify-backend |
| `survey-existing-system` | 勘察現役（in-production）系統某段行為的現況，產出系統分析師（SA）現況分析文件 |
| `system-analysis` | 把 FRD 轉成系統分析文件（SAD）：工作流、資訊流、資料流三流分析、重用盤點與邊界清單 |
| `ticket-daily-report` | 產出每日票務進度報表：走看板找卡點、只列今天變壞的事、每天一件要決策的事，票號另出明細文件 |
| `ticket-ops` | 票務工具層：對 Linear 或 GitHub Issues 做建票（含父子）、改階段、留言、附圖、查詢、blocked-by，依 ticket.tool 設定 |
| `ticket-weekly-report` | 產出每週票務進度報表供週會使用：上週回顧＋本週計劃，三份產出（會議簡報 HTML 含可點數字抽屜、週報 Markdown、票務明細 Markdown） |
| `verifying-specs` | 實作前驗證 FRD／SAD／BFS／FFS：架構可行性、資料流正確性、DB 結構實查、跨文件追溯；--cross 做跨文件一致性 |
| `work-on` | 端到端功能開發編排——規劃、實作、測試、提交一條龍 |
| `write-doc` | 詢問路徑與內容後，把一份文件寫入磁碟 |

## Agents（17）

| Agent | 用途 |
|-------|------|
| `architect` | 架構顧問（不綁技術棧） |
| `debugger` | 錯誤診斷與品質分析專家（不綁技術棧） |
| `developer` | 功能開發專家（不綁技術棧） |
| `domain-advisor` | 通用 Domain 知識顧問，協助 SA/PM 在需求分析與系統分析階段確保業務 Domain 正確性 |
| `manual-explorer` | 操作手冊探索：用瀏覽器逐畫面記錄可操作元素／預設值／驗證訊息到 inventory.yml 並截乾淨圖；第二模式回頭加紅框重拍 |
| `manual-reviewer` | 操作手冊交付前七項審查（圖文比、內部資訊、個資遮罩、圖片完整、與 inventory 一致、模式純度、整批一致），並整理規格落差 |
| `manual-writer` | 操作手冊撰寫：讀 inventory.yml 與截圖清單，依範本產手冊 markdown 與 Marp 簡報，列出需加紅框的截圖 |
| `qa-fixture` | QA 前置資料：判定目標環境可寫性（讀設定 qa.environments；有唯讀 DB 查詢工具時輔以 DB 查證含個資），逐條解析 plan.yml 前置條 |
| `qa-planner` | QA 驗收計畫：讀驗收案例檔（或票面的重現步驟），開畫面對出案例欄位↔實機表頭，把案例轉成可執行步驟與預期觀察，產 plan.yml |
| `qa-runner-ui` | QA 實機執行：照 steps-only 計畫逐條操作，結構化記錄觀察並回寫成功步驟為快取；可依環境送出資料，唯讀環境只到送出前 |
| `report-writer` | 報表撰寫：吃備妥的資料集、範本與輸出路徑，產一份報表檔 |
| `reviewer` | 程式碼審查專家（不綁技術棧，後端與前端皆適用） |
| `scout` | 證據蒐集：codebase／DB／文件勘察結果，供 domain-advisor 與規格撰寫共用 |
| `silent-failure-hunter` | 靜默失敗獵手：審查程式路徑中「錯誤被吞掉、資料悄悄流失」的模式，回答「為什麼欄位空了／資料少了但沒有任何錯誤」 |
| `spec-sampler` | 規格覆蓋度取樣 agent |
| `spec-writer` | 規格文件撰寫：吃範本、證據檔與已拍板決策，產完整 FRD／SAD／BFS／FFS 寫入指定路徑 |
| `tester` | 測試工程專家（不綁技術棧，後端與前端皆適用） |
