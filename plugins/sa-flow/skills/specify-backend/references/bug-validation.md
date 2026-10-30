# Bug 假設驗證指引（後端）

> 此步驟對應 specify-backend SKILL Step 4.1.6。當 PM/SA 宣稱「修正既有功能 Bug」時，**必須**以 codebase 證據驗證，不可照單全收。

## 為什麼需要

PM/SA 宣稱的 Bug 可能：
- ✅ 真的是 Bug（既有 code 與業務期待不符）
- ❌ 是 Bug 但不在 PM 描述的欄位（PM 認知有誤）
- ❌ 根本不是 Bug（既有 code 已正確，PM 看錯）

若 skill 不驗證，BFS 會寫入錯誤的「修正範圍」，導致 RD 修錯地方或範圍過度宣稱。

---

## 觸發條件

規格描述含以下任一關鍵字：
- 「修正」「Bug」「fix」
- 「修正既有 Handler / Service / API」
- 「對齊 / 一致性 / 統一」針對既有功能

---

## 驗證流程

### Step 1：列出 PM 宣稱的所有 Bug

從規格描述 / FRD / SAD 中提取一份「**待驗證 Bug 清單**」：

| Bug 編號 | PM 宣稱問題 | 影響欄位 / 行為 |
|---|---|---|
| Bug-1 | 規格欄位未鏡像寫入 SPEC_A 與 SPEC_B | `SPEC_A`, `SPEC_B` |
| Bug-2 | 材質帶錯欄位 | `MATERIAL` |
| Bug-3 | 加工旗標未依品項類別自動判定 | `PROCESS_FLAG` |

### Step 2：對每個 Bug 找出既有 code 行號

對每個 Bug，使用 Grep / Read 定位既有實作：

```bash
# 通常是 Create*FromXxx mapping 方法
Grep "{相關欄位名}|{相關屬性名}" path=.../{Handler}.cs -n
Read path=.../{Handler}.cs offset={定位行} limit=50
```

### Step 3：對照 PM 宣稱 vs 實際 code

| Bug 編號 | PM 宣稱 | 既有 code（行號） | 比對結果 |
|---|---|---|---|
| Bug-1 | 規格未鏡像 | L194-239：`SpecA = s; SpecB = s;` | ❌ **不是 Bug**（已鏡像） |
| Bug-2 | 材質帶錯 | L194-239：`MaterialId = source.MaterialId` | ✅ **是 Bug**（用 ID 而非 Name 字串） |
| Bug-3 | 加工旗標硬編 | L194-239：`NeedProcess = true`（硬編） | ✅ **是 Bug** |

### Step 4：對齊 PM（若有非真 Bug 項目）

若任何 Bug 經驗證**不是真 Bug**，**必須**用 `AskUserQuestion` 跟 PM 對齊：

```
question: "經 codebase 驗證，您原本提到的 Bug 中，有 N 項可能不是 Bug。請確認本次 ticket 真正要修的範圍。"
options:
  1. 只修經驗證為真 Bug 的項目（推薦）
  2. 全部都修（包含非 Bug 項目，視為需求調整）
  3. 跟我確認每一項
```

### Step 5：BFS §1.2 範圍精準化

依驗證結果寫入 BFS：

```markdown
### 1.2 功能範圍

**後端實作範圍：**
- 修正 {Handler} 的 {欄位} Bug — 經 codebase L{行號} 驗證為真 Bug

**不在本規格範圍：**
- PM 原本提及的「{欄位}」經驗證**不是 Bug**（既有 code L{行號} 已正確），故不在修正範圍
```

---

## Lint 規則

1. BFS §1.2 提到「修正既有 Handler 的 Bug」**必須**附 §A.4 既有 mapping 完整對照（與 reuse-scan §4.1.5b 連動）
2. 「修正範圍」每一項**必須**對應到 codebase 具體行號，否則視為 CRITICAL
3. 任何「Bug 假設」未經驗證即寫入 BFS，視為 CRITICAL
