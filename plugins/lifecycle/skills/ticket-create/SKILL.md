---
name: ticket-create
description: "依自然語言描述開票：精簡模式（scale: lean，預設）開一張票；scale: full 開父票＋PM／SA／QA／Dev 四張子票。所有票務動作經 ticket-ops，不綁特定票務工具。Use when 「開票」「建票」「我要開一張票」「create ticket」「ticket-create」。"
argument-hint: "{自然語言描述}"
model: sonnet
---

# 開票

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

把自然語言描述變成票：判類型（Feature／Bug）、盤點既有票、出草稿讓使用者確認，再經 `lifecycle:ticket-ops` 建票。票面只放「要交付什麼、對齊哪條需求、去哪查明細」，規格明細用路徑指路，不抄進票。
互動詢問依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範（推薦置首、一次一題）。

- 票描述範本與通則：`${CLAUDE_SKILL_DIR}/references/ticket-templates.md`
- 建票派工與建票規則：`${CLAUDE_SKILL_DIR}/references/create-dispatch.md`

## 輸入

`$ARGUMENTS` 為自然語言描述（必填）。空 → 請使用者描述要做的功能或問題，不猜。

## 規模

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get scale
```

缺檔或缺鍵回預設 `lean`（見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`）。規模只決定拆幾張票，流程相同。

| scale | 票樹 |
|-------|------|
| `lean`（預設） | 一張票（Feature 或 Bug 各有範本），不拆角色 |
| `full` | Feature：父票＋四張子票 PM（需求）、SA（規格）、QA（測試）、Dev（實作）。Bug：父票＋QA（重現與驗收）、Dev（修復）兩張子票，不開 PM、SA |

## 流程

### 1. 前置

本 skill 不直接呼叫任何票務工具；缺 `ticket.*` 設定時由 `lifecycle:ticket-ops` 的設定流程問使用者並寫入設定，補完後繼續。只有 ticket-ops 回報工具不可用，或使用者拒絕補設定時，才原樣轉告後終止。

### 2. 判類型

分析描述判 Feature 或 Bug，用 `AskUserQuestion` 確認（判定類型置首標「（推薦）」，一行理由寫進 description）。判準：「想要不同或新的行為」是 Feature（含調整既有功能）；「既有功能跑出錯誤結果」是 Bug。

### 3. 盤點既有票（必做）

開票前用 `lifecycle:ticket-ops` 的 `query`（關鍵字）找重複或同主題的票；描述含票號則 `get` 讀該票與其 children。

- 已有相同主題的票 → 告知使用者，問要併入既有票（不開）、掛在既有票下開子票，還是仍開新票。
- `full` 且已有父票 → 只補缺的子票，掛在既有父票下，不另建新父票。
- 既有票內容不改（開票人的原始敘述保留原貌）；缺的相依用 `link_blocked_by` 補。

### 4. 推導預設值，只問查不到的

沿用同主題既有票的慣例（label 組合、標題格式），不重問；草稿裡標明「依據某某票推導」供覆核。**要問**的只有：

- 初始階段：預設 `lean` 的票與 `full` 的父票、第一張子票用 `todo`，其餘子票 `backlog`；使用者說「先放著」整批改 `backlog`。
- 前置條件缺漏（例如 Feature 需求太淺）→ 建議先 `lifecycle:explore`，由使用者決定是否仍開票。

### 5. 讀取依據、寫草稿

找已完成的規格（目錄取 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir`，預設 `docs/specs`）。找到就在票描述附路徑，並只讀取材需要的章節，不整檔載入。沒有規格就依 `ticket-templates.md` 從描述生成。

草稿含：每張票的標題、階段、labels、描述全文、parent、相依表（每條相依的依據）。開票前先看規格進度（目錄同上）：`lean` 規格檔或 `full` 的 FRD 已存在時，PM 子票預設階段 `in-review`（需求內容已成文、待人確認，而非 `todo`；使用者確認過可改 `done`）；SA 子票視 BFS／FFS 是否已完成調整（兩者都在 → 同 PM 的預設；未備 → 照步驟 4）。只改預設階段，流程不變，使用者可在步驟 6 改。`full` 的票間相依：SA 等 PM、Dev 等 SA、QA 等 Dev（Bug：QA 等 Dev），均以 `blocked_by` 表達；父子之間不另掛。

### 6. 確認

草稿全文先以文字輸出並收尾一回合（`AskUserQuestion` 會蓋住同回合文字），下一回合再問：確認建票／要修改／取消。`full` 時使用者可在此刪掉不需要的角色票（刪掉的票其相依一併移除）。

### 7. 建票

- `lean`：自己依序呼叫 `lifecycle:ticket-ops` 的 `create`。
- `full`：把確認後的草稿寫成 ticket-plan 檔，派 subagent 照檔建票，只收回票號表；做法見 `create-dispatch.md`。

建票規則（父子關係、票源 flag、相依寫入、失敗處理）見 `create-dispatch.md`「建票規則」。

### 8. 回報

票樹結構、票資訊表（票號、標題、階段、labels、blocked_by、URL）、降級說明（`ticket-ops` 回報的落差，如 GitHub 的 blocked-by 只寫在內文）、下一步。票號與 URL 取自建票回傳，不再逐張 `get`。

下一步依情境：Feature 規格未備 → 建議 `lifecycle:spec`；已備 → 可開工；Bug → 可進 `lifecycle:implement` 修復。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 描述空白 | 請使用者提供，終止 |
| `ticket-ops` 回報工具不可用，或使用者拒絕補 `ticket.*` 設定 | 原樣轉告，終止（設定缺而使用者願補時不走此列，見步驟 1） |
| 建票中途失敗 | 列出已成功的票，不自行換參數重試；使用者決定補開或收尾 |
| 相依被後端拒絕 | 停下回報，不改掛弱關聯蒙混 |
