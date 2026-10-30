---
name: specify-frontend
description: "依 FRD／SAD／BFS 撰寫前端功能規格書（FFS），或以 --change 產出 CR-FFS；只做前端，後端走 specify-backend。觸發：「前端規格」「寫 FFS」。"
argument-hint: "[--change] {功能描述}"
---

# 建立前端功能規格書

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

從自然語言功能描述建立前端功能規格書（FFS），遵循專案標準範本格式。

## 模式說明

| 模式 | 觸發方式 | 適用情境 | 產出文件 |
|------|---------|---------|---------|
| **標準模式** | `{描述}` | 全新功能 | `{功能名稱}_前端功能規格書.md`（FFS） |
| **調整模式** | `--change {ticket} {描述}` | 原功能新功能調整 | 更新 FFS 主文件 changelog + Linear 票 |

## 輸入參數

```
$ARGUMENTS → [--change] {功能描述}
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `--change` | 否 | 指定調整模式（CR-FFS），省略則為標準模式（FFS） |
| `{功能描述}` | 是 | 自然語言描述，空白則提示輸入後終止 |

**模式偵測**：`$ARGUMENTS` 含 `--change` → 調整模式；否則標準模式。

## 前置規範

依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`（核心原則：不猜測、技術中立、Docs 同步、Graphify 查詢）。

---

## 標準模式執行流程

### 0. Docs 同步檢查

依 `shared-preludes.md` Step 0.5：docs 在獨立 repo 時先 pull 一次，確保文件目錄是最新狀態；docs 在本 repo 則略過。

### 0.4. 載入 FRD §4 畫面設計（必要）

**先讀 `analysis/_context.yml`** 取各文件路徑（依 `shared-preludes.md` Step 0.8）——本 skill 需要 FRD／SAD／BFS 三份，路徑已登記就一次取齊，不逐份 find。未登記才 `find docs/ -name "*需求文件*.md" -path "*{功能名稱}*"`，找到後寫回。三份文件一律定向讀取（先看章節標題再讀需要的段落），不整檔載入。

- **找到 FRD** → 讀取並提取：每個畫面（SCR-XX）的業務目的與操作表、業務層有話要說的欄位（必填理由、計算規則、連動語意、權限差異）作為 FFS §2 業務輸入——**FFS §2 是完整欄位表的唯一 owner**（四類欄位群齊備要求在功能層級把關，格式與來源欄兩階段寫法見 `${CLAUDE_PLUGIN_ROOT}/references/screen-spec-format.md`），完整欄位集合取材自 `ui-survey.md`／原型 HTML／BFS §6 Response／`db-analysis.yml`；§5 欄位規格對應 FFS §4 欄位驗證規則表；操作表對應 FFS §2 操作表（偏離標準 CRUD 動線另對應 §3）；§2.1 US-XX 用於 FFS §6.1／§8 追溯欄（舊 FRD 只有 §1.5 UC 清單時，以其「對應使用者故事」欄換算成 US-XX）。
- **未找到** → `AskUserQuestion` 詢問使用者是否有 FRD；若無則依 BFS 和功能描述推導 UI

### 0.45. 載入 SAD（若存在）

路徑取自 `analysis/_context.yml`；未登記才 `find docs/ -name "*系統分析文件*.md" -path "*{功能名稱}*"`（找到後寫回）。

- **找到 SAD** → 提取：**§2.2 角色與系統互動表**（含 `對應 US` 欄）→ FFS §2 操作表「權限」欄的依據；偏離標準 CRUD 動線者另作為 §3 依據。**§6.4 US→API 對應表** → FFS §6 的 US 追溯來源。
- **未找到** → 先看 `_context.yml` 的 `chain_profile`：**`lite`** → SAD 本來就不存在（分流時刻意跳過），改自 FRD §4 操作表取權限、**BFS §6.1 端點總覽「對應 US」欄**取 US→API；**`standard` 或未登記** → 繼續（僅依 BFS 和 FRD），功能明顯複雜時先向使用者確認是否漏跑 `system-analysis`。

### 0.46. parity 鏈（`chain_origin: foxpro`）

讀 `_context.yml` 的 `chain_origin`（缺欄但功能目錄有 `*_FoxPro分析報告.md` → 補寫 `foxpro` 並告知使用者）。`foxpro` → 本鏈以 FoxPro 版本為主：（四類偏離與三要件定義見 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`）
欄位集、欄序、篩選、驗證與互動（版面套專案既有 UI 規範，即 P-UI）只寫 FRD 已有、可追溯到 `FX-` 編號或 `decisions.md` P-FIX／P-EXT 裁決的項目，**不自行新增**；Web 化技術上必要的差異標 `P-PLATFORM`。
撰寫中發現 FRD 沒寫、FoxPro 也沒有的行為 → 不補規則、不丟延伸問題給使用者，記為「不處理（parity）」；確實非補不可才退回 FRD 走 P-EXT 裁決。不是 `foxpro` → 本節結束。

### 0.5. 載入 BFS（必要）

路徑取自 `analysis/_context.yml`；未登記才 `find docs/ -name "*後端功能規格書*.md" -path "*{功能名稱}*"`（找到後寫回）。

- **找到 BFS** → 定向讀取 §6（端點清單、Request/Response 欄位表）、§7 VR、§2 業務規則，作為前端 API 對接的依據。
- **未找到 BFS** → `AskUserQuestion`：「尚未找到對應的後端規格書，請提供 BFS 路徑，或先執行 `specify-backend` 產出後端規格。」

### 0.7 Graphify 查詢（條件式）
> 參考 `${CLAUDE_PLUGIN_ROOT}/references/graphify-integration.md` — **Query 區塊**（graphify 未安裝時靜默跳過）

### 1. 解析功能描述

提取：**功能名稱**（2-4 個字）、**所屬模組**、**UI 類型**（列表+表單 / 看板 / 報表 / 純表單）。

### 2. 確定儲存位置

**先讀 `analysis/_context.yml`** 取功能目錄；未登記才探索專案慣例，確定後寫回該檔。若無慣例，預設 `docs/{模組名稱}/{功能名稱}/{功能名稱}_前端功能規格書.md`。

### 3. 載入規格範本

讀取 `${CLAUDE_PLUGIN_ROOT}/templates/ffs.md`（骨架，含撰寫須知）；畫面／元件寫法不確定時按需讀 `templates/examples/ffs-ui.md`，圖例寫法讀 `templates/examples/diagrams-and-worked-examples.md`，不預先全載。

### 3.5 同類既有頁面掃描

搜尋同模組是否已有同類畫面（列表／表單／看板）供重用判斷；搜尋策略、FFS §A 產出格式與規則（只列頁面層級、標注延用／擴充／新建、須標勘察日期、不得複製進 Dev 票）見 `references/reuse-scan.md`。

### 3.7 功能代碼綁定（條件式）

功能含**新頁面**或涉及**頁面／選單可見性**時執行，依 `${CLAUDE_PLUGIN_ROOT}/references/program-code-inventory.md`（Step C「FFS」；代碼取自 SAD Step 7.5 或 BFS）。專案無功能代碼／權限盤點機制且搜尋不到 → 靜默跳過。

FFS 須含「功能代碼綁定」段落：route ↔ 代碼對應、綁定方式（**先查既有同類頁面怎麼綁，勿自創**）、既有暫時性權限圈法的移除點、**上線順序（前端綁碼須在後端 seed 之後）**。

### 4. 視覺分析（條件觸發）

依 `${CLAUDE_PLUGIN_ROOT}/references/ui-analysis-guide.md`「前置條件與偵測」：

- **`analysis/ui-survey.md` 已涵蓋且未過期** → 直接讀用作為 §2 欄位表的取材來源，**不重問 URL、不重跑勘察**
- **未涵蓋** → `AskUserQuestion`（`提供系統 URL 做現有畫面分析（推薦）` / `跳過，依 FRD/BFS 推導`）；選提供 → 派 `sa-flow:browser-surveyor` 勘察（派工樣板見 `references/browser-survey-dispatch.md`），它落檔 `analysis/ui-survey.md` 後作為 §2 輸入
- **勘察失敗**（agent 回報連不上）→ 先跑 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py`，照它印的標準寫法改註冊後重啟 session；不阻斷本 skill——標記「未取得畫面證據」續行，§2 改依 FRD/BFS 推導並在該節註明

> **主 session 不開瀏覽器。** DOM snapshot 與截圖對「寫 FFS」毫無用處卻會擠爆 context——你要的是 `ui-survey.md` 裡的欄位表。**不要 Read 截圖進 context**。

### 5. 撰寫 FFS（**派 `spec-writer`，主 session 不寫正文**）

FFS 正文 30KB，長文生成會佔滿主 session 的 context。主 session 只做四件事：
**備齊輸入 → 落決策 → 派工 → 判讀複核**。順序依相依性重排過——
契約回查在決策落檔之前，取捨才能**當場**記進 decisions.md。

#### 5.1 BFS 契約回查（派工前必做，**逐項對照不可抽樣**）

FFS 是規格鏈最後一份，**寫的當下 BFS 就在手上**——此時對照的成本是「多讀一份 §6」；
留到鏈末才發現，成本是回頭改兩到四份文件並重跑驗證。
**這一步必須在派工前**：它會改動 BFS，而 agent 拿到的 BFS 必須already是修正後的版本。

逐項檢查三個方向，**任一不成立即為契約缺口**：

| 方向 | 檢查 | 不成立的處理 |
|------|------|-------------|
| **顯示 → Response** | §2 每個查詢結果／明細欄位，其「來源」欄必須對得上 BFS §6 某個 Response 欄位，或標為 `前端計算：{公式}`（其輸入也必須來自 Response） | 補進 BFS Response，或改為前端計算 |
| **輸入 → Request** | §2 每個新增／編輯表單欄位，必須對得上該端點 BFS Request 的某個欄位 | 補進 BFS Request，或移除該欄位並說明改由哪條路徑設定 |
| **操作 → 端點** | §2 操作表每一列，必須對得上 BFS §6.1 某個端點，或明確標「純前端行為，不呼叫 API」 | 補端點，或標註純前端 |

**特別注意「畫面上的數字」**——筆數、總計、比率這類值不是欄位，最容易兩邊都以為對方負責：
是後端回傳（Response 補欄位）還是前端算（輸入從哪來），**兩者擇一寫明**，不可留白。

#### 5.2 邊界落實對照（派工前必做）

打開 SAD §6.6，依 `${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md`「② 撰寫階段落實對照」把 B1/B2/B3 落成 §4 欄位驗證、B4/B7 落成 §5 狀態控制、B11 落成 §2 欄位群完備。**對照結果寫進 brief**——agent 依此知道每章該承載哪些邊界。

**B13**（參數化來源一致性）：FFS 若複述了 BFS 的長度／格式／閾值，**一律改為 ref BFS 同編號 VR，不重寫字面值**——重寫就是製造第二份會走樣的真相。找不到落點當場補寫；補不出來併入步驟 6 一次問完，不留給 `dev-readiness`。

#### 5.3 決策紀錄落檔（派工前必做）

把本次**已拍板**的決策 append 到 `{功能目錄}/decisions.md`（全鏈唯一決策落點；
`grep -n '^| D-' decisions.md | tail -1` 取最大號接續；規範見
`${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`）。檔案不存在 → 建檔，不視為缺陷。
**不新增分析步驟、不多問任何問題。**

FFS 階段典型的決策來源：Step 3.5「沿用哪一頁的動線」、**5.1 契約回查抓到缺口時
「補進 BFS Request/Response vs 改為前端計算」的取捨**（這一類必記——它同時改動了 BFS）。
`階段` 欄填 `FFS`。**上游已記過的決策不重抄**，引用寫 `見 decisions.md D-0xx`。

> Step 6.5 UI/UX 審查在檔案已寫出**之後**——其 `[必改]` 回填 FFS 的同一次編輯中
> 一併 append 到 decisions.md 並補 `§D` 列，不要因為「已經寫過檔了」就跳過。

#### 5.4 派工

完整派工 prompt → [spec-dispatch.md](references/spec-dispatch.md)。
派工前確認 5.1~5.3 都已完成——agent 拿到的 BFS 必須已是回查修正後的版本。

`extra_checks` 帶兩條 FFS 專屬硬閘（前綴刻意用 `EC-` 避開 `L` 編號，理由與完整驗法見 `spec-dispatch.md`）：

<law>
**EC-1｜§2 四類欄位群齊備、每個顯示欄位「來源」欄不得留空**（填 BFS Response 欄位名或 `前端計算：{公式}`）。
**EC-2｜全文無框線字元、無元件名稱、無像素寬度**。
兩條**不通過不得產出**——畫面內容規格沒有視覺下限，§2 是全鏈唯一完整欄位表、沒有上游可 ref，這閘沒過 Dev 前端票就沒東西可取材。
</law>

#### 5.5 判讀回報與複核

agent 回報後，主 session 處理兩類回報項（自檢結果的抽驗統一在步驟 7）：

1. **待補清單**——未定案的點自己裁決或問使用者，補完回派（`mode: change`）
2. **證據缺口**——需要補勘察的回頭派對應 agent，**不要自己去查**

### 6. 疑問點總清查（寫文件前必做）

| 面向 | 檢查問題 |
|------|---------|
| BFS 對接 | 每個 API 端點的 Request/Response 都已確認？ |
| 畫面 | 每個頁面的操作表都填實了？本功能的四類欄位群齊備？來源欄無空白？ |
| 驗證 | 每個欄位的驗證規則（時機、訊息）都清楚？ |
| 連動 | 所有選擇器連動和即時計算邏輯都已定義？§5.0 每對觸發→影響欄位在 §2 同一「所屬區塊」？ |
| 狀態控制 | 各狀態下的欄位可編輯性和按鈕顯示都確認？ |
| 例外 | API 錯誤回應的前端處理方式都已定義？ |

### 6.5 UI/UX 審查（選配）

專案有既有 UI 規範／設計系統時，對照審查 §2/§3/§5 的使用者情境動線、資訊呈現、狀態涵蓋、與既有規範／同模組畫面的一致性，以及欄位版面（分區依建檔決策順序、連動欄位同區、必填真假）。專案有 UI/UX 審查顧問（agent／skill）則委派之，否則由主 session 自行對照；兩者皆無則跳過：
- `[必改]` → 回填 FFS 對應章節後再繼續
- `[待確認]` → 併入步驟 6 疑問點總清查向使用者確認
- 越界問題（業務領域判斷）→ 轉 `domain-advisor` 或記為待釐清

### 7. 規格自我審查（**只做 agent 做不到的**）

L9/L10/L14/L15/L16 已由 `spec-writer` 的 L1~L5 自檢涵蓋，**不要重跑一遍**——
本步驟聚焦 agent **結構上做不到**的三類：

| # | 檢查 | agent 為何做不到 |
|---|------|---|
| **A** | 與 BFS 的**跨文件一致性**：端點路由、欄位名（camelCase）逐項比對 | 它只定向讀了 BFS 部分章節，沒有兩份文件的全貌 |
| **B** | **L13 契約回查落實**：5.1 三個方向皆已對照，無「畫面上的數字」留白 | 那是主 session 派工前的判斷，agent 只照 brief 寫 |
| **C** | **抽驗 agent 的自檢結論** | 見下方 `<law>` |

<law>
**不要照單全收 agent 的「自檢全過」**（理由與通用盲區見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §四）。
本文件的抽驗重點：`grep -c` 數 §2 欄位列數與 `ui-survey.md` 對照、
隨機抽 2~3 頁看「來源」欄有無空白。
</law>

不一致 → 改 FFS 回派 agent（`mode: change`）；改 BFS 屬契約變更，
要 append `decisions.md` 並在 BFS CHANGELOG 註記。

### 8. 報告完成

報告：規格書路徑、頁面數量、API 對接端點數。

**下一步**：依 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 續行條件判定——滿足 → **自動續跑 `sa-flow:dev-readiness {功能目錄}`**（✅ 後由其續跑 `verifying-specs`）；否則停下說明。**完工回寫提醒**：PR 合併後依實作修訂本 FFS（四類欄位群、欄位命名、操作流程），changelog 註「完工回寫：實作對齊」（見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`）。

---

## 調整模式執行流程

> 適用：原功能的新功能調整，in-place 更新 FFS 主文件並記錄 changelog

### B0. Docs 同步檢查

同標準模式步驟 0。

### B0.5 Ticket 守門

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 0）執行。

### B1. 識別調整內容

提取：功能名稱、所屬模組、異動票號（已由 Step 0 確認）、變更類型（新增畫面/調整欄位/修改流程）。

### B2~B3. 主文件查找與影響分析

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`：**Step 1** 搜尋 FFS 主文件（找不到時掃描頁面元件／路由設定／API 呼叫，用 `${CLAUDE_PLUGIN_ROOT}/templates/ffs.md` 範本撰寫 v1.0，同時定向讀取對應 BFS 主文件取得本次 CR 的 API 異動規格）；**Step 2** 分析影響範圍與確認。

### B4. 更新 FFS 主文件與 Changelog

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 3）執行 in-place 更新（修訂是取代不是追加）。本次 CR 有新增/調整畫面內容規格或操作動線時，更新前先依步驟 6.5 審查異動章節，`[必改]` 回填後再落檔；僅改驗證規則或 API 對接時免審。

### B5. 更新 Linear 票

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 4）更新票 description。

### B6. 報告完成（調整模式）

**下一步**：執行 `sa-flow:dev-readiness {功能目錄}` 就緒度檢核（CR 改動的邊界同樣要獵，✅ 後由其交棒 verifying-specs）；已檢核過才改執行 `sa-flow:verifying-specs --cross {功能目錄}`。**完工回寫提醒**：本次 CR 開發完成後，須依實際實作回頭修訂 FFS（changelog 註記「完工回寫：實作對齊」）。

---

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| `{功能描述}` 為空 | 提示輸入描述，終止 |
| BFS 找不到 | 用 `AskUserQuestion` 詢問路徑；若仍無，建議先執行 `specify-backend`，終止 |
| 範本找不到 | 提示範本路徑錯誤，終止 |
| FFS 主文件找不到（調整模式） | 從 codebase 反推建立 v1.0，再套用 CR 變更 |
| chrome-devtools MCP 不可用 | 跳過視覺分析，依功能描述與 BFS 推導 UI 規格 |
