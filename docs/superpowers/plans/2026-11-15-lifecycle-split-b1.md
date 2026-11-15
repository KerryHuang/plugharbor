# lifecycle 簡化第一批「先刪」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拿掉 lifecycle 的四份文件規格鏈（FRD／SAD／BFS／FFS）與連帶 skill、agent、範本、`scale` 設定，install-project 不再停用 superpowers；lifecycle 2.12.1 → 3.0.0。

**Architecture:** 先寫一支「規格鏈殘留」守門測試（紅），再分塊刪改到它轉綠；以 `validate.py`（交互引用不得斷）與守門測試的「孤兒檔」檢查決定哪些共用 references／templates 該刪。只刪不加新行為，唯一的行為改動是 qa-verify 的案例來源改為 lean 規格 §2.3、ticket-create 只開一張票。

**Tech Stack:** Markdown skill 文件、Python 3 unittest（plugin 腳本測試，直接 `python3 test_x.py` 執行）、bash（setup 腳本與其測試）。

**Spec:** `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`（第一批＝「分批」一節第 1 項；相關決定見「決定」「與現況衝突」兩節）

## Global Constraints

- 工作在 worktree `../plugharbor-lifecycle-b1`（分支 `feat/lifecycle-b1`），不在 main checkout 動。
- 版號：lifecycle 3.0.0（BREAKING）；同一個 commit 內同步 `plugins/lifecycle/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、根 `README.md` 版本欄、`plugins/lifecycle/CHANGELOG.md` 最上方 `## [3.0.0] - 2026-11-15`（正體中文，寫明起因）。用 release-plugin skill。
- 改到 `skills/`、`agents/`、`references/`、`templates/` 的 commit 都要帶版號同步——本計畫只在最後一個 task bump 一次，前面的 task **不 commit**，最後一次 commit 全部（例外核准：避免 3.0.0 拆成多個中間版號；CHANGELOG 一條涵蓋全部）。
- 外洩規則：不寫個人絕對路徑、公司名、小孩姓名；commit 前 `python3 scripts/ci/validate.py` 必須 `✓`。
- `git add` 逐檔指名，不用 `-A`／`.`；不用 `--no-verify`。
- 不碰第二、三批的範圍：不搬 skill 到新 plugin、不改 implement、不寫 AGENTS.md 段落、不改 user 層 `superpowers.md`。
- `architect`、`developer` agent 保留（backend、frontend、workspace 有可選引用）。

## Review Focus

1. 刪掉的 references 仍被別處（含其他 plugin、`setup/`、`docs/`）引用 → validate.py 抓得到 plugin 內的，跨 plugin 的要 Task 7 的 `rg` 驗。
2. 既有專案 `.plugharbor/lifecycle.yml` 仍有 `scale: full` → 應印一行提示並照 lean 跑，不得報錯或靜默走舊路（Task 5 測試）。
3. `spec --stage frd` 等舊參數被呼叫 → 應回「已移除，改用 lean」而不是找不到檔案的錯（Task 3 的 SKILL 錯誤處理表）。
4. qa-verify 收到 lean 規格路徑而非案例檔 → 從 §2.3 轉案例；§2.3 不符格式時停下說明，不硬猜（Task 6）。
5. install-project 在已被舊版停用 superpowers 的專案重跑 → 不再寫停用，也不擅自改回（只在 CHANGELOG 說明手動恢復），Task 8 測試兩種情境。

---

### Task 1：守門測試（紅）

**Files:**
- Create: `plugins/lifecycle/scripts/test_no_spec_chain.py`

**Interfaces:**
- Produces: 測試類 `NoSpecChain`，後續每個 task 結束都跑它看剩幾項紅。

- [ ] **Step 1：寫測試**（unittest，plugin 根＝`Path(__file__).resolve().parents[1]`）

```python
REMOVED_SKILLS = ["spec-chain", "explore", "consolidate-docs", "write-doc", "dev-feedback"]
BANNED = [r"lifecycle:(explore|spec-chain|consolidate-docs|write-doc|dev-feedback)\b",
          r"scale:\s*full", r"--stage\s+(frd|sad|bfs|ffs|index)",
          r"\b(FRD|SAD|BFS|FFS)\b"]
# 掃描範圍：skills/ agents/ references/ templates/ README.md 下的 .md .py .json；略過 CHANGELOG.md 與本測試檔
def test_removed_skill_dirs_absent(self): ...   # 5 個目錄都不存在
def test_no_banned_tokens(self): ...            # 失敗訊息列「檔:行: 命中」
def test_no_orphan_files(self): ...             # references/、templates/、skills/*/references/ 下每個檔的檔名（不含副檔名）至少出現在 plugin 內另一個檔
def test_spec_writer_agent_removed(self): ...   # agents/spec-writer.md 不存在
def test_config_has_no_scale_default(self): ... # import scripts/config.py，"scale" not in DEFAULTS
```

`test_no_banned_tokens` 的例外：行內含 `allow-legacy` 字樣就跳過（Task 3、Task 4 錯誤處理表的「舊參數已移除」列用 `<!-- allow-legacy -->` 行尾註記）。

- [ ] **Step 2：跑，確認紅**

Run: `python3 plugins/lifecycle/scripts/test_no_spec_chain.py`
Expected: 5 個測試全 FAIL（目錄存在、命中數百、孤兒 0 但其餘紅、spec-writer 存在、DEFAULTS 有 scale）。`test_no_orphan_files` 現在可能是綠的——記下來，刪檔後它才有意義。

### Task 2：刪 5 個 skill，改轉交

**Files:**
- Delete: `plugins/lifecycle/skills/{spec-chain,explore,consolidate-docs,write-doc,dev-feedback}/`（`git rm -r`）
- Modify: `skills/spec/SKILL.md:59,76,102`、`skills/ticket-create/SKILL.md:58`、`skills/triage/references/ticket-flow.md:66,110`、`skills/survey-existing-system/SKILL.md:48`、`skills/qa-verify/references/batch-mode.md:101-103`、`references/doc-boundaries.md:157`

- [ ] **Step 1：刪目錄、改引用**
  - 「先跑 `lifecycle:explore`」一律改成「需求還模糊就在 `lifecycle:spec` 開頭先問清楚（一次一題）」；triage 的起點選項刪掉 explore 那一個。
  - qa-verify batch-mode 與 doc-boundaries 的 consolidate-docs 整段刪掉（lean 規格 in-place 修改，不產生票號後綴檔）。
  - survey-existing-system 下一步改指 `lifecycle:spec`。
- [ ] **Step 2：跑守門測試**：`test_removed_skill_dirs_absent` 轉綠；`rg -n 'lifecycle:(explore|spec-chain|consolidate-docs|write-doc|dev-feedback)' plugins/lifecycle --glob '!CHANGELOG.md'` 只剩 `references/pipeline.md`（Task 7 處理）。

### Task 3：spec 只留 lean

**Files:**
- Modify: `plugins/lifecycle/skills/spec/SKILL.md`（刪「full：分層規格」一節與 Step 0 表中 full 兩列、`--stage` 參數只留 `index` 是否保留見下、`--change` 說明只留 lean）
- Delete: `skills/spec/references/{frd,sad,bfs,ffs,stages}/`、`templates/{frd,sad,bfs,ffs,cr-frd,cr-bfs,cr-ffs}.md`、`templates/examples/`、`agents/spec-writer.md`
- Modify: `skills/spec/references/lean-template.md`（標題的「`scale: lean`」字樣拿掉；§2.3 驗收標準改成 qa-verify `acceptance-format.md` 的 markdown 案例格式，附一個兩條案例的範例）

- [ ] **Step 1：`--stage index` 與 SPEC-INDEX**：`references/index/spec-index-format.md` 只服務 full 的功能目錄 → 一併刪，`--stage` 參數整個移除；「讀寫既有規格」一節改為直接讀 lean 單檔。
- [ ] **Step 2：錯誤處理表加一列**：「帶 `--stage frd|sad|bfs|ffs` 或設定 `scale: full`」→ 回「四份文件規格鏈已在 lifecycle 3.0.0 移除，改產一份 lean 規格」並照 lean 繼續。該列行尾加 `<!-- allow-legacy -->`（守門測試放行用）。
- [ ] **Step 3：跑** `python3 scripts/ci/validate.py`（repo 根）— 交互引用斷掉的地方逐一修到 `✓`；斷掉的引用若在要刪的檔裡，刪那個檔。
- [ ] **Step 4：跑守門測試**：`test_spec_writer_agent_removed` 綠；`test_no_banned_tokens` 的命中只剩 spec-check、references、qa-verify 相關檔。

### Task 4：spec-check 只留 lean 檢查＋sample

**Files:**
- Modify: `plugins/lifecycle/skills/spec-check/SKILL.md`（刪 Step 0 的 full 判斷、verify 模式、readiness 模式；lean 規格檢查成為預設；sample 保留；錯誤處理表刪 verify／readiness 相關列；description 與 triggers 同步）
- Delete: `skills/spec-check/references/{modes/verify.md,modes/readiness.md,verify/,readiness/}`、`skills/spec-check/scripts/{check-decision-propagation.py,test_check_decision_propagation.py}`

- [ ] **Step 1：改 SKILL.md、刪檔**。lean 檢查表第 2 項改為「§2.3 每條驗收案例符合 `acceptance-format.md`（qa-verify）」，等級 CRITICAL。
- [ ] **Step 2：`--readiness`／`--quick`／`--cross`／`--recheck` 等舊旗標**：錯誤處理表一列「舊旗標已移除，照 lean 檢查跑」，行尾 `<!-- allow-legacy -->`。
- [ ] **Step 3：跑 validate.py 修到 `✓`；跑守門測試看剩餘命中。**

### Task 5：拿掉 `scale` 設定

**Files:**
- Modify: `plugins/lifecycle/scripts/config.py:20`、`plugins/lifecycle/scripts/test_config.py`、`plugins/lifecycle/references/config.md`、`plugins/lifecycle/skills/ticket-create/SKILL.md:22-34`

**Interfaces:**
- Produces: `config.py get scale` → 印到 stderr `scale 已在 lifecycle 3.0.0 移除，一律 lean` 並 exit 0、stdout 印 `lean`（舊呼叫端不壞）；`DEFAULTS = {"spec.dir": "docs/specs"}`。

- [ ] **Step 1：寫失敗測試**（`test_config.py` 新增）

```python
def test_scale_removed_prints_notice_and_lean(self):
    # 設定檔寫 scale: full；跑 config.py get scale
    # assert returncode == 0, stdout.strip() == "lean", "已在 lifecycle 3.0.0 移除" in stderr
def test_defaults_without_scale(self):
    # assert "scale" not in config.DEFAULTS
```

刪掉既有測試裡斷言 `scale` 預設為 `lean`、或 `delivery-flow.yml` 只有舊檔時 exit 3 的案例（照實際內容判斷；退出碼 3 的舊檔名偵測若與 scale 無關就保留）。

- [ ] **Step 2：跑，確認紅**：`python3 plugins/lifecycle/scripts/test_config.py` → 2 個新測試 FAIL。
- [ ] **Step 3：改 config.py**：`get scale` 特例如上；DEFAULTS 拿掉 scale。
- [ ] **Step 4：跑綠**：同上指令全 PASS；守門測試 `test_config_has_no_scale_default` 綠。
- [ ] **Step 5：ticket-create**：「規模」一節改為：預設一張票（Feature 或 Bug 範本）；使用者明說要拆，或功能清單該節已有父票（行尾 `#n`）時，才建子票並掛父票。刪 PM／SA／QA／Dev 角色子票表與其範本段落（`references/` 下相關範本照 orphan 規則刪）。`config.md` 刪 `scale` 鍵說明，留一行「3.0.0 移除」。

### Task 6：qa-verify 案例改從 lean 規格 §2.3

**Files:**
- Delete: `plugins/lifecycle/references/ffs8-to-acceptance.md`
- Create: `plugins/lifecycle/skills/qa-verify/references/spec-to-acceptance.md`（≤40 行）
- Modify: `skills/qa-verify/SKILL.md` Step 1（輸入是 lean 規格路徑時讀 §2.3 → 依新檔轉案例）

- [ ] **Step 1：寫新檔**：規則三條——§2.3 每條案例原樣轉成 `acceptance-format.md` 案例；缺必要欄位（前置、步驟、預期）就列出缺項停下請人補，不猜；轉出的案例檔放 `.tmp/qa/<feature>/cases.md` 再交 planner。
- [ ] **Step 2：SKILL.md Step 1 加一列輸入判斷**；刪任何 FFS／ffs8 字樣。
- [ ] **Step 3：跑 validate.py `✓`、守門測試命中只剩 references 根目錄的檔。**

### Task 7：根 references 清理與 pipeline 改寫

**Files:**
- Modify: `plugins/lifecycle/references/pipeline.md`（改寫成新流程：triage／ticket → spec（lean）→ spec-check → implement（superpowers 或退路）→ qa-verify → release；刪 explore、spec-chain、full 目錄樹、探索摘要；≤120 行）
- Modify／Delete: 其餘 `references/*.md` 中仍有 FRD／SAD／BFS／FFS 字樣的檔——內容只服務 full 的整檔刪，混用的刪 full 段落

- [ ] **Step 1：逐檔處理** `rg -l '\b(FRD|SAD|BFS|FFS)\b' plugins/lifecycle/references plugins/lifecycle/agents plugins/lifecycle/templates`。判準：刪掉 full 段落後若檔案只剩標題或一兩句 → 整檔刪。
- [ ] **Step 2：孤兒檔**：跑守門測試 `test_no_orphan_files`，列出的檔逐一 `git rm`（例外：`references/skill-design.md` 若列出，代表原本就沒人引用——不刪，改在 plugin README 加一行引用並寫進 CHANGELOG「既有孤兒」，因為它不是規格鏈的連帶）。
- [ ] **Step 3：跨 plugin 引用** `rg -n 'lifecycle/(references|templates|agents)/|lifecycle:(explore|spec-chain|consolidate-docs|write-doc|dev-feedback)' plugins setup docs/agent-parity.md README.md .github --glob '!plugins/lifecycle/**' --glob '!**/CHANGELOG.md'` → 修到只剩合理引用（例：`plugins/workspace/skills/quality-check/SKILL.md`、`plugins/workspace/skills/project-setup/references/flow.md`、`plugins/research/skills/plugin-harvest/scripts/test_harvest.py`）。
- [ ] **Step 4：守門測試全綠**：`python3 plugins/lifecycle/scripts/test_no_spec_chain.py` → 5 PASS。

### Task 8：install-project 不再停用 superpowers

**Files:**
- Modify: `setup/install-project.sh:123-` （刪整段停用 superpowers 的邏輯與 python 片段）
- Modify: `setup/tests/install-project.sh`（第 12 段）
- Modify: `setup/README.md:34`

- [ ] **Step 1：改測試先紅**：第 12 段改為兩個情境——(a) 新專案裝 lifecycle → `settings.local.json` 不含 `superpowers@…: false`；(b) 舊版已寫入 `"superpowers@claude-plugins-official": false` 的專案重跑 → 該鍵維持原樣（不刪、不改 true）。
- [ ] **Step 2：跑紅**：`bash setup/tests/install-project.sh` → (a) FAIL。
- [ ] **Step 3：刪停用段落**；`setup/README.md` 第 34 行改述「lifecycle 與 superpowers 並存：流程交 superpowers」。
- [ ] **Step 4：跑綠**：`bash setup/tests/install-project.sh` 全 PASS。

### Task 9：文件、版號、驗證、e2e、commit

**Files:**
- Modify: `plugins/lifecycle/README.md`、根 `README.md`（「skills 與 agents」表刪 5 個 skill 與 spec-writer；第 78–80 行流程段）、`docs/agent-parity.md:86,91`、`.github/workflows/validate.yml`（若有規格鏈相關步驟）、`plugins/lifecycle/package.json`（不用改，確認）
- Modify: `plugins/lifecycle/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`plugins/lifecycle/CHANGELOG.md`

- [ ] **Step 1：README 與 parity 文件同步。**
- [ ] **Step 2：release-plugin `lifecycle major 3.0.0`**；CHANGELOG 起因寫「單人專案 24 個 session 只用到清單腳本、本機無專案用 `scale: full`；決定 superpowers 當工程核心（設計見 docs/superpowers/specs/2026-11-15-lifecycle-split-design.md）」，BREAKING 列：移除的 5 個 skill、spec-writer、`--stage`、`scale`、spec-check 的 verify／readiness、ticket-create 角色子票；遷移：舊 `scale: full` 照 lean 跑並提示；被舊版停用 superpowers 的專案手動刪 `.claude/settings.local.json` 的該鍵。
- [ ] **Step 3：全部驗證**（repo 根）

```bash
python3 scripts/ci/validate.py
for t in $(find plugins -name 'test_*.py' -not -path '*/node_modules/*'); do python3 "$t" >/dev/null 2>&1 || echo "FAIL $t"; done
bash setup/tests/install-project.sh
for t in setup/tests/*.sh; do bash "$t" >/dev/null 2>&1 || echo "FAIL $t"; done
```

Expected：validate `✓`；兩個迴圈無 `FAIL` 行。

- [ ] **Step 4：e2e**（push 前，`claude -p --plugin-dir plugins/lifecycle`，prompt 走 stdin，暫存專案放 scratchpad）
  - (a) 「用 lifecycle:spec 為『訂單加備註欄』寫規格」→ 產出 `docs/specs/<feature>.md`，§2.3 為 acceptance-format 案例；不出現 FRD 等字樣。
  - (b) 暫存專案 `.plugharbor/lifecycle.yml` 寫 `scale: full` 再跑 (a) → 照 lean 產出，回覆提到已移除。
  - (c) 「用 lifecycle:spec-check 檢查 (a) 的規格」→ 走 lean 檢查表。
- [ ] **Step 5：commit**（逐檔 `git add`；刪除用 `git rm` 已暫存）

```bash
git status --short   # 確認只有本計畫的檔
git commit -m "feat(lifecycle)!: 移除四份文件規格鏈與連帶 skill，install-project 不再停用 superpowers（lifecycle 3.0.0）"
```
