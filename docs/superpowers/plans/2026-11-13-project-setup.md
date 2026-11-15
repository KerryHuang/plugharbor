# project-setup 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal：** 在 workspace plugin 新增 `project-setup` skill。只能從 Claude Code 叫用，替一個目錄或專案在專案層補裝 Claude Code、Codex、pi、agy 都讀得到的 skill 與指示。來源依序是 plugharbor、網路上的純 skill、自寫。

**Architecture：** 判斷與寫作（需求解讀、挑 plugin、寫 AGENTS.md 與缺口 skill）交給模型，照 SKILL.md 與 references 進行。機械步驟交給 3 支 Python 標準函式庫腳本：

- `detect.py`：盤點現況、決定 git 模式、依技術線索建議 plugin。
- `vendor.py`：檢查外部 skill 是否只有說明文件、授權是否寬鬆，通過就複製。
- `mirror.py`：把專案 skill 鏡像到 `.agents/skills`，並寫入 `.git/info/exclude`。

plugharbor 的 plugin 照舊用 `setup/install-project.sh` 安裝。另外替它加 `--no-claude` 選項，讓「進 git」模式能先用 `--shared` 裝 Claude（project scope），再補裝 pi、Codex、agy（local）。

**Tech Stack：** Python 3（只用標準函式庫，`unittest`）、bash（install-project.sh）、Markdown。

**Spec：** `docs/superpowers/specs/2026-11-13-project-setup-design.md`

## Global Constraints

- SKILL.md 300 行以內；實作邏輯放 `references/` 或 `scripts/`。
- 腳本只用 Python 標準函式庫。檔案 I/O 一律明給 `encoding="utf-8"`。
- 只動專案層：不寫 `~/.claude`、`~/.codex`、`~/.pi`。
- 不覆寫既有的 `AGENTS.md`、`CLAUDE.md`、`.claude/skills/*`、`.agents/skills/*`；碰到同名的一律略過並回報。
- 外部 skill 只有「沒有 `scripts/`、沒有可執行檔、沒有 hooks／MCP 設定，而且授權屬於 MIT、Apache-2.0、BSD-2-Clause、BSD-3-Clause、ISC、0BSD、Unlicense、CC0-1.0」的才直接裝。其他一律回傳「待決」並附理由。
- git 模式（spec 的主控決定）：
  - 沒有 `.git`：`git init`，不 commit，新檔不加 exclude。
  - 既有 AI 設定已進版控：`shared`，新檔不加 exclude。
  - 其他：`local`，新檔一律加 exclude。
- 只從 Claude Code 叫用。在其他 CLI 被要求時，回覆「請改到 Claude Code 叫用 project-setup」。
- workspace 在 user 層，description 是常駐 context：新 skill 的 description 限 120 字以內，CHANGELOG 寫明多出的常駐量。
- 公開 repo：不得寫進個人絕對路徑。版號照 AGENTS.md：workspace 升 minor 到 1.10.0，`setup/` 的改動一併寫進同一筆 CHANGELOG。

## Review Focus

1. 路徑含空白或中文（例如 `~/Work/我的 專案`）時，偵測、鏡像、exclude 都要正常運作。→ Task 1、Task 3 各加一個測試。
2. `.agents/skills/<name>` 已有同名的實體目錄（不是 link），例如 dual-tool-mirror 鏡像出來的：不得覆蓋，回報 skipped。→ Task 3。
3. 外部 repo 的 LICENSE 只放在 repo 根，不在 skill 目錄：要往上找到 repo 根。→ Task 2。
4. 系統建不了 symlink（Windows 沒開開發人員模式）：改用複製，並寫 `.plugharbor-root` 之類的來源標記；重跑時不要重複複製。→ Task 3。
5. `CLAUDE.md` 已存在、內容不是 `@AGENTS.md`：不改它。偵測要回報 `claude_md: "custom"`，讓 SKILL 流程列進「待你決定」。→ Task 1。

---

### Task 1：detect.py——盤點、git 模式、建議 plugin

**Files：**
- Create：`plugins/workspace/skills/project-setup/scripts/detect.py`
- Test：`plugins/workspace/skills/project-setup/scripts/test_detect.py`

**Interfaces：**
- Produces：`inventory(root: Path) -> dict`。命令列 `python3 detect.py <root>` 印出同一份 JSON。鍵如下：
  - `is_empty: bool`：沒有任何檔案，或只有 `.git`。
  - `has_git: bool`
  - `git_mode: "init" | "shared" | "local"`
  - `signals: list[str]`：技術線索，例如 `"dotnet"`、`"node"`、`"vue"`、`"react"`、`"sql"`、`"python"`、`"avalonia"`。
  - `suggested_plugins: list[str]`
  - `existing`：
    - `agents_md: "none" | "present"`
    - `claude_md: "none" | "at-agents" | "custom"`
    - `claude_skills: list[str]`
    - `agents_skills: list[str]`
    - `pi_settings: bool`

- [ ] **Step 1：寫失敗測試**（`unittest`，每個測試在 `tempfile.TemporaryDirectory()` 裡建目錄）
  - `test_empty_dir`：`is_empty True`、`has_git False`、`git_mode "init"`、`signals []`。
  - `test_untracked_existing_repo_is_local`：`git init`，加一個 `a.cs` 並 commit → `git_mode "local"`。
  - `test_tracked_ai_config_is_shared`：`AGENTS.md` 已 commit → `git_mode "shared"`、`existing.agents_md "present"`。
  - `test_signals_and_suggestions`：
    - 有 `x.csproj` → `signals` 含 `"dotnet"`，`suggested_plugins` 含 `"backend"`。
    - `package.json` 的 dependencies 有 `vue` → 含 `"vue"` 與 `"frontend"`。
    - 有 `db/a.sql` → 含 `"sql"` 與 `"database"`。
    - `x.csproj` 內含 `Avalonia` → 含 `"desktop"`。
  - `test_claude_md_variants`：內容是 `@AGENTS.md\n` → `"at-agents"`；其他內容 → `"custom"`。
  - `test_path_with_space_and_cjk`：根目錄名是 `我的 專案`，結果同 `test_signals_and_suggestions` 的 csproj 案例。
  - `test_cli_prints_json`：子程序執行 `detect.py <root>`，exit 0，stdout 可用 `json.loads` 解析。
- [ ] **Step 2：執行 `python3 plugins/workspace/skills/project-setup/scripts/test_detect.py`**，預期 FAIL（模組不存在）。
- [ ] **Step 3：實作 `inventory()`**
  - 線索對應表放在檔案頂端的常數 `SIGNAL_PLUGINS = {"dotnet": "backend", "vue": "frontend", "react": "frontend", "sql": "database", "avalonia": "desktop"}`。
  - 掃描深度限制 3 層，跳過 `node_modules`、`.git`、`bin`、`obj`。
  - 「既有 AI 設定已進版控」的判斷：`git ls-files AGENTS.md CLAUDE.md .claude .agents` 有輸出。
- [ ] **Step 4：重跑測試**，預期全部通過。
- [ ] **Step 5：Commit**：`feat(workspace): project-setup 盤點腳本`

### Task 2：vendor.py——外部 skill 純度與授權檢查、複製

**Files：**
- Create：`plugins/workspace/skills/project-setup/scripts/vendor.py`
- Test：`plugins/workspace/skills/project-setup/scripts/test_vendor.py`

**Interfaces：**
- Produces：`vendor(skill_dir: Path, project_root: Path, source: dict) -> dict`。`source` 是 `{"repo": str, "commit": str, "path": str}`。回傳下列三種之一：
  - `{"status": "installed", "dest": str, "license": str}`
  - `{"status": "pending", "reasons": list[str]}`
  - `{"status": "skipped", "reason": "exists"}`

  命令列：`python3 vendor.py <skill_dir> <project_root> --repo R --commit C --path P`，印出 JSON。
- 複製到 `<project_root>/.claude/skills/<skill 目錄名>/`，同時寫 `.source.json`：`{repo, commit, path, license}`。

- [ ] **Step 1：寫失敗測試**
  - `test_pure_mit_installs`：skill 目錄只有 `SKILL.md` 與 `references/a.md`，repo 根有 MIT 授權 → `installed`、`license "MIT"`，`dest` 底下有 `SKILL.md` 和 `.source.json`。
  - `test_scripts_dir_pending`：有 `scripts/x.py` → `pending`，`reasons` 含 `"scripts"`。
  - `test_executable_file_pending`：任一檔案有執行權限 → `pending`，`reasons` 含 `"executable"`。
  - `test_hooks_or_mcp_pending`：有 `hooks/hooks.json` 或 `.mcp.json` → `pending`。
  - `test_no_license_pending`、`test_gpl_pending`：`reasons` 含 `"license"`。
  - `test_license_found_at_repo_root`：LICENSE 只在 repo 根（skill 在 `skills/x/`）→ `installed`。
  - `test_existing_dest_skipped`：目的地已存在 → `skipped`，內容不變。
- [ ] **Step 2：執行測試**，預期 FAIL。
- [ ] **Step 3：實作**
  - 授權偵測：在 skill 目錄往上到含 `.git` 或 `LICENSE*` 的最近一層，找 `LICENSE*`、`COPYING*`，比對各授權的關鍵句。MIT 比 `Permission is hereby granted, free of charge`，Apache 比 `Apache License` 加 `Version 2.0`，其餘照 Global Constraints 的清單。
  - 找不到或比對不上，就回傳 `pending`。
- [ ] **Step 4：重跑測試**，預期全部通過。
- [ ] **Step 5：Commit**：`feat(workspace): project-setup 外部 skill 檢查與複製`

### Task 3：mirror.py——鏡像到 .agents/skills、寫 exclude

**Files：**
- Create：`plugins/workspace/skills/project-setup/scripts/mirror.py`
- Test：`plugins/workspace/skills/project-setup/scripts/test_mirror.py`

**Interfaces：**
- Produces：
  - `mirror(project_root: Path) -> dict`：對每個 `.claude/skills/<name>/`，在 `.agents/skills/<name>` 建立相對路徑 symlink，指向 `../../.claude/skills/<name>`。回傳 `{"linked": [...], "copied": [...], "skipped": [...]}`。
  - `exclude(project_root: Path, paths: list[str]) -> list[str]`：把路徑加進 `.git/info/exclude`，冪等，回傳這次實際新增的行。
  - 命令列：`python3 mirror.py <root> [--exclude PATH ...]`。

- [ ] **Step 1：寫失敗測試**
  - `test_links_each_skill`：建出的 link 指向相對路徑，透過 link 讀得到 `SKILL.md`。
  - `test_existing_real_dir_skipped`：`.agents/skills/a` 是實體目錄 → 名字出現在 `skipped`，內容不變。
  - `test_rerun_idempotent`：跑兩次，第二次 `linked` 是空的，也沒有報錯。
  - `test_symlink_unsupported_falls_back_to_copy`：用 `unittest.mock.patch("os.symlink", side_effect=OSError)` → 名字出現在 `copied`，目錄內有 `.mirror-source` 標記檔；重跑時若內容相同就不再複製。
  - `test_exclude_idempotent`：同一路徑加兩次，exclude 檔裡只有一行；第二次回傳 `[]`。
  - `test_path_with_space_and_cjk`：根目錄名是 `我的 專案`，linked 和 exclude 都正常。
- [ ] **Step 2：執行測試**，預期 FAIL。
- [ ] **Step 3：實作**，簽名照上面的 Interfaces。
- [ ] **Step 4：重跑測試**，預期全部通過。
- [ ] **Step 5：Commit**：`feat(workspace): project-setup 鏡像與 exclude`

### Task 4：install-project.sh 加 `--no-claude`

**Files：**
- Modify：`setup/install-project.sh`（參數解析，以及 Claude Code 那一段的開頭）
- Modify：`setup/tests/install-project.sh`
- Modify：`setup/README.md`（用法行與表格說明）

**Interfaces：**
- Produces：`install-project.sh [--shared] [--no-claude] [--check] <專案根> <plugin…>`。加 `--no-claude` 時，略過整段 Claude Code 安裝，印出 `SKIP: claude（--no-claude）`；pi、Codex、agy 照 local 規則裝。`--shared` 和 `--no-claude` 同時給是用法錯誤，exit 2。

- [ ] **Step 1：在 `setup/tests/install-project.sh` 加測試案例**，照既有 stub CLI 的寫法：
  - 加 `--no-claude` 時，stub claude 沒有被呼叫，stub codex／pi 照常被呼叫。
  - `--shared --no-claude` 的 exit code 是 2。
- [ ] **Step 2：執行 `bash setup/tests/install-project.sh`**，預期新案例 FAIL。
- [ ] **Step 3：實作 `NOCLAUDE` 旗標與用法檢查**。
- [ ] **Step 4：重跑**，預期全部 PASS。
- [ ] **Step 5：Commit**：`feat(setup): install-project.sh 加 --no-claude`

### Task 5：SKILL.md、references、版號與文件

**Files：**
- Create：`plugins/workspace/skills/project-setup/SKILL.md`
- Create：`plugins/workspace/skills/project-setup/references/flow.md`：七步流程細節，以及每步要呼叫哪支腳本。
- Create：`plugins/workspace/skills/project-setup/references/external-search.md`：skills.sh API `https://skills.sh/api/search?q=<關鍵字>&limit=10`、外部文字當資料、只取 skill 目錄。
- Create：`plugins/workspace/skills/project-setup/references/report.md`：清單格式。
- Modify：`plugins/workspace/README.md`、根目錄 `README.md`（skills 表與版本欄）、`plugins/workspace/CHANGELOG.md`、`plugins/workspace/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`docs/feature-checklist.md`（📋 改 🚧）

**Interfaces：**
- Consumes：Task 1 到 Task 4 的命令列介面。
- SKILL.md 的 frontmatter：
  - `name: project-setup`
  - `description`：120 字以內，含觸發詞「幫這個專案裝設定」「專案補裝」「project-setup」。

- [ ] **Step 1：寫 SKILL.md**，用條列寫出流程骨架：
  1. 確認在 Claude Code 內；不是的話回固定訊息後停止。
  2. 跑 `detect.py`。
  3. 定需求清單：使用者的需求句，加上 `signals`。
  4. plugharbor 安裝。`git_mode` 是 `init` 時，先跑 `git init`（不 commit）。安裝依 `git_mode` 分三種：
     - `local`：`install-project.sh <root> <plugins>`。
     - `shared`、`init`：`install-project.sh --shared <root> <plugins>`，再跑一次 `install-project.sh --no-claude <root> <plugins>`，最後用 `mirror.py --exclude` 把 `.agents/plugharbor`、`.pi/settings.json` 加進 exclude。
  5. 網路搜尋，用 `vendor.py` 安裝。
  6. 自寫 `AGENTS.md`、`CLAUDE.md`（只在 `existing` 是 `none` 時寫），以及缺口 skill，放 `.claude/skills/`。`AGENTS.md` 裡的建置與測試指令要實際跑過，沒跑過的標「未驗證」。
  7. 跑 `mirror.py`；`git_mode` 是 `local` 時把新檔加進 exclude。
  8. 驗證並交清單。
- [ ] **Step 2：寫三份 references**。`report.md` 的清單欄位：項目、對應需求、來源（plugharbor／repo@commit／自寫）、授權、進不進 git、移除方式、驗證結果（含「未驗證」）。另外兩區塊：「待你決定」與「換機器要重跑的指令」。
- [ ] **Step 3：bump 版號並同步 README、CHANGELOG**。CHANGELOG 寫明起因（使用者提出的需求）、常駐 description 增加的字數，以及 `setup/` 的 `--no-claude`。
- [ ] **Step 4：執行 `python3 scripts/ci/validate.py`**，預期 `✓ 11 個 plugin 驗證通過`。另跑 `wc -l SKILL.md`，預期小於 300。
- [ ] **Step 5：Commit**：`feat(workspace): project-setup skill（workspace 1.10.0）`

### Task 6：pi 查證與端到端驗收

**Files：**
- Modify：視查證結果，改 `references/flow.md` 的 pi 段與 `mirror.py`。
- Modify：`docs/agent-parity.md`（新增 project-setup 一列與 pi 的結論）

- [ ] **Step 1：查證 pi 讀不讀專案層 skill**。在暫存專案放 `.agents/skills/probe/SKILL.md`，也試 `.pi/skills/probe/SKILL.md`，用 pi 列出 skill。哪個路徑生效，`mirror.py` 就加對應的 link，同時補測試（先寫失敗測試再改）。兩個都不生效，就在 flow.md 和 agent-parity.md 標為已知缺口。
- [ ] **Step 2：端到端驗收**。在 scratchpad 用 `claude -p --plugin-dir plugins/workspace`，逐條跑 spec「驗收」的四個情境：
  - 空目錄＋「幫我做一個 .NET Web API」：裝了 backend／database，有 `AGENTS.md`，`CLAUDE.md` 只有一行，四個 CLI 都列得出 skill（Codex 用 `codex debug prompt-input` 看 skill roots；pi、agy 用各自列 skill 的方式），並交出清單。
  - 既有的無設定 repo：`git status` 是乾淨的。
  - 已有 `AGENTS.md` 的專案重跑：檔案內容 hash 不變。
  - 外部候選帶 hook：沒有被安裝，出現在「待你決定」。

  每條記下實際輸出；沒跑到的標「未驗證」。
- [ ] **Step 3：跑完整 CI 對應指令**：`python3 scripts/ci/validate.py`、各個 `test_*.py`、`bash setup/tests/install-project.sh`，預期全過。
- [ ] **Step 4：Commit**：`docs(workspace): project-setup pi 查證與 agent-parity`
