# BFS 規格 Lint 規則

> 此檔案集中規範 specify-backend SKILL Step 7「驗證規格品質與自我審查」掃描規則。撰寫完成後必須逐項檢查並修正。

## L1：禁止「沿用既有 DTO」籠統描述（P4）

### 觸發掃描關鍵字

在 BFS 內容中搜尋：
- `沿用既有` `既有結構` `以實際 DTO 為準` `既有 DTO 不變`
- `Request：既有` `Response：既有`

### Lint 規則

任一上述關鍵字出現於 §6 API 規格，**必須**附上：

1. **既有 DTO 完整欄位清單**（從 codebase 實查 grep）
2. **或** 明確標註「不在本次修改範圍 — 參照路徑 `src/.../XxxDto`」並附上**主要欄位摘要**（至少 5 個關鍵欄位）

### 範例

❌ 違反：
```markdown
**Request：** `CopyTemplateItemsRequest`（既有，本次不變）— 欄位以實際 DTO 為準
```

✅ 合規：
```markdown
**Request：** `CopyTemplateItemsToOrderCommand`（既有，本次不變）

| 屬性 | 型態 | 必填 | 說明 |
|---|---|---|---|
| `SalesOrderId` | string | O | 訂單 ID |
| `TemplateItemIds` | string[] | O | 欲複製的範本品項 ID 清單 |
| `WarehouseId` | string? | X | 倉庫 ID（可選） |
| `CopyAttachments` | bool | X | 預設 true，是否同時複製附件 |
```

### Lint 等級
- 違反 = **CRITICAL**（RD 無法開發）

---

## L2：API 端點命名風格 lint（P6）

### 觸發條件
BFS §6 新增 API 端點時。

### 檢查邏輯

1. 從 Step 4.1.5a 的「既有路由清單」歸納該 Controller 命名風格：
   - **PascalCase Action 風格**：`/Light`、`/Paged`、`/{id}/PaymentTerms`
   - **kebab-case sub-resource 風格**：`/items/copy-from-template`、`/items/parent-item-nos`
   - **混合**：Controller 內既有 Action 用 PascalCase，sub-resource 用 kebab-case
2. 新增端點**必須**沿用同 Controller 既有風格

### Lint 規則

| 情境 | 處理 |
|---|---|
| 新端點是同層 Action（如 `/ByCategories`） | 沿用既有 PascalCase Action 風格 |
| 新端點是子資源（如 `/{id}/items/{action}`） | 沿用既有 kebab-case sub-resource 風格 |
| 新端點為「同層 Action」但寫成 kebab-case（或反之） | **WARNING**：列出建議改名 |

### Lint 等級
- 違反 = **WARNING**（不阻擋但需 RD 確認）

---

## L3：「TBD / 待確認 / 需釐清」清零（既有規則延用）

### 觸發掃描
- 關鍵字：`TBD`、`待確認`、`需釐清`、`[需要澄清]`、`?` 結尾的句子

### Lint 規則
任一關鍵字出現於規格內容（不含 §15 待澄清事項表）= **CRITICAL**。

---

## L4：章節矛盾掃描

### 檢查項目
- **API 端點 ↔ 驗證規則**：每個 API Request 欄位是否在 §7 有對應 VR
- **驗證規則 ↔ 資料模型**：VR 引用的欄位是否在 §5 有定義
- **資料模型 ↔ §A 既有實作快照**：§5 表結構是否與 §A 路由所屬 Controller 寫入的表一致

### Lint 等級
- 違反 = **CRITICAL**

---

## L5：「模糊條件」改寫

### 觸發掃描關鍵字
- `可能`、`也許`、`視情況`、`依需要`、`必要時`、`理論上`

### Lint 規則
必須改為明確條件（如「當 X = Y 時，執行 Z」）。

### Lint 等級
- 違反 = **WARNING**

---

## L6：路由不存在 lint（與 reuse-scan.yml 連動）

### 檢查邏輯
BFS §6.1 端點總覽中任何「既有不變動」路由，**必須**在 `analysis/reuse-scan.yml` 的 `routes:`
找到匹配（完整路由字串），且 BFS §A.1 有對應的現況結論列。

### Lint 等級
- 違反 = **CRITICAL**（RD 會找不到端點）

---

## L7：列表／報表端點開發就緒度（DoR）

> 依 `list-endpoint-dor.md`。**通用規則，不綁特定專案的值。**

### 觸發條件
BFS 含任何回傳集合 / 有篩選排序 / 提供匯出 / 含統計的端點。

### 檢查邏輯

1. 該類端點**必須**有 §6.0 列表/報表端點規格基準表。
2. 表中每個「本端點適用 = 是」的維度，**處理方式欄不可留空**，且必須是下列其一：
   - `依循慣例：{codebase 路徑}`（引用既有慣例，附證據）
   - `自定義：{明確值}`（欄位 / 邊界 / 公式 / 取值規則）
3. **禁 hand-wave 關鍵字**（出現在 DoR 維度的處理方式即違反）：
   `比照既有`、`反查回填`、`對齊報表`、`依需要分頁`、`視資料量`、`同既有 Handler`（未附欄位/路徑）。
   **第三種合規寫法（手段留置）**：`約束：{…}｜來源：{codebase 路徑或表.欄位}｜TD-{n}`——約束與來源必填，手段由 Dev 定，不算 hand-wave。
4. 維度特例（後端常無護欄，spec 必須自列）：
   - 排序：必須有「可排序欄位白名單」或明確 `SortBy → ORDER BY` 對應（避免注入 + RD 臆測）。
   - 1:N 取值 / 聚合母體：不可只寫「回填 / 統計」，須寫取哪筆 / 母體單位。

### Lint 等級
- 適用端點缺 §6.0 表 = **CRITICAL**
- 任一適用維度留空或 hand-wave = **CRITICAL**（RD 會卡住或各自臆測，數字對不上被 QA 退）

---

## L1 補充：hand-wave 結案一律比照 L1/L7

L1（沿用既有 DTO）、L5（模糊條件）、L7（DoR hand-wave）共用同一精神：**任何把解析責任丟給開發者的句子都不可結案**。權限/過濾欄位寫「比照既有 Handler」而未附 `來源表.欄位 + 格式 + legacy 資料歸屬` = **CRITICAL**。反過來，**規格替 Dev 選了手段**（指定鎖／快取／佇列／儲存實作）也不合規——改寫成 TD 留置（`decision-record.md`），只留約束、現況、陷阱。

---

## L8：API 回應契約完整性（各 Method 成功狀態碼）

### 觸發條件
BFS §6 任一端點。

### 檢查邏輯

1. §6 每個端點**必須明寫成功 HTTP 狀態碼**（不可只靠 §3 sequence 圖隱含）：
   - GET → 200；POST → **201**；PUT → 200；DELETE → 204；BATCH → **207**
2. **POST** 端點必須標明 `Location` header 指向新建資源。
3. **批量端點**（路由含 `/Batch` 或描述含「批量 / 一次多筆」）必須二擇一明確定義部分成功行為，**不可留白**：
   - 逐項獨立 → 回 `207` + `BatchResultResponse`（逐項 success/error）
   - 整批交易 → 回 `200`/`400`/`409` + rollback 範圍說明
4. **PATCH**：除非 BFS 明確提出部分更新需求並經確認，否則不應出現 PATCH 端點（部分更新一律走 PUT）。

### Lint 等級
- 端點缺成功狀態碼 = **CRITICAL**（前端 / RD 無法確定回應契約）
- POST 缺 `Location` header = **WARNING**
- 批量端點未定義部分成功行為 = **CRITICAL**
- 未經確認出現 PATCH 端點 = **WARNING**

---

---

## L9／L10：SPEC-INDEX 與正文預算（由 SKILL.md Step 7 直接檢查，此處定義）

- **L9** SPEC-INDEX 存在；索引列出的章節（含 `§0`、`§D`）與 `^## ` 一一對應；BR／VR／TC 編號區間與正文一致。核法：以 `diff` 比對索引列出的章節與 `grep -n '^## ' {文件}` 的輸出。
- **L10** **正文** ≤45KB——量 `## 1.` 到 `## D.` 之前，不含 §0／§D／附錄／CHANGELOG。超標依 `spec-dedup-and-budget.md`：先去重、JSON 改欄位表、示範值外移；仍超標 → 拆附錄檔 `{功能名稱}_附錄_{主題}.md`。**不向使用者請求放行**；真要放行須在 `decisions.md` 記一列。

### Lint 等級
- L9 違反 = **WARNING**；L10 超標且未拆附錄 = **WARNING**（不阻擋開發，但 verifying-specs 會再報一次）

---

## L14：必畫圖存在

### 檢查邏輯
依 `spec-dedup-and-budget.md`「必畫圖清單」BFS 列：§0 總覽圖（端點→核心處理→資料表）、每個寫入端點一張 §3 sequence、有計算／歸集時 §2.5 匯流圖、§7／§8 規則超過 8 條時決策樹圖。用 `grep -c '```mermaid'` 與章節對照。

### Lint 等級
- 缺任一必畫圖 = **WARNING**

---

## L15：公式型規則附算例

### 觸發掃描
§2／§7 規則列含 `＝`、`=`、`％`、`%`、`÷`、`×`、「分攤」「比率」「遮罩」「優先」任一者。

### Lint 規則
每條命中的規則須在同章或 §2.5 有「算例」（輸入→輸出，附資料來源），或一行 ref FRD §5.3 對應 BR 的算例。

### Lint 等級
- 命中規則無算例且無 ref = **WARNING**

---

## L16：§0 一頁摘要

### 檢查邏輯
文件第一個 `## ` 是 `## 0. 一頁摘要`，內含總覽圖、讀者導覽表（四列已填實、無 `{佔位符}`）、關聯表。

### Lint 等級
- 缺 §0 或導覽表為佔位符 = **WARNING**

## Lint 執行時機

| 時機 | 動作 |
|---|---|
| Step 7「驗證規格品質與自我審查」 | 依本檔 L1~L8、L14~L16 逐項掃描並直接修正（L9／L10 定義在此，由 SKILL.md 直接檢查） |
| Step 8「自動驗證與修復」 | `verifying-specs` 重跑時包含本檔規則 |
| Step B7（CR 模式自動驗證） | 只對異動段落執行 |
