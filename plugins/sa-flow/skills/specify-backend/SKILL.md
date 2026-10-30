---
name: specify-backend
description: "依 FRD／SAD 撰寫後端功能規格書（BFS），或以 --change 產出 CR-BFS；只做後端，前端走 specify-frontend。觸發：「後端規格」「寫 BFS」。"
argument-hint: "[--change] {功能描述}"
---

# 建立後端功能規格書

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

從自然語言功能描述建立後端功能規格書（BFS），遵循專案標準範本格式。

## 模式說明

| 模式 | 觸發方式 | 適用情境 | 產出文件 |
|------|---------|---------|---------|
| **標準模式** | `{描述}` | 全新功能 | `{功能名稱}_後端功能規格書.md`（BFS） |
| **調整模式** | `--change {ticket} {描述}` | 原功能新功能調整 | 更新 BFS 主文件 changelog + Linear 票 |

## 輸入參數

```
$ARGUMENTS → [--change] {功能描述}
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `--change` | 否 | 指定調整模式（CR-BFS），省略則為標準模式（BFS） |
| `{功能描述}` | 是 | 自然語言描述，空白則提示輸入後終止 |

**模式偵測**：`$ARGUMENTS` 含 `--change` → 調整模式（移除旗標後解析描述）；否則標準模式。

## 前置規範

依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`（核心原則：不猜測、技術中立、Docs 同步、Graphify 查詢）。

---

## 標準模式執行流程

### 0. Docs 同步檢查

依 `shared-preludes.md` Step 0.5：docs 在獨立 repo 時先 pull 一次，確保文件目錄是最新狀態；docs 在本 repo 則略過。

### 0.3. 載入 FRD §4 畫面設計（若存在）

**先讀 `analysis/_context.yml`** 取 FRD 路徑（依 `shared-preludes.md` Step 0.8）；未登記才 `find docs/ -name "*需求文件*.md" -path "*{功能名稱}*"`，找到後寫回。

- **找到 FRD** → 讀 §4（定向讀取，不整檔載入）：業務層欄位規格（必填理由、計算規則、連動語意、權限差異）併入 §5 欄位規格（含算例），作為 Request 欄位業務語意依據——完整欄位集合另由 `db-analysis.yml` 表結構＋SAD §3.2 IF-XX 推導（FRD §4 不含完整欄位群，owner 是 FFS §2）。輸入語意推型別：數值（小數 N 位）→decimal、日期／日期範圍→date、開關→bool、單選固定清單→列舉、單選可搜尋／開窗→外鍵 id。操作表跟 SAD §6.4 US→API 對應表交叉確認，每個「執行後行為」都要有對應端點；「權限」欄是授權設計輸入。
- **未找到** → 從 `db-analysis.yml` 與 DB schema 推導欄位命名

### 0.45. 分流確認（lite 鏈時本 skill 要多做四件事）

讀 `_context.yml` 的 `chain_profile`：`standard`／未登記 → 照常，本節結束。`lite` → 無 SAD，依 `${CLAUDE_PLUGIN_ROOT}/references/chain-profile.md`「lite 跳過 system-analysis」表由本 skill 第一手產出四項（§1.3 資料表/ER、§A.3 重用結論、§6.1「對應 US」欄、**邊界 B1~B10+B13**）；同檔「中途升級」訊號出現（需要交易／跨表寫入／狀態合法轉換）→ **停下告知使用者**補做 `system-analysis`，**不要**把 SAD 內容硬塞進 BFS。

### 0.46. parity 鏈（`chain_origin: foxpro`）

讀 `_context.yml` 的 `chain_origin`（缺欄但功能目錄有 `*_FoxPro分析報告.md` → 補寫 `foxpro` 並告知使用者）。`foxpro` → 本鏈以 FoxPro 版本為主：（四類偏離與三要件定義見 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`）
VR／BR／Request 與 Response 欄位只寫 FRD 已有、可追溯到 `FX-` 編號或 `decisions.md` P-FIX／P-EXT 裁決的項目，**不自行新增**；Web 化技術上必要的差異標 `P-PLATFORM`。
撰寫中發現 FRD 沒寫、FoxPro 也沒有的行為 → 不補規則、不丟延伸問題給使用者，記為「不處理（parity）」；確實非補不可才退回 FRD 走 P-EXT 裁決。不是 `foxpro` → 本節結束。

### 0.5. 載入 SAD（若存在）

**先讀 `analysis/_context.yml`** 取 SAD 路徑；未登記才 `find docs/ -name "*系統分析文件*.md" -path "*{功能名稱}*"`，找到後寫回。

- **找到 SAD** → 定向讀取：推薦技術方案、初步 API 端點建議、涉及資料表清單、重用結論表、Light API 需求清單、Migration 預判、跨模組影響；重點 **§6.4 US→API 對應表**（BFS 端點設計起點，每個 US-XX 展開為具體端點；舊 SAD 的 UC-XX 為 legacy 沿用其對應）與 **§3.2 資訊流 IF-XX**（Request/Response 欄位與轉換邏輯依據）。
- **未找到** → `AskUserQuestion` 是否執行 DB 深度分析：**是** → 若專案有 DB 分析顧問／工具則派工（`tables` 從描述推測），結果寫入 `db-analysis.yml` 並注入步驟 4/4.2/5；無則依步驟 4 自行以唯讀 DB 查詢工具查表結構；**否** → 繼續（步驟 4 只做基本 COLUMNS 查詢）

### 0.7 Graphify 查詢（條件式）
> 參考 `${CLAUDE_PLUGIN_ROOT}/references/graphify-integration.md` — **Query 區塊**（graphify 未安裝時靜默跳過）

### 1. 解析功能描述

提取：**功能名稱**（2-4 個字）、**所屬模組**、**功能類型**（CRUD API / 排程同步 / 混合類型）。

### 2. 確定儲存位置

**先讀 `analysis/_context.yml`** 取功能目錄；未登記才探索專案慣例，確定後寫回該檔。若無慣例，預設 `docs/{模組名稱}/{功能名稱}/{功能名稱}_後端功能規格書.md`。

### 3. 載入規格範本

讀取 `${CLAUDE_PLUGIN_ROOT}/templates/bfs.md`（骨架，含撰寫須知）；範例集（`templates/examples/bfs-flow.md`／`bfs-data-model.md`／`bfs-api.md`／`bfs-validation.md`／`diagrams-and-worked-examples.md`）按需讀取、不預先全載；既有規格文件（FRD／SAD／舊版 BFS）定向讀取（先看章節標題再讀需要的段落），不整檔載入。

### 4. 查詢相關資料

**先讀 `analysis/db-analysis.yml`**（依 `shared-preludes.md` Step 0.8；先讀 `_index:` 再 `grep -n '^  {TABLE}:'` 只讀該表段）——SAD 階段已查過的表結構直接沿用。以下只對該檔未涵蓋的表／欄位執行，查完寫回同一份 yml。

依 `references/canonical-schema.md`：**必須先**切到 canonical 連線（避免從特定環境／客戶連線推斷錯誤），再用唯讀 DB 查詢工具查欄位（`db-analysis.yml` 已有則沿用；工具不可用則請使用者提供 schema 並標注）。BFS §5 欄位定義表加註來源連線與查詢日期；發現 canonical 欄位描述與證據不符（錯誤／過時／空白但語意已確立）→ 不中斷，BFS 以證據語意為準並標注，於完成報告列出。

### 4.1 Light API 存在性確認

撰寫 BFS §6 之前，**必須**確認規格書將引用的參照表 Light API 是否已存在，避免 FFS 引用不存在的端點；不存在則在 BFS §6 新增該端點規格。確認方式與處理表見 `references/light-api-check.md`。

### 4.1.5 現有實作掃描（三子步驟，強制）

**先讀 `analysis/reuse-scan.yml`**（依 `shared-preludes.md` Step 0.8）——SAD Step 3 已盤過的路由與 Handler 對照直接沿用；以下三子步驟只補該檔未涵蓋的部分，補完寫回同一份 yml。

依 `references/reuse-scan.md` 執行（各步驟的 BFS 章節寫法、Lint 規則見該檔）：

- **4.1.5a 路由清單**（一律必做）→ `reuse-scan.yml` 的 `routes:`
- **4.1.5b 既有 mapping 完整對照**（涉及修改既有寫入邏輯時必做）→ `handler_mappings:`
- **4.1.5c 同類寫入路徑掃描**（涉及多入口／一致性／Bug Fix 時必做）→ `write_paths:`；掃出多條**必須** `AskUserQuestion` 跟 PM 確認範圍——那是業務範圍決策，結論留在規格書

BFS **§A.3** 標注每項**能力**（既有可用／需擴充／需新建），**不可留空**；標的是能力不是類別，類別名與路徑留在 `reuse-scan.yml`（細節見該檔末段）。

### 4.1.6 Bug 假設驗證（條件式）

**觸發**：規格描述含「修正 / Bug / fix / 對齊 / 一致性」針對既有功能 → 依 `references/bug-validation.md` 驗證後才寫入 BFS §1.2，範圍須對應到 codebase 具體行號。**禁止**未經 codebase 驗證即寫入 BFS。

### 4.2 Migration 偵測（實作前置）

依步驟 4 的 DB 查詢結果判斷是否需要 Migration（條件與章節格式見 `references/migration-spec.md`）。若專案有「舊系統共用表不可直接加欄」的慣例（如以 1:1 擴充表承載新欄位），依該慣例，不得擅自 ADD COLUMN。

- **不需要** → 繼續步驟 5
- **需要** → 插入「§M. Migration 規格」，步驟 7 報告加註：**Migration 須在開發 API 前執行**。§M.1 資料模型契約是 **SA 定案的契約**（依專案 schema 治理規範與 canonical schema）；§M.3 Migration 實作寫 `decisions.md` TD 由 Dev 定，DB 先行與否由 Dev 提案、PO 拍板，完工回寫時 TD 轉定案並同步 canonical schema。

### 4.25 功能代碼（條件式）

功能含新頁面或涉及頁面權限時執行，依 `${CLAUDE_PLUGIN_ROOT}/references/program-code-inventory.md`（Step C「BFS」；SAD 已有 Step 7.5 產出則沿用）。專案無功能代碼／權限盤點機制且搜尋不到 → 靜默跳過。

BFS 須含「功能代碼」段落：代碼與描述、來源（沿用／新編＋撞碼驗證）、seed 方式（新編須含冪等腳本＋管理員授權）、**授權端影響（不變也要明寫理由——代碼存在不等於端點該改用代碼授權，判斷見該檔 Step C）**。新編代碼 → 同批更新盤點文件。

### 4.3 列表／報表端點慣例探索 + DoR（條件式）

**觸發**：功能含任何端點回傳集合／有篩選排序／提供匯出／含統計。依 `references/list-endpoint-dor.md`（探索既有慣例 → 逐端點解析 DoR → 輸出），**禁 hand-wave**；填入 BFS §6.0，維度 2-5 同步餵 SAD §6.6、分頁/效能餵 SAD §6.5。排序鍵非唯一必補決勝欄（否則分頁跨頁重複／漏筆），見 `${CLAUDE_PLUGIN_ROOT}/references/sort-order-standards.md`。

### 5. 撰寫規格書（**派 `spec-writer`，主 session 不寫正文**）

BFS 正文預算 45KB，是全鏈最大的一份。主 session 只做四件事：**備齊輸入 → 問清疑點 → 落決策 → 派工判讀**（疑問清查與決策落檔都在派工前，agent 拿到的才是已定案的內容）。

#### 5.1 邊界落實對照（派工前必做）

**standard 鏈**：依 `${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md`「② 撰寫階段落實對照」逐條把 SAD §6.6 的邊界結論落成 §7 VR/BR、§2.4 狀態表、§8 例外、§8.4 並發、§6.0 DoR 的具體規格；找不到落點**當場補寫**，補不出來併入 5.2，**不得**留給 `dev-readiness` 收拾。**對照結果寫進 brief**。

**lite 鏈**（無 SAD）：本節改為**第一手盤點**——依同檔 B1~B10＋B13 逐維度盤一次（M1~M4 標不適用），每個維度都要有結論。盤到 B4／B5／B6 有實質內容 → 依 `chain-profile.md`「lite 下 dev-readiness 的限縮」，代表分流判定有誤，停下改走 standard。

兩鏈皆須做的 **B13**（參數化來源一致性）處理方式同樣在 `boundary-dimensions.md` 該列——**不得只寫字面常數**，這是 `verifying-specs` 跨文件比對結構上抓不到的一類。

#### 5.2 疑問點總清查（派工前必做）

逐一檢查面向依 `references/pre-write-checklist.md`。**若仍有任何疑問**：回到步驟 1-4 重新搜尋或詢問使用者，直到全部解決。**多個疑問依「互動詢問規範」逐題問**。

#### 5.3 決策紀錄落檔（派工前必做）

把本次**已拍板**的決策 append 到 `{功能目錄}/decisions.md`（全鏈唯一決策落點；`grep -n '^| D-' decisions.md | tail -1` 取最大號接續；規範見 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`）。檔案不存在 → 建檔，不視為缺陷。

典型決策來源：Step 4.1.5「重用既有端點 vs 新建」、Step 4.2「DB 先行 vs code 先行」、Step 4.25「沿用／新編／不需代碼」、資料契約形狀拍板、5.2 問完產生的新拍板。`階段` 欄填 `BFS`。**上游已記過的決策不重抄**，引用寫 `見 decisions.md D-0xx`。

> **手段層一律記 TD**（見 `decision-record.md`「技術決策留置」），**不在規格正文定案**——這是 plugin `<law>` 技術中立的落地機制。

#### 5.4 派工

完整派工 prompt → [spec-dispatch.md](references/spec-dispatch.md)。`extra_checks` 帶兩條 BFS 專屬硬閘（該檔已含完整 grep 驗法）：

<law>
**TN｜技術中立**（plugin `<law>`）：全文不得指定 framework／library／ORM／元件／設計模式／類別命名，**以及手段層**（快取、鎖、佇列、儲存位置、併發原語、重試與補償、索引策略）；手段層問題寫成 `decisions.md` 的 **TD**，**不得在正文定案**。**LINT｜`spec-lint.md` L1~L8 逐項自檢**。SA 定的是會被外面看見的事：行為、契約、資料語意、權限邊界、上線風險。
</law>

#### 5.5 判讀回報與複核

agent 回報後，主 session 處理兩類回報項（自檢結果的抽驗在步驟 6）：

1. **待補清單**——未定案的點自己裁決或問使用者，補完回派（`mode: change`）
2. **證據缺口**——需要補查 DB／掃 codebase 的回頭派對應 agent，**不要自己去查**

### 6. 規格審查（**只做 agent 做不到的**）

L9/L10/L14/L15/L16 與 `spec-lint.md` L1~L8 已由 agent 自檢涵蓋，**不要重跑**。
本步驟聚焦 agent **結構上做不到**的：

| # | 檢查 | agent 為何做不到 |
|---|------|---|
| **A** | **與 FRD／SAD 的跨文件追溯**：§7 VR/BR 編號對得上 FRD §5.3、§6 端點對得上 SAD US→API 表 | 它只定向讀了上游部分章節，沒有全貌 |
| **B** | **DB 欄位與 `analysis/db-analysis.yml` 一致** | 它讀的是 yml，無法察覺 yml 本身已過期 |
| **C** | **抽驗 agent 的自檢結論**（尤其 TN 技術中立） | 見下方 `<law>` |

<law>
**不要照單全收 agent 的「自檢全過」**（理由與通用盲區見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §四）。
本文件的抽驗重點：TN 自己 grep 一次——手段層的越線常以「建議」「可考慮」的語氣出現，
agent 容易判成非定案而放行。
</law>

**不跑驗證迴圈**：DB 逐欄比對、FRD↔BFS 追溯性、舊系統交叉比對屬 `sa-flow:verifying-specs` 既有 Task，此時 FFS 尚未產出，完整驗證留鏈末（`dev-readiness`獵未寫的→`verifying-specs`驗已寫的）。

### 7. 報告完成

報告：規格書路徑、章節完成狀態、所有疑問已釐清確認。若本次發現 canonical schema 描述疑義 → 一併列出供使用者後續校正。

**下一步**：依 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 續行條件判定——滿足 → **自動續跑 `sa-flow:specify-frontend {功能描述}`**（宣告後直接執行，不另問）；否則停下說明未滿足項。架構師級驗證留待鏈末 `sa-flow:verifying-specs`（FFS 產出後 `--cross` 一次驗完整）。**完工回寫提醒**：PR 合併後依實作修訂本 BFS（端點路由、欄位命名、Migration 細節），changelog 註「完工回寫：實作對齊」（見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`）。

---

## 調整模式執行流程

> 適用：原功能的新功能調整，in-place 更新 BFS 主文件並記錄 changelog

### B0. Docs 同步檢查

同標準模式步驟 0。

### B0.5 Ticket 守門

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 0）執行。

### B1. 識別調整內容

提取：功能名稱（對應哪個既有功能）、所屬模組、異動票號（已由 Step 0 確認）。

### B2~B6. 主文件查找、DB 查詢、影響分析、更新主文件與 Linear 票

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md` Step 1~4 逐步執行：**Step 1** 搜尋 BFS 主文件（找不到時掃描 API Controller／Handler／DB schema，用 `${CLAUDE_PLUGIN_ROOT}/templates/bfs.md` 範本撰寫 v1.0）；同步用唯讀 DB 查詢工具查**本次異動涉及**的資料表欄位結構（描述疑義處理同標準模式步驟 4），並依步驟 4.2 邏輯只針對異動欄位判斷 Migration（需要時插入「§M. Migration 規格（異動）」）；**Step 2** 分析影響範圍與確認；**Step 3** in-place 更新 BFS 主文件與 Changelog（修訂是取代不是追加）；**Step 4** 更新 Linear 票 description。

### B7. 自動驗證（調整模式）

格式完整性驗證 + DB 欄位交叉驗證（只含異動欄位）。詳見 `${CLAUDE_PLUGIN_ROOT}/references/auto-verification-loop.md`。

### B8. 報告完成（調整模式）

依 `references/completion-reports.md` 輸出完成報告。

**下一步**：執行 `sa-flow:specify-frontend --change {ticket} {功能描述}` 更新 FFS 主文件；**完工回寫提醒**：本次 CR 開發完成後，須依實際實作回頭修訂 BFS（changelog 註記「完工回寫：實作對齊」）。

---

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| `{功能描述}` 為空 | 提示輸入描述，終止 |
| 唯讀 DB 查詢工具不可用 | 記錄警告，跳過 §B3 DB 查詢，於規格書中標注「需補充 DB 結構」 |
| 範本找不到 | 提示範本路徑錯誤，終止 |
| BFS 主文件找不到（調整模式） | 從 codebase 反推建立 v1.0，再套用 CR 變更 |
