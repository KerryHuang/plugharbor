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

## Skills（22）

| Skill | 用途 |
|-------|------|
| `consolidate-docs` | 把帶票號後綴的 CR 規格文件併回主規格（手動） |
| `demo-video` | 把旁白加操作步驟的腳本錄成有配音、字幕的操作示範影片（MP4＋SRT）：寫稿 → 審稿 → 配音 → 依語音長度錄操作 → 字幕 → 合成 → 驗證，最後由使用者試聽；預設語音 Edge TTS 非正式授權，對外發布前要先確認 |
| `dev-feedback` | 把規格類 skill 開的票面摩擦追回產生它的那行開票規格，提出刪減清單並寫成報告檔（只做減法，不改 plugin）（手動） |
| `explore` | 新功能起手、寫規格前快速收斂需求：六維引導問答，產出探索摘要供 lifecycle:spec 使用 |
| `implement` | 照規格把功能從開分支做到交付 |
| `interview-prep` | 正式訪談前後準備：把多場會議／訪談素材彙整成已知／未知盤點，或為指定受訪者產出需求訪談大綱；每條標已確認／待確認／推測並附出處（手動） |
| `meeting-minutes` | 記錄會議：即時記錄、會後整理，或錄音（錄音檔／麥克風／線上會議，需 toolkit）轉逐字稿後整理成結構化會議記錄（摘要、結論、待辦），可選第二意見審閱 |
| `operation-manual` | 產出交付客戶的操作手冊與教育訓練簡報：實機探索 → 標註截圖 → 撰寫 → 審查 → 出 PDF／PPTX，並把過程中發現的規格落差整理成待開票清單（手動） |
| `plugin-healthcheck` | 檢查 Claude Code 官方 Plugin 規範最新變化，對比本 plugin 結構，產出健康報告與重構建議（手動） |
| `prototype-html` | 需求階段要給 PO 或客戶確認畫面時，產出單一檔案、可點切換多畫面的 HTML 原型，可套用使用者給的設計系統，資料用寫實的假資料 |
| `qa-verify` | Dev 完工後依驗收案例做實機 E2E 驗收 |
| `release` | 分關卡發版：release branch、品質閘、merge 回 main、反合 develop；含線上急修（hotfix） |
| `spec` | 寫功能規格：lean 產一份 `<spec.dir>/<feature>.md`；full 分棒產 FRD→SAD→BFS→FFS；`--change` 走 CR |
| `spec-chain` | 跨 session 協調 full 規模規格鏈（spec 各棒 → spec-check → ticket-create）：每棒決定就地做、派 subagent（手動） |
| `spec-check` | 實作前檢查規格：verify（預設）、`--readiness` 獵邊界缺口、`--sample` 覆蓋度取樣 |
| `survey-existing-system` | 勘察現役（in-production）系統某段行為的現況，產出系統分析師（SA）現況分析文件 |
| `ticket-create` | 依自然語言描述開票：精簡模式（scale: lean，預設）開一張票；scale: full 開父票＋PM／SA／QA／Dev 四張子票 |
| `ticket-ops` | 票務工具層：對 Linear 或 GitHub Issues 做建票（含父子）、改階段、留言、附圖、查詢、blocked-by，依 ticket.tool 設定 |
| `ticket-reply` | 票上有 Dev 或 AI 的未回覆留言需 PM／SA 回應時使用：讀取未答留言、判角色、逐題預覽草稿確認後回票，並更新對應規格再建議跑 spec-check |
| `ticket-report` | 票務進度報表：daily 列今天變壞的事、weekly 上週回顧＋本週計劃（手動） |
| `triage` | 分流：給一張票號，先判有效性再判型，Feature／CR 引導進規格，Bug 找根因，確認後回票並視情況開票；給一批回饋（會議記錄、需求清單）則逐項對照現況分類 |
| `write-doc` | 詢問路徑與內容後，把一份文件寫入磁碟（手動） |

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
| `qa-fixture` | QA 前置資料：判定環境可寫性，逐條解析前置條件並備妥資料；另可查核資料斷言 |
| `qa-planner` | QA 驗收計畫：讀驗收案例檔（或票面的重現步驟），開畫面對出案例欄位↔實機表頭，把案例轉成可執行步驟與預期觀察，產 plan.yml |
| `qa-runner-ui` | QA 實機執行：照 steps-only 計畫逐條操作，結構化記錄觀察並回寫成功步驟為快取；可依環境送出資料，唯讀環境只到送出前 |
| `report-writer` | 報表撰寫：吃備妥的資料集、範本與輸出路徑，產一份報表檔 |
| `reviewer` | 程式碼審查專家（不綁技術棧，後端與前端皆適用） |
| `scout` | 證據蒐集：codebase／DB／文件勘察結果，供 domain-advisor 與規格撰寫共用 |
| `silent-failure-hunter` | 靜默失敗獵手：審查程式路徑中「錯誤被吞掉、資料悄悄流失」的模式，回答「為什麼欄位空了／資料少了但沒有任何錯誤」 |
| `spec-sampler` | 規格覆蓋度取樣 agent |
| `spec-writer` | 規格文件撰寫：吃範本、證據檔與已拍板決策，產完整 FRD／SAD／BFS／FFS 寫入指定路徑 |
| `tester` | 測試工程專家（不綁技術棧，後端與前端皆適用） |
