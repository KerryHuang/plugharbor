# linear-triage 細節準則

SKILL.md 的判型、Bug 戰場選擇、適狀態決策的判斷依據。

## 1. 判型準則（Feature vs Bug）

依下列訊號綜合判斷，**衝突時以票描述語意為準**。步驟 4 只做內部初判（不詢問使用者）；
無法確定就在步驟 8 報告中如實列兩種可能與各自依據，讓使用者於閘道 A 裁決。

| 訊號 | 偏向 Feature | 偏向 Bug |
|------|-------------|---------|
| 所屬 team | PM／SA team | QA team（內部 Bug 樹根票常為 QA） |
| 標題關鍵字 | 新增、需求、功能、希望、調整為、支援 | 錯誤、無法、跑不出、壞了、異常、重複、漏、不一致、報錯 |
| 描述結構 | 使用者故事 / 目標 / 範圍 | 重現步驟 / 預期 vs 實際 |
| 既有 label | 需求／規格類 | QA／Bug 類 |

> 注意：QA team 的票在本工作流既可能是 **Feature 樹的測試票**，也可能是 **Bug 樹根票**。
> 區分看描述：有「重現步驟 / 預期 vs 實際」→ Bug；有「測試情境 CheckList」且掛在 PM/SA 父票下 → Feature 樹測試票（此情況通常不該由本 skill 分流，提示改用 `sa-flow:linear-reply`）。

### CR（既有功能調整）的歸類

描述為「把既有功能 X 改成 Y」屬 **CR**，在本 skill 視為 **Feature 分支**處理，
但引導起點建議直接從 `sa-flow:requirement --change` 起跑（跳過 explore/brainstorming），
pipeline 走 CR 路徑（見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md` 的「CR 流程」）。

## 2. Bug 戰場選擇準則（AI 自動判斷）

依票線索選戰場與委派對象。可多戰場併用；先讀碼定位，再視需要查 DB 佐證。

| 票線索 | 戰場 | 委派 / 工具 |
|--------|------|------------|
| 「某現役功能行為怪 / 跟預期不符」需先釐清現況 | 現役系統行為 | `sa-flow:scout` agent（蒐集現況證據，本 skill 不落檔，只取結論） |
| 有明確錯誤現象、需逐步縮小範圍 | 除錯推理 | `superpowers:systematic-debugging` |
| 「資料不對 / 算錯 / 某筆異常 / 欄位空」 | 實際資料、schema | 唯讀 DB 查詢工具（若專案有提供；正式資料優先查測試／staging 環境；沒有則請使用者提供查詢結果） |
| 「程式邏輯有誤」可直接定位 | codebase | Grep / Read，或 `Explore` agent 做廣度搜尋 |
| 跨模組 / 不確定在哪 | 多戰場 | 先 `Explore` agent 找線索，再依結果選上述其一深入 |

### 對接模組

依票內容對應子模組／目錄（路徑見根 `CLAUDE.md` 的子模組表），常見：
- 後端 API 行為 → 後端專案目錄
- 外部系統整合／拋轉 → 整合專案目錄
- 前端畫面 / 互動 → 前端專案目錄
- 舊系統邏輯佐證 → 舊系統（如 FoxPro）原始碼目錄，用 `sa-flow:foxpro-analyzer` 解析

### 根因報告必備內容

對齊 `sa-flow:linear-create` 的 Bug Dev 票三段強制欄位，讓開票可直接套用：

1. **根因分析**：為何會產生此錯誤行為（不是現象複述，是機制）。
2. **程式碼問題定位**：`檔案相對路徑:行號` + 函式/方法 + 此處為何造成 Bug。
3. **修改細節（建議方向）**：怎麼改；可附問題片段與修正方向。**僅建議，不實際改碼**。

無法完全定位時，給「最可能位置 + 排查方向」，不可杜撰行號或機制。

## 2.5 勘察前置：規格 + 完工度 + 資料三面查證（CR / Bug 必做）

分析/定位**之前**三面都查，**只查 codebase 會漏掉需求依據與規格衝突**
（呼應「CR 必先勘察實作」「重用分析要查 docs+Linear 非只查 codebase」「核對最新碼與 git log」）。

### A. docs 規格佐證（必查，最易被略過）

1. 搜 `{docs-root}` 既有規格（FRD/SAD/BFS/FFS/FoxPro 分析）。**用功能名稱／模組搜內容**，
   檔名常不含票號（例：`{docs-root}/訂單模組/訂單查詢/` 整套 FRD/SAD/BFS/FFS）。
2. 對照票要的行為 vs 既有規格：
   - **CR 牴觸既有規格** → 這是**改規格的 CR**，需 PM 確認 + 回寫 CR 規格，不是默默改碼。
   - 規格將某欄/行為設為 by-design（NOT NULL、必填、刻意保留）→ 回報務必點出，別當可隨意移除。
3. 也掃 Linear 既有票（同義功能/前序票），避免重複或漏掉規格鏈。

### B. codebase 完工度

4. `git log --oneline -- <模組路徑>`、`git log --grep=<票號/關鍵字>`：是否已有人做過。
5. 讀**現役最新碼**逐項確認實作狀態（已完成 / 未完成）。
6. **對照票述檔案/行號與實際 codebase**：路徑/行號常過時或指錯
   （典型：精簡版功能在另一個模組，票卻指向完整版元件）。以實際碼為準，回票更正。

### C. 資料庫現況（資料相關時）

7. 涉及資料值/欄位語意/分布 → 唯讀 DB 查詢工具（若專案有提供；正式資料優先查測試／staging 環境）。

### 下結論的對齊原則

對齊三面：**規格說該怎樣 vs 現役碼做到哪 vs 資料實況**。
- 部分已完工 → **收斂範圍**為實際剩餘工作，回票標示「已完成 / 剩餘」。
- 發現規格衝突 → 標為**待 PM 確認**，勿逕自宣告「小改 / 無影響」。

> 典型案例：(B) 三項中兩項已由前票完工、票指錯元件路徑；但 (A) 漏查 docs 才是大坑——
> 既有 FFS/BFS 把某欄位設為 by-design（NOT NULL），
> 移除其實是**改規格 CR**，非「純前端小改」。只查 codebase 會把這層風險吞掉。

## 3. 適狀態決策表

讀 `get_issue` 的 `state`、`parent`、既有子票、team，決定本次 triage 動作。

> 前置：步驟 3.5 已將**尚未進入工作狀態**（Backlog / Todo / Triage）的票依票種標記——
> **PM 根票（分析階段）標 `In Refinement`**、其他票標 `In Progress`；
> `In Refinement` / `In Progress` / `Testing` / `Done` / `Canceled` 則保持原狀不自動改。
> 下表情境以**改狀態前**的原始 state 判讀。

| 情境 | 動作 |
|------|------|
| Backlog / Todo，無子票 | 正常分流（步驟 7）；已於步驟 3.5 標記（PM 票→In Refinement、其他→In Progress） |
| In Refinement / In Progress，無子票 | 正常分流；提示此票進行中，分析供補充 |
| 有完整子票樹 | **不重複開票**；提示改用 `sa-flow:linear-reply <id>` 回覆票上問題；徵詢是否仍要分析 |
| **Dev 葉票**（Dev team、無子票，非 PM/SA 根票） | 不開「子」票樹（葉票之下無 Dev 可開）；Bug/CR 需測試 → **建 QA 父票**並把本票設為其子票；否則收斂範圍後回票 |
| Testing | 通常已進測試，提示確認是否真的需要 triage |
| Done / Canceled | 提示已結案；徵詢是否仍要分析（僅回報、不開票） |

### 開票時機與方向

- **Bug 根票**：根因確認 + 同意後，委派 `sa-flow:linear-create` 開 `QA → Dev` 修復子票，
  根因報告三段帶入 Dev 票描述。
- **Feature / CR**：**不在本次 triage 開**。先走完 `requirement → … → verifying-specs`，
  規格通過後才委派 `linear-create` 建 `PM → SA → QA → Dev` 票樹。本 skill 只做起步引導。
- **Dev 葉票需測試**：建 QA 父票（Linear MCP `save_issue`：QA team、QA label〔取自 `sdlc-linear-labels`，未設定則問使用者〕＋沿用本票
  其餘 label、Bug QA 範本、assignee 依慣例、適當 state），再 `save_issue` 設本票
  `parentId` = QA 票。
- **PM 根票狀態收尾**：票樹建立完成且含 Dev 票後，把 PM 根票從 `In Refinement` 改為
  `In Progress`；分析中／規格未產出／未開票則維持 `In Refinement`。

### ⚠️ re-parent 副作用

設 `parentId` 後，Linear team 自動化規則可能改動本票的 `assignee` / `state`
（實測：掛父票後 assignee 被改成後端、state 被自動改為 Todo）。
開票後**核對並回報**，前端票誤指後端等情況需更正。

## 4. 與其他 skill 的界線（不重造輪子）

| 職責 | 負責者 |
|------|--------|
| 讀票 / 回票 | 本 skill 直接用 Linear MCP（`get_issue` / `list_comments` / `save_comment`） |
| Feature 規格產出 | `sa-flow:requirement` → `system-analysis` → `specify-backend/frontend` → `verifying-specs` |
| Bug 現況勘察 | `sa-flow:scout` |
| Bug 除錯推理 | `superpowers:systematic-debugging` |
| 開子票（票樹 + 描述範本） | `sa-flow:linear-create` |
| 票上未回覆問題 | `sa-flow:linear-reply` |

本 skill 只做「判型 + 分流 + 根因分析 + 回票 + 觸發開票」，其餘一律委派。

## 5. 輸出範本（對應 SKILL.md 步驟 12）

```
## linear-triage 處理結果
票：{ticket-id} — {票標題}
判型：{Feature / CR / Bug}
session 標題：[{類型}] {票號} {標題}
完工度：{勘察結果，如「3 項中 2 項已完成，剩 1 項」}
分析結論：{Feature/CR 建議起點 / Bug 根因一句話}
Linear 回票：{已發佈 / 未發佈}
開票：{已建子票樹 / 已建 QA 父票 / 未開 / 待規格完成}
建議下一步：{對應指令}
```
