---
name: explore
description: "新功能起手、寫 FRD 前快速收斂需求：六維引導問答，產出探索摘要供 requirement 使用。觸發：「探索需求」「explore」。"
argument-hint: "[功能描述]"
model: sonnet
---

# 需求探索

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

快速收斂需求，為撰寫 FRD 準備結構化輸入。適用於需求**大致明確**但尚未整理的情況。
互動詢問一律依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範（AskUserQuestion＋建議置首＋一次一題＋回合可見性）。

> **需求模糊、概念未定？** 建議改用 `superpowers:brainstorming` 進行完整設計探索。
>
> **素材還很零碎、連該問什麼都不確定？** 先跑 `sa-flow:interview-prep`——把多場會議／訪談
> 彙整成已知未知盤點，或產訪談大綱去補資料，回來再跑六維。

## 輸入參數

```
$ARGUMENTS → [功能描述]
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `功能描述` | 否 | 簡單描述功能方向；省略時由第一個問題引導收集 |

---

## 執行流程

### 0. Brainstorming 偵測

偵測 `superpowers:brainstorming` 是否可用（搜尋 `.claude/skills/brainstorming/` 或已安裝的 superpowers plugin）：

- **可用** → 使用 `AskUserQuestion` 詢問：

  > 偵測到 `superpowers:brainstorming` 已安裝。
  >
  > - **A. 使用 brainstorming**（推薦：需求模糊、需要完整設計探索）
  > - **B. 繼續 explore**（需求已大致明確，快速收斂即可）

  使用者選 A → 終止，提示執行 `superpowers:brainstorming`；選 B → 繼續。

- **不可用** → 直接繼續。

### 1. 功能定位

從 `$ARGUMENTS` 或後續問答中提取：

- **功能名稱**：2-6 個字的短名稱
- **所屬模組**：識別功能歸屬的業務模組（**取自 `{docs-root}` 既有第一階目錄，禁止自創**；新增模組先問使用者）

若無法從描述中確定模組，在六維收斂結束前使用 `AskUserQuestion` 詢問：

> 這個功能屬於哪個業務模組？（列出 `{docs-root}` 既有模組目錄供選）

### 1.5 顧問桌啟動（可選但推薦）

> 依 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md`：**一條規格鏈只開一次顧問桌，主場在
> `system-analysis`**。explore 階段**預設不開**——此時證據最少，顧問產出多為泛論，
> 而同一批 domain 問題到 SAD 階段會再被問一次。
>
> **僅在需求本身的業務邊界未定**（全新業務概念、做不做得到／算不算同一件事說不清）時才開，
> 因為那種情況下不先釐清就連六維都收斂不了。開了要在探索摘要留痕，SAD 階段改用差異複審。

命中上述情況時，以 `AskUserQuestion` 詢問（`不啟動，直接進六維 Q&A（推薦）` /
`啟動顧問桌引導收斂`）。選啟動 → 進入顧問桌流程（單顧問 `domain-advisor`）：

1. **派發 scout agent** 蒐集證據：
   ```
   subagent_type: "sa-flow:scout"
   prompt: |
     context: {使用者描述 / $ARGUMENTS}
     keywords: [{從描述提取的關鍵字}]
     docs_root: {sdlc-docs-path}
   ```
   收到 `evidence_bundle` YAML。

2. **派發顧問**：`domain-advisor`（mode: `consult`，輸入 `evidence_bundle`），主導六維引導。

3. SKILL 將顧問的每輪提問展示給使用者。

4. 顧問桌結束 → 結論落檔 `analysis/consultant-notes.md`（供 SAD 判定「鏈上已開過桌」）→
   使用者已回答完 6 維 → 跳到 Step 3 確認摘要。
   - 摘要必須在每一維度標註 `[Evidence: ...]` 或 `[使用者回答 R{N}]`，**不可空泛敘述**。

未命中例外、或選擇不啟動 → 走 Step 2 六維 Q&A（**預設路徑**）。

### 2. 六維需求收斂（傳統模式）

> 預設路徑；Step 1.5 啟動顧問桌時已由主席引導完成，不重跑。

依序使用 `AskUserQuestion` 詢問以下問題，**一次一個**，確認答案後再問下一個。
每題**必附建議選項**：先依 `$ARGUMENTS`、codebase 與 docs 線索推測合理答案作為選項（最可能的放第一位標「（推薦）」，推測依據一行寫進 description），讓使用者能快速選擇或用 Other 補充。

> 若 `$ARGUMENTS` 已包含某維度的答案，跳過該問題。

#### 維度 1：業務痛點

> 這個功能要解決什麼問題？目前沒有它時，使用者遇到什麼困難？

#### 維度 2：使用者

> 主要使用者是誰？（角色/職稱）預估使用頻率？（每天 / 每週 / 按需）

#### 維度 3：功能邊界

> 這個功能**包含**哪些子功能？有什麼是**明確不做**的？

#### 維度 4：關鍵業務規則

> 最重要的業務規則有哪些？（1-3 條即可）例如：計算邏輯、狀態條件、權限限制。

#### 維度 5：舊系統對應

> 這個功能是否有對應的舊系統（FoxPro / ERP / 其他）？
> - 有 → 舊系統功能名稱或代號？需要遷移資料？
> - 無 → 全新功能

#### 維度 6：限制與時程

> 有無技術限制、整合依賴，或時程壓力需要特別說明？

### 3. 確認摘要

將收集到的答案整理為結構化摘要。摘要屬長內容，**以文字完整輸出並結束該回合**（不可塞進 AskUserQuestion、也不可同回合先印再問——使用者會看不到）；下一回合使用者已明確表態則直接續行，未表態才用 `AskUserQuestion` 確認（`正確，繼續（推薦）` / `需修正`）：

```
功能名稱：{從描述中提取}
所屬模組：{模組名稱}
業務痛點：{維度 1}
主要使用者：{維度 2}
功能邊界：
  - 包含：{...}
  - 排除：{...}
關鍵業務規則：
  1. {規則 1}
  2. {規則 2}
舊系統對應：{有/無，含細節}
限制與時程：{維度 6}
```

使用者確認或修正後，繼續。

### 4. 輸出探索摘要

確認後，使用 Write 工具將摘要寫入（與 `sa-flow:requirement` 產出同目錄）：

```
{docs-root}/{模組名稱}/{功能名稱}/{功能名稱}_探索摘要.md
```

`{docs-root}` 依 `sdlc-docs-path` 設定決定（未設定則為 `docs/`）。

格式：

```markdown
# {功能名稱} 探索摘要

> 產出時間：{YYYY-MM-DD}
> 來源：sa-flow:explore
> 所屬模組：{模組名稱}

## 業務痛點
{內容}

## 使用者
{內容}

## 功能邊界
**包含：**
- {項目}

**排除：**
- {項目}

## 關鍵業務規則
1. {規則}

## 舊系統對應
{有/無，含細節}

## 限制與時程
{內容}
```

### 5. 完成報告

輸出：

- 探索摘要路徑
- 收集維度數（6/6）

**下一步**：執行 `sa-flow:requirement {功能名稱}`，explore 摘要會被自動讀取作為 FRD 撰寫輸入。
含 UI 的功能若需要，可先用任何方式（手繪、線框稿、原型工具）與 PO/使用者對焦畫面，再把結論補進探索摘要。

---

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| 使用者對某維度回答「不確定」 | 記錄為「待確認」，在摘要中標注 ⚠️，繼續下一個維度 |
| 目錄不存在 | 使用 Write 工具自動建立（Write 會建立中間目錄） |

## 使用範例

```bash
explore
explore 訂單管理新增批次出貨功能
explore 會員點數折抵從舊系統遷移至 Web
```

## 完整開發流程

詳見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`。
