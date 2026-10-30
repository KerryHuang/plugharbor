---
name: linear-reply
description: "Linear 票有 Dev 或 AI 的未回覆留言需 PM／SA 回應時使用：讀取未答留言、自動判 PM／SA 角色、預覽草稿確認後回票，並更新對應規格文件再觸發 verifying-specs。"
argument-hint: "<票號>"
model: sonnet
---

# Linear 票問題回覆

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

處理 Linear 票上 Dev 或 AI agent 提出的未回覆問題，以 PM 或 SA 角色回覆並同步更新規格文件。
互動詢問依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範。

## 輸入參數

```
$ARGUMENTS → <ticket-id>
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `ticket-id` | 是 | Linear 票 ID，例如 `ENG-123` |

---

## 執行流程

### 1. 驗證輸入

若 `$ARGUMENTS` 為空，提示使用者輸入票 ID 並終止。

### 2. 偵測 Linear MCP

使用 `ListMcpResourcesTool` 確認 Linear MCP 可用（名稱含 "linear"）。未找到 → 提示設定 `.mcp.json`，終止。

### 3. 讀取票資訊與 Comments

呼叫 `get_issue` 取得票基本資訊（標題、描述、team）。
呼叫 `list_comments` 取得所有 comment。

### 4. 過濾未回覆問題

**「未回覆」判斷邏輯：**

1. Comment 由非 PM/SA 使用者（Dev / AI agent）發出
2. 該 comment 之後，沒有 PM/SA 使用者的後續回覆

**PM/SA 使用者識別原則**：
- 需求端 team 的票，assignee 視為 PM
- 開發端 team 的票，assignee 視為 SA/Dev（需結合問題類型判斷）
- team 對應不明時，用 `list_teams` 列出請使用者指認，不寫死
- 無法確認角色時，以問題內容決定角色（業務規則 → PM，系統設計 → SA）

若無未回覆問題 → 輸出「此票目前無待回覆問題」並終止。

### 5. 逐一處理每個未回覆 Comment（逐題落地，禁止批次跳確認）

**一次只處理一則**：每則走 5a → 5b → 5c，取得使用者對該則的裁決後，才分析下一則。
禁止把所有 comment 一口氣分析完就直接跳發佈確認——使用者必須先看到每一則的
根因、方案與回覆全文，才有東西可以確認。

#### 5a. 分析問題 → 判斷角色

| 問題類型 | 角色 | 更新文件 |
|---------|------|---------|
| 業務規則、需求範圍、使用者行為、流程邏輯 | PM | FRD / CR-FRD |
| 系統設計、資料流、API 行為、DB 結構、技術限制 | SA | SAD / BFS / FFS（視影響範圍） |
| 橫跨兩者 | PM + SA | FRD + 對應 SA 文件 |

#### 5b. 撰寫分析與回覆草稿

以判斷的角色視角撰寫，內容必含四段，缺一不可：

1. **問題原文**：該 comment 的提問內容（長則摘錄關鍵段）
2. **根因分析**：為什麼會有這個問題——附查證證據（codebase 路徑／DB 查詢結果／規格出處），不是憑印象
3. **解決方案**：採用的做法與理由；若有被否決的替代方案，簡述為何不採。**Dev 問的是手段**（用哪種鎖／快取／佇列／存哪）→ 回答**約束、現況、陷阱**並追加 `decisions.md` TD（格式依 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`），不替 Dev 選型；問的是行為／契約／資料語意 → 由 PM／SA 定案回寫規格
4. **回覆全文**：將原樣發佈至 Linear 的完整文字——給使用者的預覽必須完整，不得截斷。
   **發佈到 Linear 的回覆本身要短**：只給結論＋一句依據＋規格錨點（如 `FRD §3.2`），不抄規格原文，單則 ≤10 行。

#### 5c. 逐題落地與裁決（確認閘道 A）

把 5b 的四段以文字**完整輸出**給使用者，然後：

- **該回合必須以純文字收尾，不得帶任何工具呼叫**——包含 `AskUserQuestion`。
  同回合的問題卡片會蓋掉先前輸出的文字，使用者根本看不到內文就被迫作答。
- 收尾以文字詢問這一則的裁決：**發佈／修改後重列／跳過**，等使用者回覆。
- 使用者要求修改 → 修訂後重新完整輸出（仍是純文字收尾），再次徵詢。
- 取得裁決後才進入下一則的 5a。

所有 comment 裁決完成後，輸出彙總表並以 `AskUserQuestion` 做**最終發佈確認**
（此時全文皆已在先前回合落地，卡片不會遮到未讀內容）：

```
## 待發佈彙總

票：{ticket-id} — {票標題}

| # | 問題摘要 | 角色 | 裁決 | 更新文件 |
|---|---------|------|------|---------|
| 1 | {問題前 50 字} | PM | 發佈 | FRD §{章節} |
| 2 | {問題前 50 字} | SA | 跳過 | — |
```

- **question**：「是否確認發佈以上裁決為『發佈』的回覆？」
- **header**：「發佈確認」
- **multiSelect**：false
- **options**：
  1. `是，依裁決發佈`
  2. `否，取消（不發佈）`

選項 1 → 對裁決為「發佈」的項目執行 5d/5e；選項 2 → 輸出「已取消，未發佈任何回覆」並終止。

#### 5d. 發佈回覆至 Linear

呼叫 `save_comment`，將回覆內容發佈至該 comment 所在的票（`issueId`）。

#### 5e. 定位並更新對應 spec 文件

> 讀取 FRD／SAD／BFS／FFS 一律定向讀取（先 `grep -n 'SPEC-INDEX v1'` 定位索引，再依章節 offset/limit 讀），不整檔載入。

1. 依 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md` 確認文件目錄位置，搜尋對應的規格文件（FRD / SAD / BFS / FFS）
2. 定位問題相關的段落
3. 用 Edit 工具更新文件，補充或修正原始規格內容
4. 若問題揭示了文件中的遺漏，新增對應段落
5. 若更新了 FRD §2.2 驗收條件且功能目錄存在 `features/*.feature` → 依 `${CLAUDE_PLUGIN_ROOT}/skills/requirement/references/bdd-feature-guide.md` 整檔覆蓋重轉譯（FRD 為唯一權威）

### 6. 輸出處理摘要

```
## linear-reply 處理結果

票：{ticket-id} — {票標題}
處理 comment 數：{n}

| # | 問題摘要 | 角色 | 更新文件 |
|---|---------|------|---------|
| 1 | {問題前 50 字} | PM | FRD §{章節} |
| 2 | {問題前 50 字} | SA | BFS §{章節} |

Linear 回覆：已發佈
Spec 更新：已完成
```

### 6b. 確認後繼續（確認閘道 B）

摘要輸出後，**必須**使用 `AskUserQuestion` 詢問使用者：

- **question**：「以上回覆已發佈、spec 文件已在本地更新，變更是否正確？」
- **header**：「變更確認」
- **multiSelect**：false
- **options**：
  1. `是，繼續後續步驟（推薦）`
  2. `否，需手動修正後再繼續`

依使用者回應：選項 1 → 繼續 Step 7；選項 2 → 輸出「請完成手動修正後，執行 `sa-flow:verifying-specs {文件路徑}` 驗證」並終止。

### 7. 詢問是否執行 verifying-specs

所有 comment 處理完後，**必須**使用 `AskUserQuestion` 詢問使用者：

- **question**：「是否要立即執行 sa-flow:verifying-specs 驗證文件一致性？」
- **header**：「驗證執行」
- **multiSelect**：false
- **options**：
  1. `是，完整模式驗證`
  2. `是，快速模式驗證（跳過舊系統比對）`
  3. `否，稍後手動執行（推薦預設）`

依使用者回應：選項 1 → 執行 `sa-flow:verifying-specs {已更新文件路徑}`；選項 2 → 執行 `sa-flow:verifying-specs {已更新文件路徑} --quick`；選項 3 → 輸出提示語「如需驗證，請執行：`sa-flow:verifying-specs {文件路徑}`」並結束。

---

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| 票 ID 不存在 | 顯示 Linear 錯誤訊息，終止 |
| Linear MCP 未設定 | 提示設定 `.mcp.json`，終止 |
| 找不到對應 spec 文件 | 提示「找不到 {文件類型}，請確認文件路徑」，跳過文件更新，繼續回覆 |
| save_comment 失敗 | 顯示錯誤，列出已成功回覆的 comment |
| 無未回覆問題 | 輸出說明並正常終止（非錯誤） |

---

## 使用範例

```bash
linear-reply ENG-123
linear-reply PROJ-456
```

## 完整開發流程

詳見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`。
