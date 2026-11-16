# lifecycle 拆分第三批「最後接」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 lifecycle 接上 superpowers：專案層 AGENTS.md 標準段落（`install-project.sh --shared` 寫入）、implement 變薄入口＋同格式退路（含計畫審查）、設計文件章節兩條路徑一致並固定有「驗收」一節、spec-check 縮成實作前檢查、after.md 只留驗收對照與回填、user 層 `superpowers.md` 改寫；lifecycle 4.0.0 → 4.1.0。

**Architecture:** 先定「設計文件格式」（章節契約＋驗收格式＋舊章節對照），寫進範本與 AGENTS.md 段落兩處，讓 brainstorming 與退路產同一種文件；再讓讀它的 skill 與共用 references 改讀新章節並相容舊 §2.3／§5／§7；驗收轉案例改由腳本做，行為可測。計畫格式照 superpowers writing-plans，退路照抄同格式。install-project 只在 `--shared` 碰受版控的檔，且遇到異常輸入一律不寫。

**Tech Stack:** Markdown skill、Python 3 unittest（`python3 test_x.py`）、bash（相容 3.2）、JSON。

**Spec:** `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`（第三批＝「分批」第 3 項；內容見「決定／lifecycle」「接點」「與現況衝突」三節）

## Global Constraints

- 工作在 worktree `../plugharbor-l3`（分支 `feat/lifecycle-l3`，從 `origin/main` 03b7ccc 開）；主 checkout 不動（另一個 session 正在主 checkout 改 `docs/feature.md`）。
- 版號：lifecycle **4.1.0**；tickets、discovery、delivery **1.0.1**（共用 references 副本與 tickets 自有檔的對照修正）；backend 若改 README 為 patch。CHANGELOG 正體中文、寫「起因」。用 release-plugin skill 同步三處。
- Task 1–5 **不 commit**；Task 6 e2e 通過後一次 commit（理由：版號規則要求 skill 改動與 CHANGELOG 同 commit，e2e 失敗的修正也落在同一版）。每個 task 結束 `python3 scripts/ci/validate.py` 與該 task 列的測試必須綠。
- 共用副本由 `scripts/ci/shared-copies.json` 管：改 lifecycle canonical 就同步副本（改名對照照該檔），validate 的 `check_shared_copies` 比對。
- 常駐 context 不變胖：skill description 改了不得變長（逐個量字數）；setup 的 home 目錄下的 `rules/superpowers.md` 總字數不得增加。
- 每個 plugin 能單獨安裝：叫用 superpowers、tickets、toolkit 一律「可選＋沒裝的退路」。
- 外洩規則：不寫個人絕對路徑、公司名；`git add` 逐檔；不用 `--no-verify`。
- 不碰：`docs/retrospective/metrics.yml`、`.agents/`、`docs/retrospective/20261113-feedback-handoff/`、`docs/feature.md`（本批的清單變動在主 checkout 由主控做）、`.tmp/ticket-dual-track/`。

### 設計文件格式（Task 1 定，之後各 task 照字面用）

- 開頭：`# <功能>`，下一行 `票號：#n · 狀態：草稿 · yyyy-mm-dd`（沒票寫「無」；舊系統移植再加 ` · 來源：舊系統移植（<分析報告路徑>）`）。
- 章節依序：`## 起因`、`## 目標`（含非目標、反目標）、`## 限制`、`## 做法比較`、`## 決定`、`## 驗收`、`## 留給 builder`；可選 `## 變更紀錄`（文末，一行一筆含票號）。專案規則要求的額外章節放 `## 留給 builder` 之前。這七節即 superpowers「The Written Design」六項＋驗收，兩條路徑都照它。
- `## 決定`：一條一行 `- D-01 <決定>；否決：<選項與原因>（拍板：使用者／顧問／證據／自行決定）`；手段層留置寫 `- TD-01 <約束＋現況＋陷阱>（拍板：待實作）`；移植的偏離候選放 `### 偏離候選（預設不做）` 小節。
- `## 驗收`：`### <id> <標題> [通道]` 起一案，`#### 前置條件`／`#### 步驟`／`#### 預期` 接清單（`acceptance-format.md` 降一級）。
- 舊章節對照（給 references 改寫用）：§2.3→驗收、§5 決策表→決定、§7 變更歷史→變更紀錄、§1 背景→起因、§3 設計／§3.4 邊界→決定（邊界的反例寫進驗收）、§6 風險→限制、表頭「來源｜舊系統移植」→開頭行的「來源：舊系統移植」。讀端一律新舊都認。
- 實作前檢查通過紀錄：開頭行下一行 `> 實作前檢查：✅ YYYY-MM-DD（內容 <8 碼>）`；8 碼＝`grep -v '^> 實作前檢查：' <doc> | shasum | cut -c1-8`。

### 撰寫時自行決定（技術類）

1. 設計文件格式如上：章節名取 superpowers 六項的中文對應（本 repo 既有設計文件同此），通過紀錄由表頭列改為雜湊行（新格式沒有表頭表格；保留「跨 session 不重跑」契約，起因見 `test_skill_contracts.py` 的 S2、S3）。
2. spec-check 保留：待澄清清零（BLOCKER）、驗收一節可測（CRITICAL，用 Task 2 的轉檔腳本＋`validate.py acceptance`）、引用的既有元件／端點／資料表真的存在（CRITICAL）、舊系統移植照 legacy-parity、`--sample` 不動。移除：決策表否決欄、§3.4 五面向、技術中立、「不包含」——屬 brainstorming 建造者檢查；**沒裝 superpowers** 才多跑一項簡版「建造者讀法」（列出會改變做出什麼的未答問題，有就 WARNING）。
3. `--change` 保留為「就地更新既有設計文件、文末 `## 變更紀錄` 加一行」；設計移除的是規格鏈的 CR 變體。
4. AGENTS 段落放 `plugins/lifecycle/templates/agents-md-section.md`，標記 `<!-- plugharbor-lifecycle begin -->`／`<!-- plugharbor-lifecycle end -->`；設計文件目錄寫「`.plugharbor/lifecycle.yml` 的 `spec.dir`（預設 `docs/superpowers/specs/`）」，安裝時不做變數替換。
5. 計畫審查共用 `skills/implement/references/plan-review.md`（兩條路徑都跑，設計文件裁決）：`toolkit:agent-dispatch` 跨家族短問答優先 → 同家全新 subagent → 都沒有就自審標「自審」。必修修完才開工；必修 ≥ 3 時修完再審一輪定點核對（起因：初審 10 項、修訂後仍 3 項）。**實作後的 diff 審查**在退路只做自審（設計文件：退路「不派 subagent、自審」）。
6. `--shared` 宣告 superpowers：專案 `.claude/settings.json` 的 `enabledPlugins` 合併 `"superpowers@claude-plugins-official": true`；乾淨機器上是否提示安裝仍屬設計文件「未驗證」。
7. agent 去留：`lifecycle:tester` 保留（backend、frontend、workspace 的 skill 仍引用）；`lifecycle:debugger` 移除後沒有 skill 引用 → 依設計去留規則刪除，同步 lifecycle README、backend README。
8. 驗收轉案例改用腳本 `plugins/lifecycle/skills/qa-verify/scripts/spec_to_cases.py`（原本由模型照文字規則轉，無法驗）；spec-to-acceptance.md 留規則說明與「不是案例格式」的擬稿流程。

## Review Focus

1. **舊規格仍可用**：舊範本規格（§2.3 降兩級、表頭 `| 規格檢查 |`、表頭來源列）轉案例、過 spec-check、觸發 legacy-parity → Task 2 測舊格式 fixture。
2. **AGENTS.md 標記異常**：只有 begin、只有 end、兩組、順序顛倒 → 拒絕寫入、印 `FAIL:`、原檔 bytes 不變 → Task 4 (h)。
3. **settings.json 壞掉或型別不符**（非 JSON、`enabledPlugins` 不是物件）→ 保留原檔、印 `FAIL:` → Task 4 (e)。
4. **CRLF 與標記外內容**：AGENTS.md 為 CRLF、標記外有使用者內容 → 標記外 bytes 不變 → Task 4 (c)。
5. **雜湊行為**：正文沒改可跳過、只改紀錄行仍跳過、正文改一字必須重跑 → Task 3 測試。

---

## 開工前（主控做，已完成）

- [x] 主 checkout `docs/feature.md` 第 59 行 L3 改 🚧（未 commit，與另一個 session 的未提交編輯同檔）；#36 label `stage:in-progress`、看板 In Progress。reconcile 的 5 項差異屬那個 session 新加、尚未開票的 demo-video 節。

### Task 1：設計文件格式、spec skill、AGENTS 段落

**Files:**
- Rewrite: `plugins/lifecycle/skills/spec/references/lean-template.md`
- Modify: `plugins/lifecycle/skills/spec/SKILL.md`
- Create: `plugins/lifecycle/templates/agents-md-section.md`
- Test: `plugins/lifecycle/scripts/test_skill_contracts.py`

**Interfaces:**
- Produces: 「設計文件格式」一節的全部字面值落在範本；AGENTS 段落檔路徑與兩個標記。

- [ ] **Step 1：測試（先紅）**，只碰本 task 的檔：
  - `test_spec_check_pass_record_is_persisted_and_read`：拿掉對範本的 `| 規格檢查 |` 斷言（spec-check、implement 兩行留給 Task 2、3 改）。
  - `test_template_sections_align_superpowers`：範本依序含七個章節標題、含 `票號：`、`### AC-01`、`#### 步驟`、`#### 預期`、`（拍板：`、`TD-01`；不含 `##### `、`§2.3`、`| 拍板 |`。
  - `test_agents_section_markers_and_contract`：段落檔首行為 begin 標記、末行為 end 標記；含七個章節名、`lifecycle:implement`、`docs/superpowers/plans/`、`計畫審查`、`### `、`#### 預期`、`lifecycle:release`、`同步票`。
  - `test_spec_routes_by_superpowers`：spec SKILL.md 含 `superpowers:brainstorming`、「一次一題」、`AskUserQuestion`、`lean-template.md`。
  - 既有測試引用舊範本字樣者（`[api]`、專案必要章節位置 `§6 與 §7 之間`）改成新格式字樣（`[api]` 仍在範本；必要章節「放 `## 留給 builder` 之前」），不刪測試意圖。
- [ ] **Step 2：跑** `python3 plugins/lifecycle/scripts/test_skill_contracts.py` → 新測試 FAIL。
- [ ] **Step 3：改寫範本**照「設計文件格式」；`## 驗收` 放 AC-01 正例、AC-02 反例（沿用「備註 200 字」例子），保留 `[api]` 案例要寫明由哪個整合測試涵蓋；`## 做法比較` 要兩三個做法與選擇理由；自查清單對新章節。
- [ ] **Step 4：改 spec SKILL.md**：
  - 可用 skill 有 `superpowers:brainstorming` → 交給它，交代：照本 skill 的 `references/lean-template.md` 章節與驗收格式寫（AGENTS 段落有同一份契約）、開頭票號行、位置 `<spec.dir>/YYYY-MM-DD-<slug>-design.md`。lifecycle 自己只做 Step 0 的 `spec.dir` 設定。
  - 沒裝 → 退路：照範本自己寫；把決策樹每個分支解完，一次一題、用 AskUserQuestion、推薦選項放第一（沒有該工具就文字問）；機械決策自查不問（保留「機械／品味」分類表，拍板寫法改成「設計文件格式」的 `（拍板：…）`）。
  - `--change` 照自行決定 3；刪 `get scale` 指令與段落（錯誤處理表留一列）；`§6 與 §7 之間`、`§5 決策表`、`§7` 改新章節。
  - description 不提 §2.3、不得變長（`python3 -c` 量新舊字數）。
- [ ] **Step 5：寫 AGENTS 段落**（≤ 30 行）：標記；設計文件位置；**設計文件章節契約**（七節名稱一行＋開頭票號行）；精簡驗收格式（3–6 行示意）；計畫位置 `docs/superpowers/plans/`（進版控）；計畫寫完先審（跨家族優先、必修修完才開工；裝了 lifecycle 照 `lifecycle:implement`）；「開始實作」以 `lifecycle:implement` 為入口；收尾接功能清單打勾＋同步票；Git Flow 專案發版交 `lifecycle:release`。
- [ ] **Step 6：跑** contract 測試 PASS、validate.py ✓。

### Task 2：驗收轉案例腳本、spec-check 縮減、共用 references 改讀新章節

**Files:**
- Create: `plugins/lifecycle/skills/qa-verify/scripts/spec_to_cases.py`、`plugins/lifecycle/skills/qa-verify/scripts/test_spec_to_cases.py`
- Modify: `plugins/lifecycle/skills/qa-verify/references/spec-to-acceptance.md`、`plugins/lifecycle/skills/qa-verify/SKILL.md:34`、`plugins/lifecycle/skills/qa-verify/references/batch-mode.md:3,51,52,71`
- Modify: `plugins/lifecycle/skills/spec-check/SKILL.md`
- Modify（canonical＋全部副本）：`plugins/lifecycle/references/legacy-parity.md:31-50`、`shared-preludes.md:37,43`、`shared-preludes-details.md:85-112`、`consultant-desk.md:153`、`analysis-rigor.md:47`、`config.md:17`（「規格與 `LEARNINGS.md` 的目錄」→「設計文件的目錄」）
- Modify：`plugins/tickets/skills/ticket-reply/SKILL.md:53-54`、`plugins/tickets/references/pipeline.md:9,23,32,71`
- Test: `plugins/lifecycle/scripts/test_skill_contracts.py`

**Interfaces:**
- Produces: `spec_to_cases.py <設計文件> <輸出檔>` → 寫出 `acceptance-format.md` 格式的案例檔，stdout 印案例數；exit 0 成功、2 用法錯、4 缺欄或格式不符（stderr 逐條「<id>：缺什麼」）。認 `## 驗收`（案例 `###`、欄位 `####`）與舊 `### 2.3`（案例 `####`、欄位 `#####`），兩者都沒有 → exit 4「找不到驗收一節」。Task 3 的 after.md、spec-check 都叫它。

- [ ] **Step 1：測試（先紅）** `test_spec_to_cases.py`：
  - `test_new_format_roundtrip`：新格式 fixture 兩案（一案有前置條件、一案 `[api]`）→ 輸出 `## AC-01 … [ui]`、`### 步驟`…；案例數 2、id、通道、步驟與預期逐條相同；輸出交 `validate.py acceptance` exit 0。
  - `test_legacy_23_roundtrip`：舊 §2.3 fixture 同樣斷言。
  - `test_missing_expected_exit4`：一案缺 `#### 預期` → exit 4、stderr 含 `AC-02：缺 預期`、不寫輸出檔。
  - `test_placeholder_and_non_ascii_id_exit4`：預期是 `{…}`、id 含中文 → exit 4。
  - `test_no_acceptance_section_exit4`。
  - `test_skill_contracts.py` 加 `test_legacy_parity_marker_both_formats`：legacy-parity、spec-check、spec 三檔的觸發句都同時含「來源：舊系統移植」與「來源｜舊系統移植」，範本開頭行說明含 `來源：舊系統移植`（模型是否真的觸發屬行為，靜態測試只到觸發句，回報標「未驗證」）。`test_shared_refs_use_new_sections`：shared-preludes、consultant-desk、analysis-rigor、ticket-reply 不含 `§5 決策表`、`§7 變更` 這類只有舊名的寫法（允許「（舊範本 §5）」括號別名）。
- [ ] **Step 2：跑** → FAIL。
- [ ] **Step 3：實作 `spec_to_cases.py`**（標準庫，只用 `re`、`sys`、`pathlib`）；規則照現行 spec-to-acceptance.md（原樣轉、不改寫、缺欄就停）。
- [ ] **Step 4：改 spec-to-acceptance.md** 成「跑腳本＋exit 4 交使用者補文件＋`.tmp/` 未忽略提醒＋不是案例格式的擬稿流程」；qa-verify SKILL.md:34 規格模式判斷加「檔內有 `## 驗收`」；batch-mode 四處 §2.3 改「驗收一節」。
- [ ] **Step 5：改 spec-check** 照自行決定 2；第 2 項改「跑 `spec_to_cases.py` 存 `.tmp/qa/<feature>.md` 再跑 `validate.py acceptance`」；通過紀錄照「設計文件格式」（寫雜湊行；刪「表頭版本 +1」）；Step 0 多找 `<spec.dir>/*<feature>*-design.md`；移植判斷新舊標記都認。description 不提 §2.3、不變長。`test_any_edit_after_spec_check_bumps_version` 刪除（意圖由 Task 3 雜湊測試接手）；`test_spec_check_says_how_to_validate_cases`（第 122 行，斷言「升兩級」）改為斷言 spec-check 含 `spec_to_cases.py` 與 `validate.py acceptance`；`test_spec_check_pass_record_is_persisted_and_read` 的 spec-check 斷言改為含 `> 實作前檢查：`。
- [ ] **Step 6：改共用 references 與 tickets 檔**照「舊章節對照」，新名在前、舊名括號；legacy-parity 的標記段新舊都認、§3／§5／§6／§3.4 落點改新章節（偏離候選→`## 決定` 的 `### 偏離候選（預設不做）`）；同步全部副本。
- [ ] **Step 7：跑** `test_spec_to_cases.py`、`test_validate.py`、contract、validate.py → 綠。

### Task 3：implement 薄入口、同格式退路、計畫審查、after.md 精簡、移除 debugger

**Files:**
- Modify: `plugins/lifecycle/skills/implement/SKILL.md`
- Rewrite: `plugins/lifecycle/skills/implement/references/fallback.md`、`plugins/lifecycle/skills/implement/references/after.md`
- Create: `plugins/lifecycle/skills/implement/references/plan-review.md`
- Delete: `plugins/lifecycle/agents/debugger.md`；Modify: `plugins/lifecycle/README.md`、`plugins/backend/README.md`、根 `README.md` agents 表（有列才改）
- Test: `plugins/lifecycle/scripts/test_skill_contracts.py`

**Interfaces:**
- Consumes: 雜湊指令與紀錄行（設計文件格式）、`spec_to_cases.py`（Task 2）。

- [ ] **Step 1：測試（先紅）**：
  - `test_pass_record_hash_behavior`：從 implement SKILL.md 抓出 `grep -v '^> 實作前檢查：'` 開頭的那條指令（斷言它與 spec-check 裡的逐字相同），在暫存檔上跑：原文 → h1；只改紀錄行日期 → 仍 h1；正文改一字 → ≠ h1。
  - `test_implement_has_no_learnings`：implement SKILL.md、after.md、fallback.md 不含 `LEARNINGS`；`test_spec_check_pass_record_is_persisted_and_read` 的 implement 斷言改為含 `> 實作前檢查：`。
  - `test_after_only_acceptance_and_backfill`：after.md 的 `## ` 標題恰兩個，含「驗收」「回填」；含 `spec_to_cases.py`、`同步票`、`未設 ticket.tool`；不含「整合測試」、`lifecycle:debugger`。
  - `test_fallback_plan_same_format`：fallback.md 含 `docs/superpowers/plans/`、`**Goal:**`、`**Architecture:**`、`**Tech Stack:**`、`**Spec:**`、`## Global Constraints`、`## Review Focus`、`**Interfaces:**`、`- [ ]`、`自審`；不含 `lifecycle:reviewer`（實作後 diff 審查不派 subagent）。
  - `test_both_paths_run_plan_review`：implement SKILL.md 與 fallback.md 都含 `plan-review.md`；plan-review.md 含 `toolkit:agent-dispatch`、`自審`、`必修`、`≥ 3`。
  - `test_implement_clean_tree_rule_is_consistent` 依新字樣調整。
- [ ] **Step 2：跑** → FAIL。
- [ ] **Step 3：implement SKILL.md**：刪 LEARNINGS；分支檢查保留；定位設計文件（含 `*-design.md`）；實作前檢查＝重算雜湊，與紀錄行相同就跳過，否則跑 `lifecycle:spec-check`（最多 3 輪）；有 `superpowers:writing-plans` → 叫用並要求計畫 **Spec** 欄寫設計文件路徑、最後一個 task 是 after.md（絕對路徑）；計畫存好、執行前照 `references/plan-review.md`；執行與收尾交 superpowers，不自動 merge。沒裝 → fallback.md。description 拿掉「讀前次經驗」「整合測試、寫 LEARNINGS.md」，必須比現在短。
- [ ] **Step 4：fallback.md**：計畫寫 `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`（進版控），貼 writing-plans 的表頭骨架與一個 task 骨架（不貼解說）；→ plan-review.md → 逐 task TDD（主控自己做：失敗測試、看它紅、實作、綠、勾選；連修 3 次不過就停下問）→ 全部完成後**自審**整份 diff、標「自審」→ 最後 task 跑 after.md → 逐檔 commit、問使用者 push／PR，不 merge。
- [ ] **Step 5：after.md** 兩節：
  - `## 1. 對照驗收`：跑 `spec_to_cases.py`（exit 4 → 回報缺欄、本 task 不算完成）；逐案對到證據（測試名或指令輸出）寫 `.tmp/implement/<feature>/acceptance-trace.md`；`[ui]` 案例建議收尾後跑 `lifecycle:qa-verify`；有案例沒證據 → 不算完成，回報主控。無設計文件對照計畫 Goal，標「無設計文件」。
  - `## 2. 回填`：`docs/feature.md` 打勾＋跑腳本更新數字（照 `references/feature-checklist.md`）；有 `ticket.tool` 照同檔「同步票」叫 `tickets:ticket-ops`（沒裝 tickets → 只勾清單、回報一行）；沒設 → 回報「未設 ticket.tool，略過同步票」。逐檔 `git add`、commit。
  - 回報：驗收對照、清單、同步票分開宣稱。
- [ ] **Step 6：plan-review.md**（≤ 40 行）照自行決定 5；審查提示從 `toolkit:agent-dispatch` 的 `references/review-prompt.md` 精神寫（自足、分必修／建議、每條必修指出 task 與反例）；結果落 `.tmp/implement/<feature>/plan-review-<n>.md`。
- [ ] **Step 7：刪 debugger** 並同步 README；`git grep -n "lifecycle:debugger\|agents/debugger" -- plugins setup README.md ':!*CHANGELOG.md'` 為空。
- [ ] **Step 8：跑** contract、validate.py → 綠；SKILL.md 皆 < 300 行。

### Task 4：install-project `--shared` 寫入 AGENTS 段落與宣告 superpowers

**Files:**
- Modify: `setup/install-project.sh`（Claude Code 區塊之後、pi 區塊之前加「專案層接點」一段；邏輯放 `$PY` 內嵌腳本或 `setup/lib/project_hooks.py`，擇一，超過 40 行就獨立檔）
- Modify: `setup/tests/install-project.sh`（新增第 13 節）、`setup/README.md`（`--shared` 說明加一句）
- Consumes: `plugins/lifecycle/templates/agents-md-section.md` 與兩個標記（Task 1）。

- [ ] **Step 1：測試（先紅）** 第 13 節，各用 `newproj`；凡「不變」都用 `cmp` 比原檔副本：
  - (a) local 模式裝 lifecycle：不建 `AGENTS.md`、`CLAUDE.md`；`.claude/settings.json` 不含 `superpowers@claude-plugins-official`。
  - (b) `--shared` 裝 lifecycle、無 AGENTS.md → 建出，內容＝段落檔全文；輸出 `OK:   AGENTS.md lifecycle 段落`；重跑 → 內容不變、輸出 `UP-TO-DATE: AGENTS.md lifecycle 段落`。
  - (c) AGENTS.md（CRLF）有使用者內容＋舊段落 → 標記內＝段落檔，標記外前後 bytes 不變；無標記的 AGENTS.md → 段落附檔尾、前空一行，原內容 bytes 不變。
  - (d) CLAUDE.md 存在且無 `@AGENTS.md` → 檔尾補一行；已有 `@AGENTS.md` 或 `@./AGENTS.md` → 不變；無 CLAUDE.md → 不建。
  - (e) settings.json：無 → 建出含 `enabledPlugins` 宣告；有其他鍵（`permissions`、`hooks`、`extraKnownMarketplaces`，以及 CLI 已寫入的 `enabledPlugins.lifecycle@plugharbor`——接點段在 Claude Code 區塊之後跑，CLI 的寫入先於合併）→ 全部保留且宣告加入；已設 false → 不變、印 `SKIP: superpowers 已在專案停用`；非 JSON 或 `enabledPlugins` 不是物件 → 不變、印 `FAIL:`、整體 exit 1。
  - (f) `--check --shared`：分別造「段落缺」「段落正確但 CLAUDE 引用缺」「只缺 superpowers 宣告」三種 → 各報對應 `MISSING:`／`DIFF:`、三檔不變、exit 3。
  - (g) `--shared` 只裝 ui-ux → 不建 AGENTS.md、不補 CLAUDE 引用、settings.json 不含 superpowers 宣告（既有 CLI 對 settings 的寫入不在本節斷言範圍）。
  - (h) AGENTS.md 標記異常（只有 begin、只有 end、兩組、end 在 begin 前）→ 不變、印 `FAIL: AGENTS.md lifecycle 標記不成對`、exit 1。
- [ ] **Step 2：跑** `bash setup/tests/install-project.sh` → 第 13 節 FAIL。
- [ ] **Step 3：實作**：`SHARED=1` 且 `PLUGINS` 含 lifecycle 才跑；檔案一律二進位讀寫（保留 CRLF 與標記外 bytes）；沒有 `$PY` 印 `WARN:` 跳過不算失敗；寫入失敗類計入 `FAILS`；`--check` 只 `note_diff`。輸出前綴沿用既有。
- [ ] **Step 4：跑** `for t in setup/tests/*.sh; do bash "$t" || echo "FAIL $t"; done` → 無 FAIL。

### Task 5：user 層規則、殘留掃描、版號、總驗證（不 commit）

**Files:**
- Modify: `setup 的 home 目錄下 rules/superpowers.md 第 7 行`
- Modify: `plugins/workspace/skills/quality-check/SKILL.md:141`（確認仍正確；要改才改並 bump workspace patch）
- Modify: CHANGELOG、`plugin.json`、`.claude-plugin/marketplace.json`、根 `README.md` 版本欄（lifecycle、tickets、discovery、delivery，backend 若有改）

- [ ] **Step 1：superpowers.md 第 7 行**改為（不得比現在 122 字長）：`- 裝了 lifecycle 時：「開始實作」走 \`lifecycle:implement\`（實作前檢查、計畫審查、收尾回填）；專案 AGENTS.md 有 lifecycle 段落就照它。`；第 9 行不動；量總字數 ≤ 原值。
- [ ] **Step 2：殘留掃描**：`git grep -nE "LEARNINGS|§2\.3|\| 規格檢查 \||讀經驗|規格閘門|§[1-7]|拍板|lifecycle:debugger" -- plugins/lifecycle plugins/tickets plugins/discovery plugins/delivery plugins/backend setup README.md docs/agent-parity.md ':!*CHANGELOG.md'`，逐筆分類：指向設計文件舊章節或舊拍板欄的必須已改（或為「（舊範本 §n）」括號別名、spec_to_cases 的舊格式支援）；指向別的文件自己的章節（如 meeting-minutes 的 §2A、SKILL.md §2）與一般用語「拍板」不算。分類結果寫進回報。
- [ ] **Step 3：版號**：release-plugin 同步；lifecycle CHANGELOG 4.1.0 列：設計文件新章節與驗收一節（兩條路徑同格式）、spec 交 brainstorming、spec-check 縮減（通過紀錄改雜湊行）、驗收轉案例腳本、implement 變薄＋同格式退路＋計畫審查、after.md 兩節、AGENTS 段落與 `--shared` 寫入、LEARNINGS 移除（舊檔留著不讀，可刪）、debugger agent 移除；起因寫設計文件「起因」與第三批。
- [ ] **Step 4：總驗證**：validate.py ✓；`for t in $(git ls-files 'plugins/**/test_*.py'); do python3 "$t" || echo "FAIL $t"; done`（新檔未追蹤，另跑 `test_spec_to_cases.py`）無 FAIL；`node --test $(git ls-files 'plugins/**/*.test.mjs')` 過；toolkit hook 測試照 `.github/workflows/validate.yml` 的指令跑；setup 測試過。逐項記指令與結果。

### Task 6：e2e、commit、收尾（主控做）

- [ ] **Step 1：準備 scratch repo**（scratchpad 下，git init）：`add.py`（空函式）、`docs/feature.md` 一項 `📋 add 函式 #<測試票>`、`.plugharbor/lifecycle.yml` 的 `ticket:` 區塊整段照本 repo `.plugharbor/lifecycle.yml`（含 `states`，不含 `project`——測試票不進看板）。**對外動作先問使用者**：A、B 各建一張 `[測試] L3 e2e A／B` 票，掛 `test` 與 `stage:todo`（reconcile 預設排除 test）。使用者不同意 → e2e 不算通過，停下問要不要改成不驗同步票，不往 commit 走。
- [ ] **Step 2：(A) 裝 superpowers**：用 stub PATH 跑 `install-project.sh --shared <scratch> lifecycle`（只驗它寫出 AGENTS.md 段落與 settings 宣告，不真的裝 plugin），再在 scratch 目錄 `claude -p --model sonnet --output-format stream-json --verbose --plugin-dir <worktree 絕對路徑>/plugins/lifecycle --plugin-dir <worktree 絕對路徑>/plugins/tickets`：先「寫 add 的設計文件，不用問我，照推薦」，再「開始實作 add」。從 stream-json 的 `tool_use`（name=Skill）核對實際呼叫：`superpowers:brainstorming`、`lifecycle:implement`、`superpowers:writing-plans`；**`lifecycle:spec-check` 有被呼叫**且設計文件出現 `> 實作前檢查：` 行；計畫在 `docs/superpowers/plans/`、有 `plan-review-1.md`、設計文件七章節、清單打勾、測試票 A 變 closed。superpowers 來自本機 user 層已裝的那份；「乾淨機器只靠專案設定被提示安裝」維持設計文件的「未驗證」。
- [ ] **Step 3：(B) 沒裝**：另一份 scratch，`.claude/settings.json` 設 `"superpowers@claude-plugins-official": false`，同樣兩句，但兩句之間由主控用設計文件格式的雜湊指令算好、手動寫入正確的 `> 實作前檢查：` 行。核對：**沒有** `lifecycle:spec-check` 呼叫（雜湊相同就跳過）；stream-json 沒有 `superpowers:` Skill 呼叫、走 fallback、設計文件章節與 (A) 相同（`grep '^## '` 比對）、計畫表頭欄位與 (A) 相同、有 `plan-review-1.md`、實作後標「自審」、測試票 B 變 closed。
- [ ] **Step 4**：任一不過 → systematic-debugging 修 → 回 Task 5 Step 4 重驗 → 重跑該情境。
- [ ] **Step 5：commit**：`git status --short` 逐檔 add（含本計畫檔），`git commit -m "feat(lifecycle): 第三批最後接——AGENTS.md 段落、implement 薄入口與計畫審查、設計文件驗收一節"`，pre-commit 過。關閉測試票、刪 scratch。
- [ ] **Step 6：收尾**：問使用者是否併進本機 main；使用者試用後才 push。push 後在主 checkout 把 L3 改 `[x]`（只 add 那一行所在的 feature.md 前先確認另一個 session 已 commit，否則協調），#36 設 done、看板 Done，reconcile 中本批相關項差異 0，commit＋push 該清單變更。
