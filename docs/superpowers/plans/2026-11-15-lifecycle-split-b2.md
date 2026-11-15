# lifecycle 拆分第二批「再拆」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 lifecycle 的票務、需求與會議、交付文件 skill 搬到三個新 plugin（tickets、discovery、delivery，各 1.0.0），只搬不改行為；共用素材複製一份、agent 副本改名，由 validate.py 機械比對同步；lifecycle 3.0.0 → 4.0.0。

**Architecture:** 先在 `validate.py` 加「共用副本同步」檢查（清單檔 `scripts/ci/shared-copies.json`＋改名對照），再逐個 plugin 用 `git mv` 搬、`cp` 複製、改 `lifecycle:<skill>` 前綴，每個 task 結束 validate 必須綠——它已會抓斷掉的路徑引用、不存在的 `<plugin>:<name>`、扁平命名撞名、README 清單漏列。最後改 install-project 的遷移（有票務設定就補裝 tickets）並跑 e2e。

**Tech Stack:** Markdown skill、Python 3 unittest（`python3 test_x.py` 直接跑）、bash（setup 腳本與測試）、JSON（marketplace、manifest）。

**Spec:** `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`（第二批＝「分批」第 2 項；共用素材、接點、遷移見「決定／共用」與「分批」兩節）

## Global Constraints

- 工作在 worktree `../plugharbor-lifecycle-b2`（分支 `feat/lifecycle-b2`，從 `main` 開）；主 checkout 不動。
- 版號：lifecycle **4.0.0**（BREAKING：skill 搬走）；tickets、discovery、delivery **1.0.0**。各自 `CHANGELOG.md` 最上方 `## [x.y.z] - 2026-11-15`，正體中文、寫明起因（設計文件「起因」節）。lifecycle 用 release-plugin skill 同步三處；新 plugin 手動加 `marketplace.json` 條目與根 README 兩張表。
- 沿用第一批做法：前面的 task **不 commit**，Task 7 一次 commit（例外理由：避免 lifecycle 4.0.0 拆成中間版號；validate 每個 task 都要綠）。
- 每個 plugin 能單獨安裝：`plugin.json` 不宣告 `dependencies`；跨 plugin 叫用一律可選，退路寫在 `shared-preludes.md`「可選依賴」表。
- 新 plugin 都是專案層（不進 `setup/lib.sh` 的 `PH_USER_PLUGINS`），都要有 pi 的 `package.json`（照 lifecycle 那份，`name`／`keywords` 換名、不放 `version`）。
- 外洩規則：不寫個人絕對路徑、公司名；`git add` 逐檔指名；不用 `--no-verify`。
- 不碰第三批：不改 implement 主流程、不寫 AGENTS.md 段落、不改 user 層 `superpowers.md`、不縮 spec-check。
- 搬動用 `git mv`（保留歷史）；複製用 `cp`，副本內容只允許「改名對照」造成的差異。

### 撰寫時自行決定（技術類）

1. **副本範圍比設計文件列的大**：共用 references 彼此點名（`config.md`→`shared-preludes.md`→`consultant-desk.md`→`advisor-discussion.md`→`advisor_last_reply.py`…），照「被點名就要在同一 plugin」算出來每個新 plugin 都要帶同一組 14 檔核心包（下表）。references 是按需讀取、不進常駐 context，代價只有 repo 體積；漂移由同步檢查擋。不改內文去斷鏈（會變成改行為）。
2. **副本改名規則**：`<plugin>-<原名>`（`tickets-scout`、`discovery-scout`、`discovery-report-writer`…）。設計文件的 `ticket-report-writer` 只是舉例，且易與 skill `ticket-report` 混淆。原名留給「仍在用它的 lifecycle」；lifecycle 不再用的（`report-writer`、`silent-failure-hunter`）原名搬到 tickets。
3. **同步檢查放 `validate.py`**（CI 與 pre-commit 都跑），取代 `plugins/lifecycle/scripts/test_harness_terms_sync.py`；browser-docs 的 5 個副本併進同一份清單。
4. `feature_checklist.py` 整檔複製給 tickets（不抽「解析部分」）：`reconcile.py` 以 `parents[3]/scripts/feature_checklist.py` 找它，搬到 tickets 後路徑自動對上，程式不用改。
5. 沒人用的 lifecycle 檔變孤兒時整檔搬走而非複製（`pipeline.md`、`report-calendar.md` → tickets；templates → discovery）。
6. plugin-healthcheck 搬到 `.claude/skills/` 後改吃參數 `<plugin>`（原本檢查「本 plugin」），刪掉 harness-terms 指向（repo 內 skill 只給 Claude Code 用）。

## 檔案去向

**核心包**（每個新 plugin 都複製一份；canonical＝lifecycle）：references `harness-terms` `config` `shared-preludes` `shared-preludes-details` `graphify-integration` `analysis-rigor` `analysis-standards` `verify-against-source` `consultant-desk` `advisor-discussion` `legacy-parity` `dispatch-conventions`（`.md`）；scripts `config.py` `test_config.py` `advisor_last_reply.py` `test_advisor_last_reply.py` `test_harness_neutral.py`。

| plugin | `git mv` 自 lifecycle | 額外複製（canonical → 副本名） |
|---|---|---|
| tickets | skills `ticket-ops` `ticket-create` `ticket-reply` `ticket-report` `triage`；agents `report-writer` `silent-failure-hunter`；references `pipeline.md` `report-calendar.md` | 核心包；`references/feature-checklist.md`；`scripts/feature_checklist.py`＋`test_feature_checklist.py`；agent `scout`→`tickets-scout`；`discovery/skills/meeting-minutes/references/second-opinion.md`→`skills/triage/references/second-opinion.md` |
| discovery | skills `meeting-minutes` `interview-prep` `survey-existing-system` `prototype-html`；`templates/` 三檔 | 核心包；agents `scout`→`discovery-scout`、`domain-advisor`→`discovery-domain-advisor`、`tickets/agents/report-writer`→`discovery-report-writer`、`tickets/agents/silent-failure-hunter`→`discovery-silent-failure-hunter` |
| delivery | skills `operation-manual` `demo-video`；agents `manual-explorer` `manual-reviewer` `manual-writer`；references `annotate-spec.md` `anonymize-before-capture.md`；scripts `annotate.py` `anonymize-page.js` `build-deck.sh` `build-manual-docx.sh` `build-manual-pdf.py` `check-deck-overflow.py` `check-inventory-rects.py` `test_check_inventory_rects.py` `ensure-tools.sh` `make-docx-reference.py` `manual-print.css` `manual-reference.docx` `manual_brand.py` `test_manual_brand.py` `prep-docx-cover.py` `text-image-ratio.py` | 核心包 |
| `.claude/skills/` | `plugin-healthcheck` | — |

lifecycle 留下：skills `spec` `spec-check` `implement` `qa-verify` `release`；agents `architect` `debugger` `developer` `domain-advisor` `qa-fixture` `qa-planner` `qa-runner-ui` `reviewer` `scout` `spec-sampler` `tester`；核心包＋`feature-checklist.md` `skill-design.md`＋`feature_checklist.py`；測試 `test_config` `test_feature_checklist` `test_advisor_last_reply` `test_harness_neutral` `test_manifest` `test_no_spec_chain` `test_skill_contracts`。

## Review Focus

1. **既有專案重跑 install-project**：`.agents/skills/triage` 是指向 `lifecycle/skills/triage` 的 symlink（搬家後失效）或複製模式的複本 → 失效的要清掉；設定有 `ticket:` 時改從 tickets 重建。測試在 Task 6。
2. **`install.sh --check-projects`**：只裝 lifecycle、設定有 `ticket:` 的專案 → 報 tickets 缺少並給修正指令（自動補裝在 `--check` 也生效即可）。測試在 Task 6。
3. **只裝 lifecycle、沒裝 tickets 時跑到同步票／開缺陷票**（implement 收尾、qa-verify）→ 照「可選依賴」表降級（只勾清單、列出待開票內容），不報錯。契約測試在 Task 5。
4. **只改了一份副本**（例如只改 tickets 的 `shared-preludes.md`）→ validate 失敗並點名兩個檔。測試在 Task 1。
5. **Claude Code 使用者照舊打 `/lifecycle:ticket-ops`** → 已不存在；CHANGELOG 4.0.0 寫「搬到哪、怎麼裝」的對照，plugin README 同。驗收在 Task 7 的 e2e（看 CHANGELOG 對照表存在）。

---

### Task 1：共用副本同步檢查

**Files:**
- Modify: `scripts/ci/validate.py`（新增 `expected_copy`、`shared_copy_errors`、`check_shared_copies`，在 `main()` 呼叫）
- Create: `scripts/ci/shared-copies.json`、`scripts/ci/test_validate.py`
- Modify: `.github/workflows/validate.yml`（「Marketplace 驗證」步驟多跑 `python scripts/ci/test_validate.py`）
- Delete: `plugins/lifecycle/scripts/test_harness_terms_sync.py`；Modify: `plugins/lifecycle/references/config.md:123`（改指 validate 的同步檢查）

**Interfaces:**
- Produces: manifest 格式 `{"aliases": {<plugin>: {<原名>: <副本名>}}, "groups": [[canonical, copy, …], …]}`，路徑相對 repo 根；後續 task 往 `groups`／`aliases` 加項。
- Produces: `expected_copy(text: str, copy_plugin: str, aliases: dict) -> str`；`shared_copy_errors(root: Path, manifest: dict) -> list[str]`。

- [ ] **Step 1：開 worktree**：`git worktree add ../plugharbor-lifecycle-b2 -b feat/lifecycle-b2 main`，之後全部在該目錄做。
- [ ] **Step 2：寫測試** `scripts/ci/test_validate.py`（`sys.path` 加 `scripts/ci` 後 `import validate`）

```python
A = {"tickets": {"scout": "tickets-scout"}}
def test_alias_rewrites_bare_and_prefixed(self):
    src = "派 `scout`；`lifecycle:scout`；scouting；`scout-x`；`lifecycle:domain-advisor`"
    self.assertEqual(validate.expected_copy(src, "tickets", A),
        "派 `tickets-scout`；`tickets:tickets-scout`；scouting；`scout-x`；`lifecycle:domain-advisor`")
def test_identical_copies_pass(self): ...      # tmp 目錄兩檔相同 → []
def test_drift_names_both_files(self): ...     # 副本多一行 → 1 筆，訊息含副本與 canonical 路徑
def test_missing_copy_reported(self): ...      # 副本不存在 → 1 筆，含「缺副本」
def test_alias_applied_before_compare(self): ...  # canonical 寫 `scout`、tickets 副本寫 `tickets-scout` → []
```

- [ ] **Step 3：跑，確認紅**：`python3 scripts/ci/test_validate.py` → `AttributeError: ... expected_copy`
- [ ] **Step 4：實作**。`expected_copy`：對 `aliases[copy_plugin]` 每組，regex `(?<![\w-])(?:[a-z][a-z0-9-]*:)?<原名>(?![\w-])`，有前綴換成 `<copy_plugin>:<副本名>`、沒前綴換成 `<副本名>`。`shared_copy_errors`：每組第一個是 canonical，canonical 所在 plugin 取路徑 `plugins/<p>/` 的 `<p>`；文字檔比 `expected_copy` 後的字串，非 UTF-8 比 bytes。`check_shared_copies` 讀 manifest、逐筆 `err`。manifest 先放現有 5 組（canonical＝lifecycle，副本＝browser-docs）：`references/harness-terms.md` `references/annotate-spec.md` `references/anonymize-before-capture.md` `scripts/annotate.py` `scripts/anonymize-page.js`；`aliases` 先空。刪 `test_harness_terms_sync.py`，`config.md` 第 123 行改指 `scripts/ci/shared-copies.json`。
- [ ] **Step 5：驗證**：`python3 scripts/ci/test_validate.py` 全過；`python3 scripts/ci/validate.py` → `✓`；手動在 browser-docs 的 `harness-terms.md` 末尾加一行 → validate 報該檔與 lifecycle 那份不同步 → 還原。

### Task 2：tickets plugin

**Files:**
- Create: `plugins/tickets/{.claude-plugin/plugin.json,package.json,README.md,CHANGELOG.md}`、`plugins/tickets/scripts/test_skill_contracts.py`
- Move／Copy：見「檔案去向」tickets 列
- Modify: 全 repo 的 `lifecycle:{ticket-ops,ticket-create,ticket-reply,ticket-report,triage,report-writer,silent-failure-hunter}` → `tickets:…`（略過各 `CHANGELOG.md`、`docs/specs/`、`docs/retrospective/`）；`harvest-lock.json` 的 `lifecycle:ticket-report`
- Modify: tickets 內的 `lifecycle:scout`／裸寫 `scout` → `tickets:tickets-scout`／`tickets-scout`；`triage/SKILL.md` 的 `${CLAUDE_PLUGIN_ROOT}/skills/meeting-minutes/references/second-opinion.md` → `…/skills/triage/references/second-opinion.md`
- Modify: `.claude-plugin/marketplace.json`、根 `README.md`（plugin 表＋「skills 與 agents」表）、`scripts/ci/shared-copies.json`

**Interfaces:**
- Consumes: Task 1 的 manifest 格式。
- Produces: `tickets:ticket-ops` 等新叫用名；`aliases.tickets = {"scout": "tickets-scout"}`；`plugins/tickets/agents/report-writer.md`、`silent-failure-hunter.md` 是 discovery 副本的 canonical。

- [ ] **Step 1：搬與複製**（`git mv`／`cp` 照表），`tickets-scout.md` 的 frontmatter `name:` 跟著改。
- [ ] **Step 2：manifest 加組**：核心包每檔一組（canonical lifecycle → tickets 副本；`harness-terms` 併進 Task 1 那組）、`feature-checklist.md`、`feature_checklist.py`＋測試、`scout.md`→`tickets-scout.md`、`second-opinion.md`。
- [ ] **Step 3：寫 `plugins/tickets/scripts/test_skill_contracts.py`**，從 lifecycle 那份搬來（並從原檔刪掉）：`test_no_relay_era_wording` 中 `skills/triage/references/ticket-flow.md` 不含 `` `scale` ``、`ticket-ops/SKILL.md` 含 `../../references/harness-terms.md`；另加 `test_reconcile_finds_checklist_parser`：`(ROOT/"scripts"/"feature_checklist.py").exists()` 且 `reconcile.py` 內含 `parents[3]`。
- [ ] **Step 4：改前綴**：`rg -l 'lifecycle:(ticket-ops|ticket-create|ticket-reply|ticket-report|triage|report-writer|silent-failure-hunter)\b'` 的檔逐一改（canonical 改了，副本同步改）。
- [ ] **Step 5：manifest 檔**：`plugin.json`（description 一句：票務——建票、改階段、回覆、日報週報、分流、清單對帳；工具可換 Linear／GitHub／Jira）、`package.json`、`README.md`（定位、安裝、設定讀 `.plugharbor/lifecycle.yml` 的 `ticket:` 區塊、可選依賴）、`CHANGELOG.md` `## [1.0.0]`；marketplace 與根 README 兩張表加 tickets 列。
- [ ] **Step 6：驗證**：`python3 scripts/ci/validate.py` → `✓`；`for t in plugins/tickets/**/test_*.py; do python3 "$t"; done`（zsh 用 `setopt globstar` 或 `git ls-files`）全過；`python3 plugins/tickets/skills/ticket-ops/scripts/test_reconcile.py` 過。

### Task 3：discovery plugin

**Files:** 照「檔案去向」discovery 列；`plugins/discovery/` 的四個 manifest 檔與 `scripts/test_skill_contracts.py`；marketplace、根 README、`shared-copies.json`、`harvest-lock.json`（`lifecycle:prototype-html`）。

**Interfaces:**
- Consumes: Task 2 的 tickets agent canonical。
- Produces: `aliases.discovery = {"scout": "discovery-scout", "domain-advisor": "discovery-domain-advisor", "report-writer": "discovery-report-writer", "silent-failure-hunter": "discovery-silent-failure-hunter"}`；`discovery:meeting-minutes` 等叫用名。

- [ ] **Step 1：搬與複製**，四個副本 agent 改 `name:`；discovery 內的 `lifecycle:scout`／`lifecycle:domain-advisor`／`tickets:report-writer`／`tickets:silent-failure-hunter` 與裸寫原名改成副本名。
- [ ] **Step 2：manifest 加組**（核心包、四個 agent），全 repo 改 `lifecycle:{meeting-minutes,interview-prep,survey-existing-system,prototype-html}` → `discovery:…`。
- [ ] **Step 3：`test_skill_contracts.py`** 搬來：`prototype-html/SKILL.md` 不含 `` `ask_user` ``、含 `../../references/harness-terms.md`；`interview-prep/SKILL.md` 不含 `§Step 0.5`（並從 lifecycle 原檔刪掉這幾條）。
- [ ] **Step 4：manifest 檔**（description：需求與會議——會議記錄、訪談準備、既有系統勘察、HTML 原型）、marketplace、根 README。
- [ ] **Step 5：驗證**：validate `✓`；discovery 下全部 `test_*.py` 過。

### Task 4：delivery plugin

**Files:** 照「檔案去向」delivery 列；四個 manifest 檔；`.github/workflows/validate.yml:50` 路徑改 `plugins/delivery/skills/demo-video/scripts/e2e.test.mjs`；`shared-copies.json`（Task 1 那 4 組 annotate／anonymize 的 canonical 改成 delivery 路徑）；`harvest-lock.json`（`lifecycle:demo-video`）；marketplace、根 README。

- [ ] **Step 1：搬**；全 repo 改 `lifecycle:{operation-manual,demo-video,manual-explorer,manual-reviewer,manual-writer}` → `delivery:…`。
- [ ] **Step 2：manifest 加核心包組**，改 annotate／anonymize 組的 canonical。
- [ ] **Step 3：manifest 檔**（description：交付文件——操作手冊（Word／PDF／簡報）與示範影片）、marketplace、根 README；`docs/agent-parity.md:86` 改成 delivery 與 browser-docs 各放一份。
- [ ] **Step 4：驗證**：validate `✓`；`python3 plugins/delivery/scripts/test_manual_brand.py`、`test_check_inventory_rects.py`、`test_harness_neutral.py` 過；`node --test $(git ls-files 'plugins/**/*.test.mjs')` 過（本機有 ffmpeg 時另跑 `DEMO_VIDEO_E2E_REQUIRED=1 node --test plugins/delivery/skills/demo-video/scripts/e2e.test.mjs`，沒有標未驗證）。

### Task 5：lifecycle 收斂與可選依賴退路

**Files:**
- Modify: `plugins/lifecycle/references/shared-preludes.md`「可選依賴」表（加 3 列，副本同步）；第 72 行 `skills/implement/references/fallback.md` 改寫成「`lifecycle:implement` 的極簡退路」（副本裡這個路徑會被 validate 判斷不存在）
- Modify: `plugins/lifecycle/scripts/test_skill_contracts.py`（刪掉已搬走的斷言；`test_pointer_survives_symlink_and_copy_install` 的 plugin 清單改 `["lifecycle", "browser-docs", "tickets", "discovery", "delivery"]`、不存在就跳過）
- Move: `plugins/lifecycle/skills/plugin-healthcheck/` → `.claude/skills/plugin-healthcheck/`
- Modify: `plugins/lifecycle/{README.md,.claude-plugin/plugin.json}`（定位改成開發主線：spec、spec-check、implement、qa-verify、release；另列三個新 plugin 的去向）、`CHANGELOG.md` `## [4.0.0]`、release-plugin 同步版號

可選依賴表新增（照原表欄位「用到｜哪裡｜沒裝時」）：

| 用到 | 哪裡 | 沒裝時 |
|---|---|---|
| `tickets:ticket-ops` 等票務 skill | implement 收尾同步票、qa-verify 開缺陷票、spec 回寫票 | 只更新清單，把要開或要改的票列給使用者，不呼叫票務工具 |
| `lifecycle:spec` | triage、survey-existing-system 建議寫規格 | 只給「建議寫規格」與要點，不產規格檔 |
| `discovery:meeting-minutes` | triage 批次、ticket-report 引用會議記錄 | 請使用者貼上會議內容或記錄檔路徑 |

- [ ] **Step 1：寫測試**（lifecycle `test_skill_contracts.py` 新增）

```python
def test_optional_deps_cover_split_plugins(self):
    s = read("references/shared-preludes.md")
    for name in ("`tickets:ticket-ops`", "`lifecycle:spec`", "`discovery:meeting-minutes`"):
        self.assertIn(name, s)
def test_only_mainline_skills_remain(self):
    self.assertEqual(sorted(p.name for p in (ROOT/"skills").iterdir() if p.is_dir()),
                     ["implement", "qa-verify", "release", "spec", "spec-check"])
```

- [ ] **Step 2：跑，確認紅**（缺表列、plugin-healthcheck 還在）。
- [ ] **Step 3：改**（表、fallback 那行、搬 plugin-healthcheck 並改為吃 `<plugin>` 參數、`plugins/<plugin>/` 為掃描根）；根 README 的 lifecycle 兩列、第 78–80 行流程段改用新叫用名；`AGENTS.md` 的「11 個 plugin」→ 14。
- [ ] **Step 4：驗證**：lifecycle 下全部 `test_*.py` 過；`test_no_spec_chain.py` 的孤兒檢查過（孤兒就照決定 5 搬走）；validate `✓`。

### Task 6：install-project 遷移

**Files:**
- Modify: `setup/install-project.sh`（`PLUGINS` 組好之後、`RENAMED` 之前）
- Modify: `setup/tests/install-project.sh`（既有斷言裡的 `triage`、`ticket-report` 換成留在 lifecycle 的 `release`、`qa-verify`；新增第 14 段）
- Modify: `setup/README.md`（第 35 行附近補一句遷移說明）

行為：`PLUGINS` 含 `lifecycle`、不含 `tickets`，且 `$ROOT/.plugharbor/lifecycle.yml` 有 `^ticket:` 行 → 加入 `tickets` 並印 `ADD: tickets（.plugharbor/lifecycle.yml 有 ticket: 區塊）`。`--check` 也套用。不用 `ph_rename_new`。

- [ ] **Step 1：寫第 14 段測試**：
  - (a) 專案有 `.plugharbor/lifecycle.yml` 含 `ticket:\n  tool: github` → `run "$P" lifecycle` 輸出含 `ADD: tickets`，`STUB_CWD_LOG` 含 `claude plugin install tickets@plugharbor --scope local @ $P`。
  - (b) 沒有 `ticket:` → 不裝 tickets。
  - (c) `--check` 且 claude-list 只有 lifecycle → 輸出含 tickets 的 MISSING，exit 3。
  - (d) 先放 `.agents/skills/triage -> ../plugharbor/lifecycle/skills/triage`（失效）→ 重跑後印 `移除失效 link`，(a) 情境下 `.agents/skills/triage` 改指向 `../plugharbor/tickets/skills/triage`。
- [ ] **Step 2：跑，確認紅**：`bash setup/tests/install-project.sh` → `FAIL: (14a) …`
- [ ] **Step 3：實作**（一段 `case`＋`grep -q '^ticket:'`，bash 3.2 相容）。
- [ ] **Step 4：驗證**：`for t in setup/tests/*.sh; do bash "$t" || echo "FAIL $t"; done` 全過（`lib/` 除外）。

### Task 7：總驗收、e2e、commit

- [ ] **Step 1：全套本機測試**：`python3 scripts/ci/validate.py`、`python3 scripts/ci/test_validate.py`、`git ls-files 'plugins/**/test_*.py'`（排除 toolkit hooks／transcribe）逐一跑、`node --test`、`python3 -m pytest plugins/toolkit/hooks/tests`、setup 測試。
- [ ] **Step 2：漂移演練**：改 tickets 的 `shared-preludes.md` 一個字 → validate 報錯點名兩檔 → 還原。
- [ ] **Step 3：e2e（離線）**：在 scratchpad 建空 git repo，分別 `claude -p --plugin-dir plugins/<p>`：
  - tickets：問「列出你看得到的 tickets: skill 與 agent」→ 5 skill、3 agent；對 fixture 清單跑 `reconcile.py`（用 `test_reconcile.py` 的 fixture 寫法）有輸出、沒有 import 錯。
  - discovery：給一段假會議逐字稿，叫 `discovery:meeting-minutes` → 產出會議記錄檔、沒有找不到檔的錯。
  - delivery、lifecycle：列 skill 數量對（2、5）。
- [ ] **Step 4：e2e（線上，對外動作先問使用者）**：在票務雙軌示範 repo 用只裝 tickets 的 session 建一張測試票、改階段、對帳，收尾關票。使用者不同意就標未驗證。
- [ ] **Step 5：收尾文件**：`docs/feature.md` 第二批改 `[x]`（附版號、未 push）；確認四份 CHANGELOG 都寫了起因與「舊叫用名 → 新叫用名」對照。
- [ ] **Step 6：rebase**：commit 前 `git fetch` 並把分支接上最新 `main`；另一個 session 正在 main bump toolkit（`marketplace.json`、根 `README.md` 的 toolkit 列），衝突只會在這兩檔的不同列，保留雙方。
- [ ] **Step 7：commit**：`git status --short` 逐檔 `git add`（含 `git mv` 的刪除與新增），`git status` 確認 staged 只有本批；`git commit`（Conventional Commits，`feat(lifecycle)!: …`，結尾附 attribution）；pre-commit 的 validate 必須過。push 前另依「push 前先試用」記憶，請使用者在一個專案試用後再 push。
