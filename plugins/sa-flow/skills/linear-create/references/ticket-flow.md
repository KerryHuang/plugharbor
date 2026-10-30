# Linear 票建立流程細節（linear-create Step 3.5 / 9-10）

## 既有票盤點與結構校正（Step 3.5）

開新票前先盤點既有票，避免重複開票，並校正結構不對的既有票樹：

1. **找根票**：`$ARGUMENTS` 或對話脈絡含票號 → `get_issue` 讀取該票與既有子票；
   無票號 → `list_issues` 以功能／問題關鍵字搜既有票（跨 team），確認是否已有票樹。
2. **對照應有結構**（Feature / Bug 票樹），盤出三類差異：
   - **缺票**：應有而未開（如問題涉前後端卻只有後端票；PM 直接掛 Dev 缺另一側）→ 列入本次補開。
   - **內容錯位**：既有 **Dev 票**內容與其職責不符——如 PM 開的 Dev 票前後端問題混寫、
     前端票寫的是後端問題 → 依對應 Dev 票範本**重寫該票描述**（前端問題歸前端票、
     後端問題歸後端票），列入本次修正。
   - **結構正確** → 直接續行，只補開缺票與缺漏的 blockedBy（依 SKILL.md Step 8.5）。
3. **修正範圍僅限 Dev 票**：原始 PM 票、QA 票內容**一律不調整**（開票人的原始敘述保留原貌），
   其 assignee / state 也不動。
4. 差異清單（要修正哪些票、要補開哪些票、各 Dev 票修正前後重點對照）於 Step 8 併入草稿一起
   預覽確認，Step 9 一併執行（修正用 `save_issue` 更新描述與 blockedBy、補開走正常建票流程掛回既有根票）。

既有根票存在時，本次建票一律掛既有票樹下（parentId = 既有根票／QA 票），**不另建新根票**。

## 資源連結（links）

若步驟 8 搜尋到文件，且 `{docs_repo_url}` 已設定（非佔位符），則在 `save_issue` 時帶入 `links` 參數，將對應文件掛為 URL 資源連結。

**連結 URL 組合方式**：`{docs_repo_url}/{URL encoded 文件相對路徑}`

文件相對路徑 = docs 目錄下的路徑（如 `訂單模組/訂單查詢/訂單查詢_需求文件.md`），需 URL encode。

### 各票掛連結規則

| 票種 | 掛的文件連結 |
|------|------------|
| PM 票（Feature） | FRD |
| SA 票（Feature） | FRD、SAD |
| QA 票 | FRD |
| Dev 後端票 | BFS |
| Dev 前端票 | FFS |

**範例（`save_issue` 的 `links` 參數）：**

```json
[{"url": "{docs_repo_url}/{encoded_path}", "title": "FRD 需求文件"}]
```

若 `{docs_repo_url}` 未設定，跳過 `links`，僅在票描述中附文件路徑。

> 標題**不帶**票源 flag；flag 放描述最後一行 `_from sa-flow:linear-create@{version}_`（規則見 `create-dispatch.md`「建票規則」節）。

## Feature 流程（PM → SA、QA → Dev）

| 順序 | 標題格式 | 父票 | 說明 |
|------|---------|------|------|
| 1 | `【需求】{標題}` | — | PM 票 |
| 2 | `【規格】{標題}` | PM | SA 票（需求啟動階段同 PM 一起開） |
| 3 | `【測試】{標題}` | PM | QA 票（SA Done 後開） |
| 4 | `【後端】{標題}` | QA | Dev 後端票 |
| 5\* | `【前端】{標題}` | QA | Dev 前端票（blockedBy 見 SKILL.md Step 8.5） |

## Bug 流程（根票 = QA 或 PM，驗收人＝開票人）

**QA 開票（現行流程）**——新建 QA 根票：

| 順序 | 標題格式 | 父票 | 說明 |
|------|---------|------|------|
| 1 | `【Bug】{標題}` | — | QA 根票（驗收） |
| 2 | `【後端】{標題}` | QA | Dev 後端票 |
| 3\* | `【前端】{標題}` | QA | Dev 前端票（若有） |

**PM 開票**——PM 已自行開 Bug 根票（PM team）：Dev 票直接掛 PM 票下，**不強制補開 QA 票**，驗收由 PM（開票人）做：

| 順序 | 標題格式 | 父票 | 說明 |
|------|---------|------|------|
| 1 | （既有 PM Bug 根票，不新建、內容不調整） | — | PM 根票（驗收） |
| 2 | `【後端】{標題}` | PM | Dev 後端票 |
| 3\* | `【前端】{標題}` | PM | Dev 前端票（若有） |

**父子關係**：
- Feature：`PM → (SA, QA)`，`QA → (後端, 前端)`
- Bug：`根票（QA 或 PM）→ (後端, 前端)`

## 「第一個 / 最後一個 Dev 票」抽象

Dev 範圍可能是「後端+前端」「只有後端」「只有前端」。下列規則一律以**第一個 / 最後一個 Dev 票**表述，三種組合通包：

| Dev 範圍 | 第一個 Dev 票 | 最後一個 Dev 票 |
|---------|--------------|---------------|
| 後端 + 前端 | 後端 | 前端 |
| 只有後端 | 後端 | 後端 |
| 只有前端 | 前端 | 前端 |

## blockedBy 規則

規則以 SKILL.md Step 8.5 為準（前端等後端、來源文件的相依、一次建齊的第一個 Dev 票 ← SA；父子與 QA 不掛）。

> 分階段模式（開立 PM、PM+SA、QA+Dev）**不掛 `第一個 Dev 票 ← SA`**——下游票是 SA Done 後才建立，建立+指派時機本身就是 gate，blockedBy 會「一出生即解除」無意義。

## 交接通知慣例

Linear 只有三種**主動推播**：指派通知、解除阻擋(unblock)通知、@mention。子票進度條 2/2 是被動信號，故 rollup 交接處補 @mention 才保險。

| 交接點 | 分階段模式 | 一次建齊模式 |
|--------|-----------|-------------|
| PM→SA | 開 SA 票並指派 = 指派通知 | SA 出 Backlog；可 @SA |
| SA→第一個 Dev 票 | 開該 Dev 票並指派 = 指派通知 | `第一個 Dev 票 blocked by SA` 的 unblock 通知 |
| 後端→前端（若都有） | `前端 blocked by 後端` 的 unblock 通知 | 同左 |
| 最後一個 Dev 票→QA | 子票 2/2 + **@QA** 並將 QA → Testing | 同左 |
| QA→PM | QA 關票 → PM rollup 2/2 + **@PM** 並將 PM → Testing | 同左 |

> 通則：**關閉上游票時，在該票留言 `@下一關負責人`**，留下明確交接時間點。指派/unblock 通知可能被對方通知偏好吃掉，@mention 不會。
> **PM 根票 Bug（無 QA 票）**：「最後一個 Dev 票→QA」「QA→PM」兩跳合併為一跳——最後一個 Dev 票關票時 **@PM（開票人）** 並將 PM 根票 → Testing，由 PM 直接驗收。

## 開票完成報告範本（linear-create Step 10）

```markdown
## 開票完成

### 票層級結構
PRD-123 【需求】{標題}
  ├── SPC-xxx 【規格】{標題}
  └── QAT-456 【測試】{標題}
        ├── DEV-789 【後端】{標題}
        └── DEV-790 【前端】{標題} ← Blocked by DEV-789

### 票資訊
| 票 | 團隊 | Assignee | 狀態 | 優先級 | Points | Labels | blockedBy |
|----|------|----------|------|--------|:---:|--------|-----------|
| PRD-123 | PM | {開票人} | In Refinement | Normal | — | Spec | — |
| DEV-789 | Dev | {backend_assignee} | Backlog | Normal | 5 | Backend | — |
| DEV-790 | Dev | {frontend_assignee} | Backlog | Normal | 3 | Frontend | DEV-789 |
（只列本次建立的票；未建立階段標「— 未建立」；狀態依 §初始狀態決策對照；blockedBy 取 subagent 回報表，與 Step 8.5 相依表不同時標出）

### 已校正票／到期日／Points 註記
（3.5 校正票列票號＋修正摘要；帶 SLA 的票標到期日；Points ≥13 標「建議拆票」，寫入失敗標「estimate 未寫入」）

### 下一步
（依情境三選一：未分析只開 PM/SA → SA Done 後再跑本 skill 建 Dev 樹；未分析一次建齊 → SA Done 後第一個 Dev 票轉 Todo、PM 轉 In Progress；已分析建 Dev 樹 → 可直接開工，前端的 blocker 全部 Done／Canceled 後 Blocked By BE → Todo。交接通知慣例見上方「交接通知慣例」節）
```

## 建票範圍與順序對應（依 Step 4.5 結果）

| 範圍選項（Step 4.5） | 本次建立 | parentId 處理 |
|---------|---------|--------------|
| 只開 PM 票（需求提出） | 順序 1 | 無父票 |
| 開 PM + SA 票（啟動分析） | 順序 1、2 | SA.parentId = PM.id |
| 建 Dev 樹（QA + Dev，分析已完成） | 順序 3、4、5 | QA.parentId 詢問既有 PM 票編號；Dev.parentId = QA.id；並將既有 PM 更新為 `In Progress` |
| 一次建齊 | 1–5 | 完整父子鏈；初始狀態依 §初始狀態決策（**已分析**→ PM `In Progress`、QA `Todo`、後端 `Todo`、前端 `Todo`／`Blocked By BE`（依 8.5），不開 SA；**未分析・含 SA**→ PM `In Refinement`、SA `Todo`、QA/後端/前端 `Backlog`，**第一個 Dev 票掛 `blocked by SA`**；**未分析・不含 SA**→ 全 `Backlog`） |
