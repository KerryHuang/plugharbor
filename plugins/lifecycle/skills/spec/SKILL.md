---
name: spec
description: "寫功能規格：產一份 <spec.dir>/<feature>.md（含可直接驗收的 §2.3 驗收案例；--change 為 CR 變體），也負責讀改既有規格。Use when 寫規格、寫規格書、spec new、更新規格、需求文件、讀規格某一章。"
triggers: ["寫規格書", "寫功能規格", "需求文件", "更新規格"]
argument-hint: "[--change {ticket}] {功能描述}"
---

# 規格

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔實體路徑：symlink 先 `realpath`，同目錄有 `.plugharbor-root` 就以其內容為 plugin 根；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

把需求寫成規格。規格是 `implement`、`spec-check`、`qa-verify` 的唯一依據。
一律產一份規格檔。原則：**先收決策、再寫規格；不確定就標記，不猜。**

## 輸入

```
$ARGUMENTS → [--change {ticket}] {功能描述}
```

| 參數 | 說明 |
|------|------|
| `--change {ticket}` | CR 變體：in-place 更新既有規格並記 §7 變更紀錄 |
| 功能描述 | 空白時提示輸入後終止 |

## Step 0：讀設定

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir   # 預設 docs/specs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get scale      # 舊鍵：固定回 lean
```

`get scale` 的 stderr 有「已在 lifecycle 3.0.0 移除」→ 照錯誤處理表，在最後回報的第一行轉告使用者（可刪掉設定檔的 `scale` 鍵），流程照常。

`spec.dir` 沒設而專案規則（AGENTS.md、`.claude/rules/`）指定了設計文件目錄 → 把該目錄寫進 `.plugharbor/lifecycle.yml` 的 `spec.dir`，回報第一行告知；之後 implement、spec-check 等都從同一個設定讀。有沒有設要讀設定檔判斷（`config.py` 沒設也會回預設值）；已設、或專案 CLAUDE.md 有舊鍵 `sdlc-docs-path`（config.py 會沿用）就照它，不看專案規則。寫法一律巢狀，沒有檔就建，既有檔只加這個區塊、其他鍵不動：

```yaml
spec:
  dir: <目錄>
```

只要讀／查／改既有規格的某一章 → 「讀寫既有規格」；其餘走「寫規格」。
`config.py` 退出碼 3（只有舊檔 `delivery-flow.yml`）→ 停下請使用者改名。

設定鍵說明見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`。互動詢問一律依
`${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範（建議置首、一次一題、回合可見性）。

## 共通原則

### 1. 先收決策，再寫規格

動筆前把這個功能的待決事項全部列出，逐條分成兩類：

| 類別 | 判準 | 處理 |
|------|------|------|
| **機械決策** | 有可查的唯一正解，或專案慣例已定：命名、欄位型別、沿用哪個既有元件、排序預設、錯誤碼格式、檔案位置 | 自己查證後定案，記入決策表（`拍板`＝`SA` 或 `證據`），**不問人** |
| **品味決策** | 多個方案都合理、取捨牽涉業務價值或使用者體驗：範圍要不要含某情境、狀態流程怎麼設計、例外時使用者看到什麼、要不要偏離既有行為 | 一次一題問人，附推薦選項與代價，答完記入決策表（`拍板`＝`PO`，即回答的人，通常就是使用者） |

- 品味決策全部收齊才進撰寫；撰寫中冒出新的品味決策 → 停筆先問，不先寫一版再改。
- 判不出類別時當品味決策處理。
- 需求本身還模糊、連該決定什麼都不清楚 → 先在這裡問清楚（一次一題），收斂後再分類。

### 2. 不確定處標 `[NEEDS CLARIFICATION]`，不猜

- 能查就查（codebase、DB 唯讀查詢、既有規格、票），查不到且能問就問。
- 當下問不到（派出去的 subagent、使用者暫不答）→ 在原處寫 `[NEEDS CLARIFICATION: 具體問題]`，不自行補值。
- 有依據的推導另標 `[推論]` 並寫依據；兩者不混用。
- 寫完前清點：殘留的 `[NEEDS CLARIFICATION` 逐條列給使用者；未清零的規格狀態維持「草稿」，`spec-check` 會判 BLOCKER。

### 3. 技術中立

只寫做什麼、輸入輸出、規則與約束；框架、快取、鎖、佇列等手段留給實作。

## 寫規格

產出 `<spec.dir>/<feature>.md`（`<feature>` 用 kebab-case 短名；目錄裡既有設計文件有命名慣例，例如 `YYYY-MM-DD-<slug>-design`，就照慣例）。範本與自查清單：本 skill 目錄的 `references/lean-template.md`。

1. **定位**：`<spec.dir>/<feature>.md` 已存在 → 視為更新（等同 `--change`）；否則新建。有設計文件（brainstorming 產出）就沿用，不重問已定案的事。
2. **章節**：照範本；專案規則規定的必要章節（AGENTS.md、`.claude/rules/`，例如「ERP 對照」）放在 §6 與 §7 之間、不編號（§7 變更歷史的編號不動），不刪範本章節。
3. **蒐證**：搜既有程式碼與規格找可重用元件、受影響範圍；涉及資料表且有唯讀 DB 工具時查表結構。範圍大時派 `lifecycle:scout` 落檔，主 session 只讀結論。命中 domain 邊界照 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md` 開顧問桌；舊系統移植照 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`。
4. **收決策**：依共通原則 1，列待決事項 → 機械決策自己定 → 品味決策逐題問。
5. **撰寫**：照範本寫；決策寫進 §5 決策表，不另開 `decisions.md`。
6. **自查**：跑範本的品質檢查清單；`[NEEDS CLARIFICATION` 未清零就照原則 2 回報。
7. **CR（`--change` 或檔案已存在）**：in-place 修改受影響段落，**取代不追加**；版本號 +1、§7 加一列，有票號就寫上。需要回覆票時交給 `lifecycle:ticket-reply`。

**下一步**：`lifecycle:spec-check`（規格檢查）就在這一步跑一次；`lifecycle:implement` 的品質閘門見到通過紀錄不重跑。通過後 `lifecycle:ticket-create` 或 `lifecycle:implement`。

## 讀寫既有規格

規格是單一檔：直接讀整份；只改某一章時 `grep -n "^## "` 定位後就地修改，CR 照「寫規格」第 7 步。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 功能描述空白 | 提示輸入，終止 |
| 範本找不到 | 回報範本路徑錯誤，終止 |
| 帶舊參數 `--stage`，或設定檔有舊鍵 `scale` | 回一句「四份文件規格鏈已在 lifecycle 3.0.0 移除，改產一份規格」，照「寫規格」繼續 <!-- allow-legacy --> |
