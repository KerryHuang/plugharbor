# agent 暫存生命週期 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** toolkit 新增 `scratch-ledger.py`：暫存建立時標記、結束時記帳、開場提議刪除、全區掃描兜底，本身不刪檔。

**Architecture:** 一支 Python hook 腳本，依 stdin payload 的 `hook_event_name` 分派 PostToolUse／SessionEnd／SessionStart；帶 argv 時是 CLI（`mark`、`keep`、`sweep`）。狀態全在 `~/.claude/scratch-ledger/`（`ledger.jsonl` 只追加、`state.json`、`sessions/<sid>.seen`）。

**Tech Stack:** Python 3 標準庫；pytest（`plugins/toolkit/hooks/tests/`）。

**Spec:** `docs/superpowers/specs/2026-11-19-agent-scratch-lifecycle-design.md`

## Global Constraints

- 常數：預設期限 7 天；`ttl` 只收 `1d`、`7d`、`handoff`；keep 7 天；未標記與交接檔閒置 14 天才列；磁碟可用 < 20 GB；掃描間隔 7 天；開場最多列 4 個；SessionEnd 量大小共用 0.5 秒。
- 狀態根：`os.path.expanduser("~/.claude/scratch-ledger")`（測試以 `HOME` 改向）。
- fail-open：任何例外寫 stderr、exit 0；hook 不刪使用者檔案（只刪自己的 `sessions/<sid>.seen`）。
- 無人值守（`AGENT_DISPATCH_UNATTENDED=1`）SessionStart 不注入。
- hooks.json 指令格式 `sh "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" scratch-ledger.py`，`commandWindows` 依 `test_hooks_windows.py` 樣板產生。

## Review Focus

- 路徑含空白與中文的專案（`專案 根/.tmp/x`）→ 單位判定與帳本照常（Task 1 測試用此路徑）。
- 帳本有壞行或空檔 → 跳過壞行，不中斷（Task 1 `test_fold_skips_bad_lines`）。
- 並行 session 還在用的單位 → 開場不列（Task 3 `test_open_session_not_proposed`）。
- `.tmp` 下的裸檔、`.tmp` 本身 → 不算單位（Task 1 `test_unit_of`）。
- 資料夾已被刪 → 開場、掃描都略過；SessionEnd 不寫 end（Task 2、3）。

---

### Task 1: 單位判定、帳本、PostToolUse 標記、`mark` CLI

**Files:**
- Create: `plugins/toolkit/hooks/scratch-ledger.py`
- Test: `plugins/toolkit/hooks/tests/test_scratch_ledger.py`

**Interfaces:**
- Produces: `unit_of(path: str) -> str | None`（第一個 `.tmp`／`.superpowers` 往下一層的絕對路徑）；`bash_units(command: str, cwd: str) -> list[str]`；`append(ev: dict)`；`fold() -> dict[str, Rec]`，`Rec` 含 `created, purpose, ttl, last_ts, open_sessions: set, sessions: set, last_end_reason, size, keep_until`；`main(argv)`。測試以 subprocess 執行腳本（stdin JSON、`HOME` 指到暫存目錄）。

- [ ] **Step 1: 寫失敗測試**：`test_unit_of`（`/p/.tmp/a/b.txt`→`/p/.tmp/a`；`/p/.tmp/x.txt`→None；`/p/.tmp`→None；`/p/.superpowers/brainstorm/1/x`→`/p/.superpowers/brainstorm`）、`test_bash_units`（`cat .tmp/a/x && ls ../q/.tmp/b` 以 cwd 解開）、`test_write_marks_and_injects_once`（Write 到新單位 → 帳本一筆 mark、輸出含 `additionalContext` 與 `mark`；同 session 再寫 → 無輸出、帳本不增）、`test_other_session_touches_silently`、`test_missing_session_id_noop`、`test_mark_cli_sets_meta`（`mark <相對路徑> --purpose x --ttl 1d` → meta 一筆；`--ttl 3d` exit 2；非單位 exit 2）、`test_fold_skips_bad_lines`。
- [ ] **Step 2:** `python3 -m pytest plugins/toolkit/hooks/tests/test_scratch_ledger.py -q` → FAIL（檔案不存在）。
- [ ] **Step 3: 實作**：PostToolUse 只處理 `Write|Edit|MultiEdit|NotebookEdit|Bash`；單位需為存在的資料夾；`sessions/<sid>.seen` 一行一路徑。
- [ ] **Step 4:** 同指令 → PASS。

### Task 2: SessionEnd 記帳

**Interfaces:** Consumes Task 1 `fold`、`append`。Produces `dir_size(path, deadline: float) -> (int, bool partial)`。

- [ ] **Step 1: 失敗測試**：`test_session_end_records_size`（本 session mark 過的單位 → end 一筆含 `size`、`reason`，`.seen` 被刪）、`test_session_end_skips_deleted_dir`、`test_session_end_ignores_other_sessions`、`test_dir_size_partial_on_deadline`（deadline 已過 → partial True）。
- [ ] **Step 2–4:** FAIL → 實作 → PASS。

### Task 3: SessionStart 開場提議與 `keep`

**Interfaces:** Produces `candidates(root: str, now) -> list[dict]`（含 `dir, size, idle_days, purpose, worktree: bool, deliverable: bool`）、`warnings(dir)`。

- [ ] **Step 1: 失敗測試**：`test_expired_proposed`（end 後把帳本時間改到 8 天前且 mtime 調舊 → 注入含路徑、`multiSelect`、`keep`）、`test_not_expired_silent`、`test_ttl_1d`、`test_open_session_not_proposed`、`test_handoff_excluded`（ttl handoff／end reason clear／含 `handoff.md` 三種）、`test_keep_suppresses_and_marks_asked`（`keep --root R <dir>` 後不列；不帶路徑也記今天問過 → 當天不再注入）、`test_top4_by_size`（6 個 → 列 4 個且提「其餘 2 個」）、`test_worktree_and_deliverable_flags`、`test_source_resume_and_unattended_silent`、`test_recent_mtime_not_proposed`。
- [ ] **Step 2–4:** FAIL → 實作 → PASS。

### Task 4: 全區掃描 `sweep` 與掃描提議

**Interfaces:** Produces `sweep(roots: list[str], now) -> list[dict]`（`kind` ∈ `expired|unmarked|abandoned|handoff`）、CLI `sweep [--json] [--skip] [--root R]...`。

- [ ] **Step 1: 失敗測試**：`test_sweep_nudge_when_never_swept`、`test_sweep_nudge_suppressed_after_skip`、`test_sweep_nudge_low_disk`（以環境變數 `SCRATCH_LEDGER_FREE_GB` 模擬可用空間，僅測試用）、`test_sweep_classifies`（未標記 15 天→unmarked、未標記 3 天不列、有 mark 無 end 且閒置過期→abandoned、handoff 15 天→handoff）、`test_sweep_prunes_missing_dirs`、`test_sweep_is_read_only`（掃描前後檔案樹相同）、`test_sweep_json`。
- [ ] **Step 2–4:** FAIL → 實作 → PASS。

### Task 5: 註冊、文件、版號

**Files:** `plugins/toolkit/hooks/hooks.json`、`hooks/tests/test_agent_model_guard.py`（python hook 數 25 → 28）、`plugins/toolkit/README.md`、`docs/agent-parity.md`、`plugins/toolkit/CHANGELOG.md`、`plugin.json`、`.claude-plugin/marketplace.json`、根 `README.md`、`docs/feature.md`。

- [ ] PostToolUse 新增 matcher `Write|Edit|MultiEdit|NotebookEdit|Bash`；SessionEnd 新增一組（timeout 3）；SessionStart `startup` 加一條。
- [ ] `python3 -m pytest plugins/toolkit/hooks/tests -q` 全過；`python3 scripts/ci/validate.py` 過。
- [ ] toolkit 0.32.0（feat）；commit。

### Task 6: 實觸發驗收

- [ ] 拋棄式目錄 `D`（scratchpad 內，git init），`HOME` 不改、改用 `--plugin-dir plugins/toolkit`，濾掉 `HERDR_*`、`HC_*`：`claude -p "在 .tmp/20261119-probe/ 寫一個 a.txt"` → 帳本有 mark、end（`reason`）。
- [ ] 把該單位帳本時間改到 8 天前、mtime 調舊，再 `claude -p "說 hi"` 並以 `--debug` 或 transcript 確認 SessionStart 注入提議文字。
- [ ] `sweep --root <scratchpad>` 實跑；對 `~/Work/projects` 只跑 `sweep --json`（唯讀）看分類是否合理，不刪任何檔。
- [ ] 結果寫進結果檔；跑不到的標未驗證。
