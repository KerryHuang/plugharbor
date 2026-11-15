# Session 塔台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 toolkit 加一座單機「塔台」：session 開工登記航班、追蹤改動、起飛提醒、進 main 前硬擋，並讓 unattended 可選接入。

**Architecture:** 核心是 `plugins/toolkit/skills/tower/scripts/tower.py`（純 Python 標準庫，CLI＋可 import 的函式），登記檔放 `<git-common-dir>/tower/flights/*.json`。Claude Code 上由三支 toolkit hook 自動呼叫它；其他 CLI 照 `toolkit:tower` skill 手動呼叫。

**Tech Stack:** Python 3 標準庫（不得依賴 pyyaml）、git CLI、Claude Code hooks（`hooks.json`）、pytest（hook 測試）、unittest 可直接 `python <檔>` 執行（skill 腳本測試，CI 用 `python "$t"` 跑）。

**Spec:** `docs/superpowers/specs/2026-11-15-session-tower-design.md`

## Global Constraints

- 只用標準庫；`.plugharbor/tower.yml` 自己解析（只認 `shared:` 下的 `- <glob>` 列）。
- 登記位置：`$(git rev-parse --git-common-dir)/tower/flights/<id>.json`；事件記 `tower/log.jsonl`；寫檔一律「寫暫存檔再 `os.replace`」。
- 航班對應：以 **worktree 絕對路徑＋分支** 找航班，同一 worktree 一次只有一班 `flying`。
- `host` 存 `sha256(hostname)[:8]`，不存原名。
- 心跳逾時 30 分鐘 → `lost`；`lost` 不參與提醒與硬擋，只在落地時對其碰過的檔印提醒。
- 共用跑道預設：`docs/feature.md`、`docs/roadmap.md`、`docs/todo.md`、`FEATURES.md`、`ROADMAP.md`、`TODO.md`、`**/CHANGELOG.md`；專案 `.plugharbor/tower.yml` 的 `shared:` 追加。
- `land-check` 退出碼：0 放行、10 超出申報、11 撞活航班、12 落後預設分支；多項同時成立時取 11 > 12 > 10。
- 撞活航班＝雙方**實際改動**（`git diff <merge-base>` 含工作區）交集，扣共用跑道；申報 `paths` 不參與硬擋。
- 超出申報：有對應 `overrides`（`kind: scope`）記錄就不再回 10。
- 無人值守：航班 `mode == "unattended"` 或環境變數 `AGENT_DISPATCH_UNATTENDED=1` 時，11 回 `deny`（附「排隊等航班 <id> 落地」），否則 11 回 `ask`；10、12 一律 `deny` 附放行方式。
- 本 session／worktree 沒有航班時，hook 只追蹤心跳以外什麼都不做，不擋。
- hook fail-open：任何例外 exit 0、不輸出；PostToolUse 與心跳 hook 單次目標 < 100ms（量測後記進 CHANGELOG）。
- 第一版硬擋只在 Claude Code；不做 git hook、不做跨機器同步。
- 版號：toolkit minor（0.23.x → 0.24.0）、workspace minor；CHANGELOG 起因寫「使用者實際遇過多 session 重工與衝突，未留文字紀錄（2026-11-15 裁決整套一次做完）」。
- 外洩：測試與文件不得出現個人絕對路徑、真實主機名。

## Review Focus

- 在 main 上直接 `git commit`（不是 merge）：要觸發 land-check —— Task 4 `test_commit_on_main_triggers`。
- 在 feature 分支 commit、`git push origin feat/x`：不得觸發 —— Task 4 `test_branch_commit_not_checked`、`test_push_non_default_not_checked`。
- 對方 worktree 已被刪掉但航班檔還在：land-check 不得當掉，該航班視為 `lost` —— Task 3 `test_missing_worktree_is_lost`。
- 航班檔損毀（半寫、非 JSON）：radar／land-check 略過並記 stderr，不當掉 —— Task 1 `test_corrupt_flight_skipped`。
- 不在 git repo 裡（`git rev-parse` 失敗）：所有 hook 靜默 exit 0 —— Task 4 `test_outside_git_repo_silent`。

---

### Task 1: 登記表與基本 CLI（takeoff／amend／beat／radar／landed／release／override）

**Files:**
- Create: `plugins/toolkit/skills/tower/scripts/tower.py`
- Test: `plugins/toolkit/skills/tower/scripts/test_tower.py`（unittest，`if __name__ == "__main__": unittest.main()`）

**Interfaces:**
- Produces:
  - `tower_dir(cwd: str) -> Path | None`（git common dir 下的 `tower/`；非 repo 回 None）
  - `Flight` 為 dict，欄位照 spec 第 1 節：`id, schema(=1), goal, work{segment,feature,ticket}, paths[], touched[], branch, worktree, session, cli, host, mode, started, beat, overrides[], state`
  - `load_flights(tdir: Path) -> list[dict]`（損毀檔略過、寫 stderr）
  - `save_flight(tdir: Path, f: dict) -> None`（原子寫）
  - `find_flight(tdir: Path, worktree: str) -> dict | None`（`state == "flying"`）
  - `log_event(tdir: Path, kind: str, **fields) -> None`
  - CLI：`tower.py takeoff --goal G --paths P... [--segment S] [--feature F] [--ticket T] [--mode unattended] [--session ID] [--cli NAME]` 印 JSON `{"id":..., "overlaps":[...]}`；`amend [--goal] [--paths...]`；`beat [--touched FILE...]`；`radar [--json]`；`override --kind scope --reason R`；`landed`；`release`。後六者以目前 worktree 找航班，可用 `--id` 指定。

- [ ] **Step 1: 寫失敗測試**（每個測試在 `tempfile` 建 `git init` repo，HOME 指到 tmp）
  - `test_takeoff_creates_flight_in_git_common_dir`：檔案在 `.git/tower/flights/`，`state == "flying"`、`schema == 1`、`host` 長度 8 且 ≠ hostname。
  - `test_worktree_shares_board`：`git worktree add` 出第二個 worktree，在那裡 `radar --json` 看得到第一班。
  - `test_second_takeoff_same_worktree_rejected`：同 worktree 已有 flying 時 takeoff 退出碼 2、訊息含現有航班 ID。
  - `test_beat_updates_time_and_touched`：`beat --touched a.py` 後 `touched == ["a.py"]`（去重、相對 repo 根）。
  - `test_release_deletes_file_and_logs`：檔案消失，`log.jsonl` 末行 `kind == "release"`。
  - `test_corrupt_flight_skipped`：放一個內容為 `{` 的 json，`radar` 退出碼 0、stderr 提到檔名。
- [ ] **Step 2:** `python plugins/toolkit/skills/tower/scripts/test_tower.py` → FAIL（找不到 tower.py）
- [ ] **Step 3:** 實作上列介面；ID 格式 `YYYYMMDD-HHMM-<4 hex>`；時間存 UTC ISO8601。
- [ ] **Step 4:** 同一指令 → 全部 PASS
- [ ] **Step 5: Commit**（worktree 分支上，訊息 `feat(tower): 登記表與基本 CLI`）

### Task 2: 重疊判斷、共用跑道、失聯

**Files:**
- Modify: `plugins/toolkit/skills/tower/scripts/tower.py`
- Test: `plugins/toolkit/skills/tower/scripts/test_tower.py`

**Interfaces:**
- Consumes: Task 1 全部
- Produces:
  - `shared_globs(repo_root: Path) -> list[str]`（預設＋`.plugharbor/tower.yml`）
  - `match(path: str, glob: str) -> bool`（`**` 跨目錄、`*` 不跨 `/`）
  - `is_lost(f: dict, now: datetime) -> bool`（`beat` 超過 30 分鐘，或 `worktree` 路徑已不存在）
  - `overlaps(me: dict, others: list[dict], shared: list[str]) -> list[dict]`，每筆 `{"flight": id, "goal":..., "kind": "work"|"path", "detail": [...]}`；takeoff 與 `beat` 的輸出都帶它

- [ ] **Step 1: 寫失敗測試**
  - `test_same_segment_is_work_overlap`：兩班 `--segment a7` → `kind == "work"`。
  - `test_same_feature_or_ticket_is_work_overlap`（兩個子案例）。
  - `test_path_overlap_glob`：A `paths=["plugins/toolkit/**"]`、B `touched=["plugins/toolkit/hooks/x.py"]` → `kind == "path"`。
  - `test_shared_runway_excluded`：雙方都碰 `docs/feature.md`、`plugins/a/CHANGELOG.md` → 無重疊。
  - `test_project_shared_config`：`.plugharbor/tower.yml` 寫 `shared:\n  - README.md` 後，`README.md` 重疊被排除。
  - `test_lost_flight_not_overlap`：B 的 `beat` 設為 31 分鐘前 → 無重疊，radar 顯示 `lost`。
  - `test_missing_worktree_is_lost`：B 的 worktree 路徑不存在 → `is_lost` 為 True。
- [ ] **Step 2:** 跑測試 → 新案例 FAIL
- [ ] **Step 3:** 實作；`match` 用自寫轉 regex（`**/` → `(?:.*/)?`、`**` → `.*`、`*` → `[^/]*`），不用 `fnmatch`（它的 `*` 會跨 `/`）。
- [ ] **Step 4:** 跑測試 → PASS
- [ ] **Step 5: Commit** `feat(tower): 重疊判斷、共用跑道與失聯`

### Task 3: land-check

**Files:**
- Modify: `plugins/toolkit/skills/tower/scripts/tower.py`
- Test: `plugins/toolkit/skills/tower/scripts/test_tower.py`

**Interfaces:**
- Consumes: Task 1、2
- Produces:
  - `default_branch(repo: Path) -> str`（`origin/HEAD` 指向者；沒有遠端就 `main`，再退 `master`）
  - `actual_changes(worktree: Path, base_branch: str) -> set[str]`（`git diff --name-only <merge-base>` ∪ `git diff --name-only` ∪ `git diff --name-only --cached` ∪ untracked）
  - `land_check(tdir, me) -> dict`：`{"code": 0|10|11|12, "scope_extra": [...], "collisions": [{"flight", "goal", "files"}], "behind": bool, "warnings": [...]}`
  - CLI `land-check [--id]`：印上面 JSON，退出碼＝`code`

- [ ] **Step 1: 寫失敗測試**
  - `test_clean_land_returns_0`：改動都在 `paths` 內、無他班、已含 main 最新 → 0。
  - `test_scope_extra_returns_10`：改了 `paths` 外的 `x.txt` → 10、`scope_extra == ["x.txt"]`。
  - `test_override_clears_10`：`override --kind scope --reason r` 後 → 0。
  - `test_collision_actual_changes_returns_11`：B 在自己 worktree 改了 `a.py`（未 commit），A 也改 `a.py` → 11、`collisions[0]["files"] == ["a.py"]`。
  - `test_declared_only_not_collision`：B 只申報 `paths=["a.py"]` 沒改 → A 改 `a.py` 不回 11。
  - `test_behind_main_returns_12`：main 前進一個 commit、A 分支沒 rebase → 12。
  - `test_priority_11_over_12_over_10`：三者同時成立 → 11。
  - `test_shared_runway_not_collision`：雙方都改 `docs/feature.md` → 非 11。
  - `test_lost_flight_touch_is_warning`：B lost 且碰過 `a.py` → code 非 11、`warnings` 含 B 的 ID。
  - `test_feature_not_checked_warning`：航班 `feature="塔台"`，`docs/feature.md` 該行仍 `- [ ] 📋` → `warnings` 含「feature.md」；改成 `- [x]` 後無此警告。
- [ ] **Step 2:** 跑測試 → FAIL
- [ ] **Step 3:** 實作；有遠端時先 `git fetch --quiet`？**不做**（hook 內不可聯網）——「落後」只比本機 `origin/<預設>` 與本機 `<預設>` 兩者中較新的那個。
- [ ] **Step 4:** 跑測試 → PASS
- [ ] **Step 5: Commit** `feat(tower): land-check 落地核對`

### Task 4: Claude Code hooks

**Files:**
- Create: `plugins/toolkit/hooks/tower-track.py`、`plugins/toolkit/hooks/tower-landing.py`、`plugins/toolkit/hooks/tower-context.py`
- Modify: `plugins/toolkit/hooks/hooks.json`
- Test: `plugins/toolkit/hooks/tests/test_tower_hooks.py`（pytest，照 `test_guard.py` 用 tmp_path 與 subprocess 餵 stdin）

**Interfaces:**
- Consumes: `tower.py` 以 `sys.path.insert(0, PLUGIN/"skills/tower/scripts")` import
- Produces（hooks.json 註冊）:
  - `PreToolUse` matcher `.*` 與 `UserPromptSubmit`：`tower-track.py beat`（只更新 `beat` 時間戳，不開 git 子程序；以 `cwd` 向上找 `.git` 檔／目錄定位，worktree 的 `.git` 檔要讀 `gitdir:`）
  - `PostToolUse` matcher `Edit|Write|MultiEdit`：`tower-track.py touch`，記 `tool_input.file_path`，與他班重疊時輸出 `additionalContext` 一行提醒
  - `PreToolUse` matcher `Bash`：`tower-landing.py`
  - `SessionStart`：`tower-context.py`，有航班時輸出一行（≤ 120 字）摘要，沒有就無輸出
  - 每條 `timeout: 5`

- [ ] **Step 1: 寫失敗測試**
  - `test_commit_on_main_triggers`：目前分支 main、有航班且超出申報，`git commit -m x` → `permissionDecision == "deny"`、理由含「override」。
  - `test_branch_commit_not_checked`：分支 `feat/x` 上 `git commit` → 無輸出。
  - `test_merge_into_main_triggers`：在 main 上 `git merge feat/x` → 觸發。
  - `test_push_default_triggers` / `test_push_non_default_not_checked`：`git push origin main` 觸發、`git push origin feat/x` 不觸發。
  - `test_collision_asks_when_attended` / `test_collision_denies_when_unattended`：11 時無訊號回 `ask`；`AGENT_DISPATCH_UNATTENDED=1` 或航班 `mode=unattended` 回 `deny` 且理由含「排隊」。
  - `test_no_flight_no_block`：無航班時任何指令無輸出。
  - `test_touch_records_and_warns`：PostToolUse 寫入他班改過的檔 → 航班 `touched` 更新、輸出含他班 ID。
  - `test_beat_fast`：`beat` 100 次平均耗時記錄到 stdout（不設硬門檻，結果貼進 CHANGELOG）。
  - `test_outside_git_repo_silent`：三支 hook 在非 repo 目錄 exit 0、無輸出。
  - `test_session_start_summary`：兩班在飛 → 輸出一行含「2 班」；無航班 → 空。
- [ ] **Step 2:** `python -m pytest plugins/toolkit/hooks/tests/test_tower_hooks.py -v` → FAIL
- [ ] **Step 3:** 實作；進 main 判斷：解析指令中的 `git commit`（且 `git branch --show-current` 是預設分支）、`git merge`／`git rebase`（目前分支是預設分支）、`git push <remote> <預設分支>`（或目前在預設分支且沒指定 refspec）。
- [ ] **Step 4:** 跑測試 → PASS；再跑 `python -m pytest plugins/toolkit/hooks/tests -v` 確認 `test_manifest.py` 等既有測試仍過
- [ ] **Step 5: Commit** `feat(toolkit): tower hooks——心跳、改動追蹤、進 main 前核對`

### Task 5: tower skill、文件與版號

**Files:**
- Create: `plugins/toolkit/skills/tower/SKILL.md`（< 300 行；description 一句含觸發詞「塔台」「tower」「別的 session 在做什麼」「開工登記」）
- Create: `.plugharbor/tower.yml`（plugharbor 自用：`shared:` 加 `.claude-plugin/marketplace.json`、`README.md`、`plugins/*/.claude-plugin/plugin.json`）
- Modify: `plugins/toolkit/README.md`、根 `README.md`（skills 與 agents 表、版本欄）、`plugins/toolkit/CHANGELOG.md`、`plugins/toolkit/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`docs/agent-parity.md`（toolkit hook 對照表加三支 tower hook：Claude ✅、其他「無，照 skill 手動」）、`AGENTS.md`「並行」條、`docs/feature.md`（📋 → 🚧，合併後 → [x]）

- [ ] **Step 1:** SKILL.md 內容：何時 takeoff（開工、有對應段號／功能名／票號就帶）、看到重疊怎麼回報使用者（只提醒，由使用者選等／協作／照飛）、範圍變了 amend、落地被擋三種退出碼各怎麼處理（10 補 override 理由、11 有人在場請使用者確認／無人值守排隊、12 rebase 後重試）、收工 release、有裝 tickets 用 `ticket-ops` 更新票、非 Claude Code CLI 要手動跑 land-check 並標「此 CLI 沒有自動追蹤、沒有硬擋」。
- [ ] **Step 2:** AGENTS.md「並行」條改為：有裝 toolkit 時看 `tower.py radar`，沒有時照舊 `git worktree list`／`git branch -a --no-merged origin/main`（長度不變胖：同行替換）。
- [ ] **Step 3:** 用 `release-plugin` skill 把 toolkit bump 到 0.24.0（三處同步），CHANGELOG 寫起因與 Task 4 量到的 hook 延遲。
- [ ] **Step 4:** `python3 scripts/ci/validate.py` → 「驗證通過」；toolkit:skill-reviewer agent 審 SKILL.md 無阻擋項
- [ ] **Step 5: Commit** `feat(toolkit): tower skill 與文件（toolkit 0.24.0）`

### Task 6: unattended 可選接入（workspace）

**Files:**
- Modify: `plugins/workspace/skills/unattended/SKILL.md`（第 2 節合併步驟、第 6 節回來報告）、`plugins/workspace/skills/unattended/references/autopilot.md`（排線、換新 session）、`plugins/workspace/CHANGELOG.md`、版號三處

- [ ] **Step 1:** 寫入規則（每條一行，有裝 toolkit:tower 才適用，沒裝照舊）：
  - 開工單元：在單元 worktree 跑 `takeoff --mode unattended`，帶段號；航班 ID 記帳本。
  - 排線：`radar --json` 中他班 flying 航班持有的段號，或其 `paths`／`touched` 與本段 spec 預估檔案交集（扣共用跑道）的段，不列入可開工；記主控裁決。
  - 起飛回 `kind: work` 重疊 → 跳過此段；`kind: path` → 當共用檔照順序。
  - 合併：land-check 10 → `override` 補理由；11 → 帳本記 `空檔：等航班 <id> 落地`，做別的；12 → rebase、重跑閘門後重試。
  - 單元清 worktree 前 `release`。
  - 換新 session：沿用（以 worktree 找到原航班），不重新 takeoff。
  - 回來報告加「塔台紀錄」一節，來源 `log.jsonl` 本次帳本期間的事件。
- [ ] **Step 2:** SKILL.md 仍 < 300 行；`validate.py` 通過；workspace minor bump、CHANGELOG
- [ ] **Step 3: Commit** `feat(unattended): 可選接入 session 塔台（workspace 1.17.0）`

### Task 7: 端到端試用（push 前）

- [ ] **Step 1:** 建兩個 worktree，各用 `claude -p --plugin-dir plugins/toolkit` 跑：
  1. A takeoff `--segment t1`；B takeoff `--segment t1` → B 輸出含 work 重疊提醒。
  2. A、B 都改 `x.txt` 未 commit，A 切 main 合併 → 被 `ask`（有人在場）。
  3. A 改 `paths` 外的檔、在 main 上 commit → 被 `deny`，`override` 後通過。
- [ ] **Step 2:** 把三個情境的實際輸出貼進 `.tmp/20261115-session-tower/e2e.md`，不符就回對應 Task 修。
- [ ] **Step 3:** 全套：`python3 scripts/ci/validate.py`、`python -m pytest plugins/toolkit/hooks/tests -v`、`python plugins/toolkit/skills/tower/scripts/test_tower.py`。
- [ ] **Step 4:** 合併進 main：版號規則要求「改 skills 的 commit 同時有 CHANGELOG＋bump」——worktree 分支以 squash 合成**單一 commit** 進 main（訊息 `feat(toolkit): session 塔台（toolkit 0.24.0、workspace 1.17.0）`）；push 另外問使用者。
