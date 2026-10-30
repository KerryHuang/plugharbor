---
name: ai-radar
description: 每週掃描近一週最新 AI 情報並產出週報，涵蓋大廠工具規範更新、AI 工程實踐、user 層與當下專案的 agent-system 最佳化建議、plugin 排行與（專案有提供時的）知識庫時效稽核，並對帳採納待辦跨週追蹤。手動觸發。觸發詞：「AI 週報」「查本週 AI 新聞」「AI 情報雷達」「ai-radar」。
argument-hint: "[回溯天數，預設7] [--deep 5]"
disable-model-invocation: true
---

# AI 情報雷達（週掃描）

薄編排：分五區塊掃近一週 AI 情報，彙整成週報落檔，並回頭檢視 user 層與當下專案的
agent system（及專案知識庫）的最佳化／時效機會。跑完後**對帳採納待辦**，讓各區塊的建議跨週
存活、追蹤到落地，不隨單週週報 evaporate。沿用既有引擎，不重造輪子。

## 參數

- **回溯天數**：預設 `7`（近一週）。掃描時排除超出此窗的內容，或明確標記為較舊。
- **`--deep 5`**：區塊 5 改為
  `update-knowledge-base --audit --deep`（L2 既有聲明做全量重驗，而非輪替抽樣；
  專案沒有該 skill 時同樣跳過）。

> 今天日期以使用者環境 / 對話中的當前日期為準，據此換算時間窗。

## 輸出位置

先決定輸出目錄 `<OUT>`，後面所有落檔都寫在這裡：

1. 當下專案的 `CLAUDE.md` 有 `ai-radar-output: <路徑>` → `<OUT>` = 專案根下的該路徑。
2. 沒宣告 → `<OUT>` = `~/.claude/ai-radar/`（只在本機，不進版控）。

週報與 backlog 會寫到專案內部的發現，**不要寫進公開 repo**（例如 user 層設定的版控
repo）；專案要讓週報進版控，就由專案自己宣告 `ai-radar-output`。

## 派工模型（降本）

掃描型區塊（**1B 其他大廠、2 最佳實踐、4 marketplace**）是 web 搜尋＋摘要工
作，**一律以 `subagent_type: general-purpose` 並行派發、並指定 `model: sonnet`**，
不要用主模型（Opus）跑，可省數倍 token。**區塊 3 反查設定**與**主編排／落檔**
留在主執行緒用主模型（需橫向對照 repo 與判斷）。並行掃描 agent 數維持 3–5 個（甜蜜點）。

**區塊 5** 交棒 `update-knowledge-base --audit`，其內部已自帶降本紀律（L1 機械
掃描派 `general-purpose` + `model: sonnet`；L2/L3 判斷留主執行緒），此處不重複派工。

## 流程

### 區塊 1 — 大廠更新與教學
- **Claude Code 官方**：用 WebFetch 抓 `code.claude.com/llms.txt`
  與 skill/rule/hook/script/settings 規範頁，找出近一週的規範或用法變更；對照本
  repo 既有寫法是否落後。
- **其他大廠**（OpenAI / Google / Anthropic / Cursor 等）：派 `general-purpose`
  agent（`model: sonnet`）以 `WebSearch` 掃近一週 changelog / blog / release notes。

### 區塊 2 — 最佳實踐
- 派 `general-purpose` agent（`model: sonnet`）以 `WebSearch` / `WebFetch` 掃
  `references/sources.md` 列的論壇，找軟體工程 / vibe coding + AI 實作的好做法；
  優先近一週、高互動、有具體做法的貼文。

### 區塊 3 — 反查 agent system 最佳化
- 把區塊 1&2 的發現對照現行 agent system，掃描範圍**必含**：
  - **user 層**：`~/.claude/` 的 `CLAUDE.md`、`skills/`、`rules/`、`agents/`、`hooks/`、`settings.json`
  - **當下專案**：`.claude/skills/`、`.claude/rules/`、`.claude/agents/`、`CLAUDE.md`、`.claude/settings.json`
  - 專案 `CLAUDE.md` 有 `ai-radar-extra-scan: <目錄>`（例如自家 plugin 的 skills 目錄）就一併掃；沒宣告就不掃 plugin。
- 改 user 層的檔時，指向它的版控來源（若 `~/.claude` 由某個 repo 安裝而來），不要直接改 `~/.claude`。
- 跨層一致性與時效性健檢交給 `config-doctor`（toolkit plugin 提供；先 `/doctor` 再 `/config-doctor`）；本區塊只做「本週新發現 → 現行設定」的對照。
- 反查重點維度（依本週發現動態調整，至少涵蓋）：
  - **派工 model 紀律**：skill 內文動態派 subagent/Task/Agent 時有無指定
    model；web/機械/摘要類是否該降 sonnet/haiku（agents/*.md 定義檔已 pin
    model，要查的是 skill 內文派工有無覆寫）。
  - **hook 寫法**：有無逗號分隔 matcher（2.1.191 前靜默失效）或依賴 2.1.187
    才修好的檔案級/條件式匹配。
  - **frontmatter / 結構 / 過時做法**：對照官方規範與最佳實踐。
- 輸出**建議 + 具體行動草案**（要改哪個檔、怎麼改），**不自動套用**。要實際
  套用時交棒 `superpowers:writing-skills`。
- 此反查需橫向判斷，留主執行緒主模型；大量逐檔開檔可派 `general-purpose`
  稽核 agent（`model: sonnet`）並給明確檢查清單。

### 區塊 4 — Marketplace / Plugin 排行
- 派 `general-purpose` agent（`model: sonnet`）以 `WebSearch` / `WebFetch` 查最多
  人推薦 / 使用的軟體工程 / vibe coding marketplace 與 plugin；列名稱、簡述、連結、
  為何熱門（星數 / 討論度 / 推薦來源）。

### 區塊 5 — 知識庫時效稽核（條件式）
- **只在當下專案有 `update-knowledge-base` skill 時才跑**（plugin 提供的帶命名空間版本如
  `<plugin>:update-knowledge-base` 也算）；沒有就跳過，並在週報
  區塊 5 註明「本專案無 update-knowledge-base，略過」。
- 向內驗證專案知識庫是否跟現況（codebase / DB / memory）漂移。
- **不自行實作**：交棒 `update-knowledge-base --audit`（沿用其 5 條偵測線與章節
  對照表；區塊 3 看的是 skill/rule 時效，此區塊看的是知識庫內容時效，兩者互補）。
- 該稽核**唯讀**，跑三條線並落出漂移報告，**不改任何知識庫章節**：
  - **L1 新增偵測**：知識庫缺哪些新 schema/表/欄位/客戶/服務/寬表。
  - **L2 既有聲明驗證**：抽樣既有章節的具體聲明回頭核對 DB，標「⚠ 可能失效」。
  - **L3 memory 畢業候選**：`MEMORY.md` 裡該進知識庫卻沒進的耐久事實。
- 漂移報告由該 skill 自行落檔（路徑以它的規定為準）。摘要併入當週週報。
- 要實際套用報告內容時，交棒 `update-knowledge-base`（套用模式，diff 預覽寫入）。

### 採納待辦對帳（跨區塊，最後一步）
- 把區塊 1–5 產出的每條建議 / 行動草案 / 漂移項，對帳進**持久待辦**
  `<OUT>/adoption-backlog.md`——讓建議跨週存活、追蹤到落地，不
  隨單週週報 evaporate。
- 進場先 **triage 評分**（影響 × 可行性 × 契合度）→ 壓低雜訊；**dedup vs backlog**
  （已追蹤 / 已駁回不重複加）；**append 新項**（狀態=待評估）；週報頂端**浮出**
  open 且高分（≥12）的未結待辦提醒處理。
- 新工具 / plugin 類候選，triage 時**多帶一句接入方式草案**（要加哪個 MCP、換哪個
  skill 派工 model…），別停在「知道有這個」。
- 精確規則（評分、dedup、交棒路由、狀態機）→ [references/adoption-backlog.md](references/adoption-backlog.md)。
- **不擅自改既有項狀態**；狀態變更由使用者決定或確認。

## 品質規則

- 每條重要聲明都附**來源連結 + 日期**，並標示可信度：**官方** 或 **社群**。
- 只取回溯窗內的內容；較舊但仍重要者明確標記日期。
- 區塊 3 的行動草案、區塊 5 的漂移報告落檔前先呈現給使用者，不自動改任何檔。

## 落檔

- 依 `references/report-template.md` 彙整。
- **在主執行緒寫檔**，輸出到 `<OUT>/YYYY-MM-DD-ai雷達.md`
  （`YYYY-MM-DD` = 執行當天）。
- **區塊 5**（有跑時）的漂移報告由 `update-knowledge-base --audit` 另外落檔；
  週報只放摘要 + 連結。
- **採納待辦**更新到 `<OUT>/adoption-backlog.md`（append 新項 +
  浮出未結）；週報頂端放「本週新增 N 項 / open 高分 M 項」摘要。
- 落檔後簡述重點；套用時：區塊 3 交棒 `superpowers:writing-skills`、區塊 5 交棒
  `update-knowledge-base`（套用模式，專案有才適用）、其餘依 backlog 交棒路由。

## 來源

預設來源清單見 `references/sources.md`（可增刪）。
