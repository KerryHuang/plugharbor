---
name: spec
description: "寫設計文件：產一份 <spec.dir>/YYYY-MM-DD-<slug>-design.md（含可驗收案例；--change 就地更新），也讀改既有文件。Use when 寫規格、寫規格書、spec new、更新規格、需求文件、讀規格某一章。"
triggers: ["寫規格書", "寫功能規格", "需求文件", "更新規格"]
argument-hint: "[--change {ticket}] {功能描述}"
---

# 規格

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔實體路徑：symlink 先 `realpath`，同目錄有 `.plugharbor-root` 就以其內容為 plugin 根；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

把需求寫成設計文件（舊稱規格）。設計文件是 `implement`、`spec-check`、`qa-verify` 的唯一依據。
一律產一份檔。原則：**先收決策、再寫規格；不確定就標記，不猜。**

## 輸入

```
$ARGUMENTS → [--change {ticket}] {功能描述}
```

| 參數 | 說明 |
|------|------|
| `--change {ticket}` | 就地更新既有設計文件，文末 `## 變更紀錄` 加一行（含票號） |
| 功能描述 | 空白時提示輸入後終止 |

## Step 0：讀設定

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir   # 預設 docs/superpowers/specs
```

`spec.dir` 沒設而專案規則（AGENTS.md、`.claude/rules/`）指定了設計文件目錄 → 把該目錄寫進 `.plugharbor/lifecycle.yml` 的 `spec.dir`，回報第一行告知；之後 implement、spec-check 等都從同一個設定讀。有沒有設要讀設定檔判斷（`config.py` 沒設也會回預設值）；已設、或專案 CLAUDE.md 有舊鍵 `sdlc-docs-path`（config.py 會沿用）就照它，不看專案規則。寫法一律巢狀，沒有檔就建，既有檔只加這個區塊、其他鍵不動：

```yaml
spec:
  dir: <目錄>
```

只要讀／查／改既有設計文件的某一章 → 「讀寫既有文件」；其餘走「寫設計文件」。
`config.py` 退出碼 3（只有舊檔 `delivery-flow.yml`）→ 停下請使用者改名。

設定鍵說明見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`。互動詢問一律依
`${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範（建議置首、一次一題、回合可見性）。

## 寫設計文件

格式只有一份：`references/lean-template.md`（七節＋開頭票號行＋驗收格式）；AGENTS 段落有同一份契約，兩條路徑都照它。

**可用 skill 有 `superpowers:brainstorming`** → 交給它做完整設計對話，並交代四件事：
1. 章節與驗收格式照本 skill 的 `references/lean-template.md`；
2. 開頭寫票號行 `票號：#n · 狀態：草稿 · yyyy-mm-dd`；
3. 位置 `<spec.dir>/YYYY-MM-DD-<slug>-design.md`；
4. 問使用者設計題前先照 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md`「設計提問分流」交顧問，只問轉交的。

lifecycle 自己只做 Step 0 的 `spec.dir` 設定與分流，不重複它的問答。

**沒裝 → 退路**，照範本自己寫：

1. **定位**：`<spec.dir>/*<slug>*` 已存在 → 視為更新（等同 `--change`）；否則新建。已有設計草稿就沿用，不重問已定案的事。
2. **蒐證**：搜既有程式碼與設計文件找可重用元件、受影響範圍；涉及資料表且有唯讀 DB 工具時查表結構。範圍大時派 `lifecycle:scout` 落檔，主 session 只讀結論。命中 domain 邊界照 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md` 開顧問桌；開頭行有「來源：舊系統移植」（舊範本為表頭「來源｜舊系統移植」，兩種都認）照 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`。
3. **解決策樹**：把決策樹每個分支解完才動筆，**一次一題**、用 `AskUserQuestion`（沒有該工具就文字問）、推薦選項放第一個並附代價。撰寫中冒出新的品味決策 → 停筆先問。
4. **撰寫**：照範本；專案規則規定的必要章節（AGENTS.md、`.claude/rules/`，例如「ERP 對照」）放 `## 留給 builder` 之前，不刪範本章節；決策寫進 `## 決定`，不另開 `decisions.md`。
5. **自查**：跑範本的品質檢查清單；`[NEEDS CLARIFICATION` 未清零就逐條列給使用者。
6. **`--change` 或檔案已存在**：就地修改受影響段落，**取代不追加**；文末 `## 變更紀錄` 加一行，有票號就寫上。需要回覆票時交給 `tickets:ticket-reply`。

### 機械決策與品味決策（退路用）

| 類別 | 判準 | 處理 |
|------|------|------|
| **機械決策** | 有可查的唯一正解，或專案慣例已定：命名、欄位型別、沿用哪個既有元件、排序預設、錯誤碼格式、檔案位置 | 自己查證後定案，寫進 `## 決定`，`（拍板：證據）`或`（拍板：自行決定）`，**不問人** |
| **品味決策** | 多個方案都合理、取捨牽涉業務價值或使用者體驗：範圍要不要含某情境、狀態流程怎麼設計、例外時使用者看到什麼、要不要偏離既有行為 | 先整批分流（`consultant-desk.md`「設計提問分流」）；轉交的一次一題問人，附推薦與代價，答完寫 `（拍板：使用者）` |

判不出類別就當品味決策。不確定處寫 `[NEEDS CLARIFICATION: 具體問題]`，不猜；有依據的推導另標 `[推論]` 並寫依據。手段（框架、快取、鎖、佇列）寫成 `TD-nn（拍板：待實作）` 留給實作。

**下一步**：`lifecycle:spec-check`（實作前檢查）跑一次；`lifecycle:implement` 的品質閘門見到通過紀錄不重跑。通過後 `tickets:ticket-create` 或 `lifecycle:implement`。

## 讀寫既有文件

直接讀整份；只改某一章時 `grep -n "^## "` 定位後就地修改，更新照「寫設計文件」第 6 步。舊格式文件（§ 編號章節、表頭表格）照舊讀，不強制轉檔。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 功能描述空白 | 提示輸入，終止 |
| 範本找不到 | 回報範本路徑錯誤，終止 |
| 帶舊參數 `--stage`，或設定檔有舊鍵 `scale` | 回一句「四份文件規格鏈已在 lifecycle 3.0.0 移除，改產一份設計文件」，照「寫設計文件」繼續 <!-- allow-legacy --> |
