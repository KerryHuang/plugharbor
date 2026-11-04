---
name: spec
description: "寫功能規格：預設精簡模式產一份 <spec.dir>/<feature>.md；scale: full 依範本分棒產 FRD→SAD→BFS→FFS（--change 為 CR 變體），也負責按章節讀寫既有規格。Use when 寫規格、寫規格書、spec new、更新規格、寫 FRD、需求文件、系統分析、寫 SAD、後端規格、寫 BFS、前端規格、寫 FFS、讀規格某一章。"
argument-hint: "[--stage frd|sad|bfs|ffs|index] [--change {ticket}] {功能描述或功能目錄}"
---

# 規格

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

把需求寫成規格。規格是 `implement`、`review`、`qa-verify` 的唯一依據。
規模只決定產出哪些檔，流程原則相同：**先收決策、再寫規格；不確定就標記，不猜。**

## 輸入

```
$ARGUMENTS → [--stage frd|sad|bfs|ffs|index] [--change {ticket}] {功能描述或功能目錄}
```

| 參數 | 說明 |
|------|------|
| `--stage` | 指定分層規格的某一棒（隱含 full 規模）。省略時依 `scale` 決定 |
| `--change {ticket}` | CR 變體：in-place 更新既有規格並記 CHANGELOG。lean 直接改那一份；full 搭配 `frd`／`bfs`／`ffs`（SAD 無 CR 變體） |
| 功能描述 | 空白時提示輸入後終止 |

## Step 0：讀設定、選路徑

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get scale      # lean（預設）｜full
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir   # 預設 docs/specs
```

| 條件 | 走哪條 |
|------|-------|
| 只要讀／查／改既有規格的某一章，或 `--stage index` | 「讀寫既有規格」 |
| 有 `--stage frd/sad/bfs/ffs` | 「full：分層規格」該棒 |
| `scale: full`，無 `--stage` | 「full：分層規格」，從第一份還沒產出的文件起跑 |
| 其餘（含設定檔不存在） | 「lean：一份規格」 |

設定鍵說明見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`。互動詢問一律依
`${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範（建議置首、一次一題、回合可見性）。

## 共通原則（兩種規模都適用）

### 1. 先收決策，再寫規格

動筆前把這個功能的待決事項全部列出，逐條分成兩類：

| 類別 | 判準 | 處理 |
|------|------|------|
| **機械決策** | 有可查的唯一正解，或專案慣例已定：命名、欄位型別、沿用哪個既有元件、排序預設、錯誤碼格式、檔案位置 | 自己查證後定案，記入決策表（`拍板`＝`SA` 或 `證據`），**不問人** |
| **品味決策** | 多個方案都合理、取捨牽涉業務價值或使用者體驗：範圍要不要含某情境、狀態流程怎麼設計、例外時使用者看到什麼、要不要偏離既有行為 | 一次一題問人，附推薦選項與代價，答完記入決策表（`拍板`＝`PO`） |

- 品味決策全部收齊才進撰寫；撰寫中冒出新的品味決策 → 停筆先問，不先寫一版再改。
- 判不出類別時當品味決策處理。
- 需求本身還模糊、連該決定什麼都不清楚 → 先跑 `lifecycle:explore`。

### 2. 不確定處標 `[NEEDS CLARIFICATION]`，不猜

- 能查就查（codebase、DB 唯讀查詢、既有規格、票），查不到且能問就問。
- 當下問不到（派出去的 subagent、使用者暫不答）→ 在原處寫 `[NEEDS CLARIFICATION: 具體問題]`，不自行補值。
- 有依據的推導另標 `[推論]` 並寫依據；兩者不混用。
- 寫完前清點：殘留的 `[NEEDS CLARIFICATION` 逐條列給使用者；未清零的規格狀態維持「草稿」，`spec-check` 會判 BLOCKER。

### 3. 技術中立

只寫做什麼、輸入輸出、規則與約束；框架、快取、鎖、佇列等手段留給實作（full 規模寫成 TD 留置，見 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`）。

## lean：一份規格

產出 `<spec.dir>/<feature>.md`（`<feature>` 用 kebab-case 短名）。範本與自查清單：`references/lean-template.md`。

1. **定位**：`<spec.dir>/<feature>.md` 已存在 → 視為更新（等同 `--change`）；否則新建。有探索摘要或設計文件（`lifecycle:explore`、brainstorming 產出）就沿用，不重問已定案的事。
2. **蒐證**：搜既有程式碼與規格找可重用元件、受影響範圍；涉及資料表且有唯讀 DB 工具時查表結構。範圍大時派 `lifecycle:scout` 落檔，主 session 只讀結論。
3. **收決策**：依共通原則 1，列待決事項 → 機械決策自己定 → 品味決策逐題問。
4. **撰寫**：照範本寫；決策寫進 §5 決策表，不另開 `decisions.md`。
5. **自查**：跑範本的品質檢查清單；`[NEEDS CLARIFICATION` 未清零就照原則 2 回報。
6. **CR（`--change` 或檔案已存在）**：in-place 修改受影響段落，**取代不追加**；版本號 +1、§7 加一列，有票號就寫上。需要回覆票時交給 `lifecycle:ticket-reply`。

**下一步**：建議跑 `lifecycle:spec-check`（lean 規格檢查），通過後 `lifecycle:ticket-create` 或 `lifecycle:implement`。

## full：分層規格（FRD → SAD → BFS → FFS）

每一棒的完整做法在 `references/stages/`，執行該棒時讀對應檔並照做；那些檔裡的「本 skill」指該棒。

| 棒 | 角色 | 產出 | 做法 |
|----|------|------|------|
| `frd` | 資深 PM | `*_需求文件.md`（FRD／CR-FRD） | `references/stages/frd.md` |
| `sad` | 資深 SA | `*_系統分析文件.md`（SAD） | `references/stages/sad.md` |
| `bfs` | 後端規格 | `*_後端功能規格書.md`（BFS／CR-BFS） | `references/stages/bfs.md` |
| `ffs` | 前端規格 | `*_前端功能規格書.md`（FFS／CR-FFS） | `references/stages/ffs.md` |

- 範本在 `${CLAUDE_PLUGIN_ROOT}/templates/`（`frd.md`、`sad.md`、`bfs.md`、`ffs.md`，CR 用 `cr-*.md`）。
- 文件落 `{docs-root}/{模組}/{功能}/`：`{docs-root}` 取專案 `CLAUDE.md` 的 `sdlc-docs-path`，未設定則用 `spec.dir`。
- 鏈的順序、standard／lite 分流（lite 跳過 SAD）、交棒條件：`${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`、`chain-profile.md`、`handoff-protocol.md`。
- 決策全鏈落同目錄 `decisions.md`（`${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`）。共通原則 1 的分類在各棒的確認門與決策落檔步驟套用：機械決策不進確認門。
- 起點判定（無 `--stage`）：讀 `analysis/_context.yml` 與功能目錄已有文件，從第一份缺的開始；全都有 → 停下問使用者要改哪一份或跑 `spec-check`。
- 舊系統移植（`_context.yml` 的 `chain_origin: legacy`）：各棒依 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`，以舊系統行為為準，不限舊系統技術。
- 要跨 session 一棒一個 worker 跑完整條鏈，使用者可手動叫 `lifecycle:spec-chain`。

## 讀寫既有規格

讀規格一律按章節，不整檔載入（BFS 常 60–150 KB）：先讀 SPEC-INDEX，`grep -n "^## "` 定位，再帶 offset／limit 讀。
完整做法（含可選的 codebase-memory-mcp 加速路徑、寫入後更新 SPEC-INDEX 與驗證）：`references/stages/index.md`；
SPEC-INDEX 格式：`references/index/spec-index-format.md`。lean 規格短，直接讀整份即可。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 功能描述空白 | 提示輸入，終止 |
| 範本找不到 | 回報範本路徑錯誤，終止 |
| `--stage sad --change` | SAD 無 CR 變體：改走 in-place 修訂或重跑 `--stage sad`，先問使用者 |
