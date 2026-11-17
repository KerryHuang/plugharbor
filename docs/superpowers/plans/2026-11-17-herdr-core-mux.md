# 派工層支援 Herdr.app（herdr-core）實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增轉接腳本 `mux.py`，讓 plugharbor 的派工層（agent-dispatch、雙顧問、self-rotate、hook、setup 規則）在 Herdr.app（`hc`）與 herdr TUI（`herdr`）都能運作。

**Architecture:** 一支純標準庫 Python 腳本偵測後端、把固定動作翻成 `hc` 或 `herdr` 指令並輸出 JSON。文件與腳本只呼叫 `mux.py`；hook 內嵌同一條輕量判斷。hc 下的版面、session id、狀態回報各自補一個小元件。

**Tech Stack:** Python 3 標準庫（unittest）、POSIX sh、Node 22（`node --test`）、Claude Code plugin 結構。

**Spec:** `docs/superpowers/specs/2026-11-17-herdr-core-mux-design.md`（執行者兩份都要讀）

## Global Constraints

- worktree：repo 同層的 `../plugharbor-herdr-core`，分支 `feat/herdr-core-mux`；所有指令在此執行。
- 公開 repo：不得出現個人絕對路徑（使用者家目錄開頭的路徑）、email、公司名；commit 前 `python3 scripts/ci/validate.py` exit 0。
- 改 `skills/`、`agents/`、`references/`、`templates/` 的 commit 內同步 CHANGELOG＋三處版號（`plugin.json`、`.claude-plugin/marketplace.json`、根 `README.md`）。
- SKILL.md ≤ 300 行；skill／agent description、setup 的 home 目錄規則不得變長。
- 每個 plugin 可單獨安裝：跨 plugin 共用檔複製一份並登記 `scripts/ci/shared-copies.json`。
- **core 沒跑時不得呼叫任何 `hc` 指令**（會以呼叫者環境自動啟動 core）；測試一律用 PATH stub，或獨立 `HC_SESSION`＋暫存 `XDG_*` 路徑。不得 `hc server stop/restart` 使用者的 core。
- 逐檔 `git add`；commit 訊息照 repo 慣例（中文 Conventional Commits）結尾附 attribution。
- 跨 plugin 測試慣例：`plugins/**/test_*.py` 以 `python <檔>` 跑（unittest）；shell 測試放 `tests/*.sh`；hook 測試放 `plugins/toolkit/hooks/tests/`（pytest 跑）。

## Review Focus

1. **兩組環境變數同時存在**（core 在 TUI 內啟動）：要判成 hc，不得呼叫 `herdr` → Task 1 `test_both_sets_prefers_nearest_ancestor`、`test_both_sets_unknown_ancestry_defaults_hc`。
2. **core 沒在跑**：`mux.py` 任何動作都不得執行 `hc`，回 `core_not_running` → Task 1 `test_core_not_running_never_calls_hc`。
3. **送 slash command 到自己終端被包成 `<hc …>` 標籤**：self-rotate 的 `/clear` 失效 → Task 1 `test_send_strips_hc_terminal_id`、Task 4 hc stub 版測試。
4. **worker 繼承 core 的污染變數**（`CLAUDE_CODE_CHILD_SESSION`、`HERDR_*`）→ Task 1 `test_spawn_hc_unsets_polluted_env`。
5. **app 視窗沒開**：spawn 不失敗、回 `visible:false`，主 session 不被動到 → Task 3 `test_spawn_without_window_stays_hidden`。

---

### Task 0: Spike — 實測 hc／app 行為（需使用者開著 Herdr.app）

**前置：** 使用者已從 Dock 開 Herdr.app（core 以乾淨環境啟動）；執行者在 app 的終端內操作。先 `pgrep -fl herdr-core` 確認有跑，沒跑就停下回報。

**Files:**
- Create: `docs/superpowers/specs/2026-11-17-herdr-core-mux-spike.md`

**Interfaces:**
- Produces：spike 筆記，後續任務引用其結論。每項記「指令、原始輸出摘要、結論」。

- [ ] **Step 1：逐項實測並記錄**
  1. 不自動啟動 core 的檢查法：`hc` 有無旗標／環境變數可禁止自動啟動；否則確認 socket（`~/.local/state/herdr-core/default/default.sock`）可連線判斷法可靠。
  2. 四種 CLI 狀態：各 `hc run --bg --no-notify --name s-<kind> <cli> <最小參數>`（codex 加 `--no-daemon`），送一句短任務，`hc get --json` 看 `status` 是否經過 `working`→`idle|done`。記錄哪些沒有 status。
  3. OSC 7501 格式：從 `hc --skill`、`hc schema`、herdr-core repo 查明 escape 序列與欄位；用 `printf` 在一個 hc 終端送出驗證 `status` 改變。
  4. `<hc from>` 包裝：從 hc 終端 `hc send s-claude "測試"`，與 `env -u HC_TERMINAL_ID hc send s-claude "測試"` 比較 Claude 畫面上收到的文字。
  5. self-send：在 claude 終端內背景跑 `env -u HC_TERMINAL_ID hc send "$HC_TERMINAL_ID" /status`，確認 slash command 原樣生效。
  6. 版面：`herdr-app ls`／`status` 取主 session 的 pane 與 tab；試 `herdr-app do terminal.open --place right --target <pane> --argv '[...]'` 與 `hc run` 加 `herdr.space`／`herdr.tab` label 兩法，記錄哪個能把 worker 放在主 pane 右側、回傳哪些 ID、能否指定比例（`layout.resize`、`pane.swap`）。
  7. 關閉：`hc kill`＋`hc rm` 後視窗格是否消失；否則要 `pane.close`。
  8. `env -u … K=V <cli>` 前綴在 `hc run` argv 下可用（K 進得去、被 unset 的變數不見）。
  9. 視窗沒開時 `herdr-app status` 的 exit code 與訊息。
- [ ] **Step 2：與 spec 比對**：任一結論推翻 spec 的決定（例如移除 `HC_TERMINAL_ID` 仍被包裝、某 CLI 無任何擴充點），停下把差異寫在筆記頂端並回報主控，不往下做。
- [ ] **Step 3：Commit**：`git add docs/superpowers/specs/2026-11-17-herdr-core-mux-spike.md`；`docs: 記錄 herdr-core spike 結果`。

---

### Task 1: `mux.py` 核心（偵測＋兩個後端＋共用動作）

**Files:**
- Create: `plugins/toolkit/skills/agent-dispatch/scripts/mux.py`（正本；spec 寫 `plugins/toolkit/scripts/`，改放 skill 的 scripts 以符合 repo 慣例，hook 以 `${CLAUDE_PLUGIN_ROOT}/skills/agent-dispatch/scripts/mux.py` 引用）
- Test: `plugins/toolkit/skills/agent-dispatch/scripts/test_mux.py`

**Interfaces:**
- Produces（CLI，stdout 為 JSON，`read` 例外為純文字）：
  - `mux.py env` → `{"backend":"hc"|"herdr"|"none","self":str|null,"window":bool}`
  - `mux.py spawn --name N --kind claude|codex|agy|pi --cwd DIR [--env K=V]... -- <CLI 參數...>` → `{"id":str,"visible":bool}`
  - `mux.py send ID (--text T | --file F) [--wait] [--timeout SEC]` → `{"status":S,"raw":any}`
  - `mux.py wait ID [--timeout SEC]` → `{"status":S,"raw":any}`
  - `mux.py read ID [--lines N]` → 畫面文字
  - `mux.py alive ID` → `{"alive":bool}`
  - `mux.py session ID` → `{"session":str|null}`（hc 部分 Task 2 實作，本任務先回 `null`）
  - `mux.py close ID` → `{"closed":true}`
  - `mux.py attach-hint ID` → `{"hint":str}`
  - `S` ∈ `done|idle|working|blocked|error|timeout|gone`
  - 錯誤：stderr／stdout 輸出 `{"error":kind,"hint":str}`；exit 2 用法錯、3 `core_not_running`、4 `no_backend`、1 其他。
  - Python 函式（供測試與 Task 2–3 import）：`detect_backend(env: dict, ancestors: list[int] | None = None, hc_pid: int | None = None, herdr_pid: int | None = None) -> str`、`core_running() -> bool`、`clean_env_prefix(extra: dict[str,str]) -> list[str]`（回 `["env","-u",…,"K=V"]`）、`POLLUTED_VARS: tuple[str,...]`。
  - `MUX_BACKEND` 環境變數強制後端。

- [ ] **Step 1：寫失敗測試**（unittest；每個後端用暫存目錄放 stub `hc`／`herdr` shell 腳本，把 `$*` 追加到 log 並回固定 JSON，`PATH` 前置該目錄；`core_running` 以環境變數 `MUX_CORE_SOCKET` 指向暫存路徑控制，存在即視為在跑）
  - `test_hc_only` → `detect_backend({"HC_TERMINAL_ID":"t1"}) == "hc"`
  - `test_herdr_only` → `{"HERDR_ENV":"1","HERDR_PANE_ID":"w:p1"}` → `"herdr"`
  - `test_herdr_env_without_pane_id_is_none` → `{"HERDR_ENV":"1"}` → `"none"`
  - `test_both_sets_prefers_nearest_ancestor`：ancestors `[100, 200, 300]`、`hc_pid=300`、`herdr_pid=200` → `"herdr"`；對調 → `"hc"`
  - `test_both_sets_unknown_ancestry_defaults_hc`：兩個 pid 皆 `None` → `"hc"`
  - `test_mux_backend_override`：`MUX_BACKEND=none` 蓋過其他變數
  - `test_core_not_running_never_calls_hc`：backend hc、socket 不存在，跑 `send t1 --text x` → exit 3、`hc` stub log 為空
  - `test_send_strips_hc_terminal_id`：stub `hc` 把自身環境的 `HC_TERMINAL_ID` 寫進 log；`mux.py send t2 --text hi` 後 log 中該值為空
  - `test_spawn_hc_unsets_polluted_env`：stub 記錄 argv；`spawn --name w1 --kind claude --cwd /tmp --env A=1 -- --model m` 的 `hc run` argv 含 `--bg`、`--no-notify`、`--name w1`，且其後依序為 `env`、`-u CLAUDECODE`、`-u CLAUDE_CODE_CHILD_SESSION`、`-u HERDR_ENV`、`-u HERDR_PANE_ID`、`A=1`、`claude`、`--model`、`m`
  - `test_spawn_codex_adds_no_daemon`：kind codex 的 argv 含 `--no-daemon`
  - `test_spawn_herdr_sequence`：herdr 後端 log 依序含 `pane split --current --direction right --cwd /tmp --no-focus --env A=1`、`herdr_layout.py`（stub 掉，以 `MUX_LAYOUT_CMD` 環境變數指向假腳本）、`agent start w1 --kind claude --pane <stub 回的 pane_id> -- --model m`、`pane rename <pane_id> w1`
  - `test_send_wait_status_mapping`：herdr `agent prompt … --wait --timeout 540000`（秒→毫秒換算）回各原始狀態，hc `send --wait --timeout 540` 回各原始狀態，輸出 `status` 皆落在 `S` 集合；未知值 → `error` 且 `raw` 保留
  - `test_send_file_reads_content`：`--file` 內容含反引號與 `$()`，stub 收到原字串
  - `test_wait_and_read_and_alive_and_close` 兩後端各一：指令對應 spec「動作」表
  - `test_attach_hint`：herdr → 含 `herdr agent attach`；hc → 含 `hc attach`
  - `test_none_backend_errors`：backend none 時除 `env` 外皆 exit 4
- [ ] **Step 2：跑測試確認失敗**：`python3 plugins/toolkit/skills/agent-dispatch/scripts/test_mux.py` → FAIL（找不到 mux.py）
- [ ] **Step 3：實作 `mux.py`**：argparse 子指令；後端類別 `HcBackend`／`HerdrBackend` 各實作同名方法；`POLLUTED_VARS` 與 `plugins/toolkit/skills/agent-mesh-check/scripts/clis.mjs` 的 `scrubEnv` 清單一致（`CLAUDECODE`、`CLAUDE_CODE_*` 中已知名稱、`HERDR_ENV`、`HERDR_PANE_ID`、`HERDR_SOCKET_PATH`、`HERDR_TAB_ID`、`HERDR_WORKSPACE_ID`、`HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`HC_SCOPE`）；祖先鏈用 `ps -o ppid= -p` 迴圈取得；`core_running` 依 Task 0 結論實作（預設檢查 `MUX_CORE_SOCKET` 或 Task 0 確認的 socket 路徑可連線）；hc 的視窗放置先只做「無 label、`visible:false`」，Task 3 再補；stdout UTF-8 reconfigure 比照 `herdr_layout.py`。
- [ ] **Step 4：跑測試確認通過**：同上指令 → `OK`
- [ ] **Step 5：Commit**：add `mux.py`、`test_mux.py`、toolkit CHANGELOG／版號（minor：0.25.0）；`feat(toolkit): 新增 mux.py 轉接 hc 與 herdr`

---

### Task 2: hc 下的 session id 記錄

**Files:**
- Modify: `plugins/toolkit/hooks/herdr-env-context.py`（同一個 SessionStart hook 多做一件事）
- Modify: `plugins/toolkit/skills/agent-dispatch/scripts/mux.py`（`session` 的 hc 分支）
- Test: `plugins/toolkit/hooks/tests/test_herdr_env_context.py`、`test_mux.py`

**Interfaces:**
- Consumes：Task 1 的 `HcBackend`。
- Produces：檔案 `${XDG_STATE_HOME:-$HOME/.local/state}/plugharbor/hc-sessions/<HC_TERMINAL_ID>`，內容為單行 session id；`mux.py session ID` 先 `hc get ID --json` 取 `address` 再讀此檔，不存在回 `null`。

- [ ] **Step 1：寫失敗測試**
  - hook：`test_records_session_id_under_hc`：環境 `HC_TERMINAL_ID=t5`、`XDG_STATE_HOME=<tmp>`，stdin 給 `{"session_id":"abc"}` → 檔案 `<tmp>/plugharbor/hc-sessions/t5` 內容 `abc`
  - hook：`test_no_record_without_hc`：只有 `HERDR_ENV=1` → 不建檔
  - hook：`test_record_overwrites_after_clear`：連跑兩次（`abc`、`def`）→ 內容 `def`
  - mux：`test_session_hc_reads_file`／`test_session_hc_missing_returns_null`
- [ ] **Step 2：跑測試確認失敗**：`python -m pytest plugins/toolkit/hooks/tests/test_herdr_env_context.py -v`、`python3 …/test_mux.py`
- [ ] **Step 3：實作**：hook 讀 stdin JSON（讀不到就略過記錄，不影響原輸出），只在有 `HC_TERMINAL_ID` 時寫檔；`hooks.json` 若此 hook 未接收 stdin 則確認 SessionStart 有傳（Claude Code 會傳 `session_id`）。
- [ ] **Step 4：跑測試確認通過**
- [ ] **Step 5：Commit**：`feat(toolkit): hc 下記錄 session id 供 mux.py session 取用`

---

### Task 3: hc 版面（worker 切在主 session 旁）

**Files:**
- Create: `plugins/toolkit/skills/agent-dispatch/scripts/app_layout.py`
- Modify: `mux.py`（hc `spawn` 視窗開著時呼叫 `app_layout.py`）
- Test: `plugins/toolkit/skills/agent-dispatch/tests/app_layout.sh`（比照 `tests/herdr_layout.sh` 的 stub 手法，stub `herdr-app`）、`test_mux.py`

**Interfaces:**
- Consumes：Task 0 第 6、7、9 項結論；`herdr_layout.py` 的 `PLANS` 與 `MAX_WORKERS = 6`（import 或複製常數，擇一並在檔頭註明）。
- Produces：`app_layout.py place --main <主 pane> --terminal <hc 位址>` → `{"pane":str,"visible":true}`；`app_layout.py relayout --main <主 pane>`；第 7 個起 `tab.new --name <worker>`。

- [ ] **Step 1：寫失敗測試**
  - `1 個 worker`：stub log 顯示 worker 放在主 pane 右側，主 pane 未被 close／move 到別 tab
  - `6 個 worker`：主 pane 面積 ≥ 任一 worker（以 stub 回的 rect 計算）
  - `7 個 worker`：改呼叫 `tab.new`，未重排
  - `test_spawn_without_window_stays_hidden`（test_mux.py）：stub `herdr-app status` exit 1 → `spawn` 回 `visible:false`、exit 0、未呼叫 `app_layout.py`
- [ ] **Step 2：跑測試確認失敗**：`sh plugins/toolkit/skills/agent-dispatch/tests/app_layout.sh`
- [ ] **Step 3：實作**：依 Task 0 選定的指令組合；比例做不到時以「主 pane 最大」為底線。
- [ ] **Step 4：跑測試確認通過**
- [ ] **Step 5：Commit**：`feat(toolkit): Herdr.app 下 worker 切在主 session 旁`

---

### Task 4: self-rotate.sh 改用 mux.py

**Files:**
- Modify: `plugins/toolkit/skills/handoff/scripts/self-rotate.sh`、`plugins/workspace/skills/unattended/scripts/self-rotate.sh`（位元組相同）
- Create: `plugins/workspace/skills/unattended/scripts/mux.py`（Task 1–2 正本的複本）
- Modify: `scripts/ci/shared-copies.json`（新增 mux.py 群組：toolkit 正本＋workspace 複本，Task 6 再加其他 plugin）
- Test: 兩份 `tests/self-rotate.sh`

**Interfaces:**
- Consumes：`mux.py env|wait|send|session|read`。self-rotate 以 `MUX="$(dirname "$0")/mux.py"` 呼叫同目錄複本。

- [ ] **Step 1：寫失敗測試**：現有 herdr stub 測試保留；新增同一組情境的 hc 版（stub `hc`：`get` 回 `{"address":"t3","status":"idle"}`、`send` 寫畫面檔、`/clear` 後由測試改寫 session 檔模擬 hook、`read` 印畫面檔），以 `HC_TERMINAL_ID=t3 MUX_CORE_SOCKET=<tmp 檔>` 執行；驗證項與 herdr 版相同（完成、被吞的 `/reload-plugins` 重送、接回訊息到達、不在 herdr 內退出、前 10 字比對、3 次失敗收尾），另驗 stub `hc` 收到的環境沒有 `HC_TERMINAL_ID`。
- [ ] **Step 2：跑測試確認失敗**：`sh plugins/toolkit/skills/handoff/tests/self-rotate.sh`
- [ ] **Step 3：實作**：`sid` 改 `mux.py session "$SELF"`；`wait` 改 `mux.py wait "$SELF" --timeout 1800`／`60`；送出改 `mux.py send "$SELF" --text "$1"`；畫面檢查改 `mux.py read "$SELF"`；`SELF` 取自 `mux.py env` 的 `self`，backend 為 none 時以原訊息退出。複製到 workspace、登記 shared-copies。
- [ ] **Step 4：跑兩份測試＋ `python3 scripts/ci/validate.py` 通過**
- [ ] **Step 5：Commit**：toolkit（patch 疊在 Task 1 的 minor 上不另 bump，或同版號內）、workspace（minor：1.18.0）CHANGELOG 與版號；`feat: self-rotate 支援 Herdr.app`

---

### Task 5: 「在不在 herdr 內」的 hook 與 node 判斷

**Files:**
- Modify: `plugins/toolkit/hooks/herdr-env-context.py`、`plugins/toolkit/hooks/compact-context.py`、`plugins/toolkit/hooks/notification.sh`、`plugins/toolkit/skills/agent-dispatch/scripts/bg.mjs`（`detectEnv`）、`plugins/toolkit/skills/agent-mesh-check/scripts/clis.mjs`（`scrubEnv`）
- Test: `test_herdr_env_context.py`、`test_compact_context.py`、`dispatch.test.mjs`、`agent-mesh.test.mjs`；新增 `plugins/toolkit/hooks/tests/test_mux_parity.py`

**Interfaces:**
- 判斷式（各檔內嵌，不呼叫 mux.py）：`HC_TERMINAL_ID` 非空，或 `HERDR_ENV == "1"` 且 `HERDR_PANE_ID` 非空 → 在 herdr 內。

- [ ] **Step 1：寫失敗測試**
  - env-context：只有 `HC_TERMINAL_ID` → 注入；注入文字不含 `HERDR_ENV=1` 字樣，且長度 ≤ 改前文字長度
  - compact-context：只有 `HC_TERMINAL_ID` → 指向 handoff skill
  - `dispatch.test.mjs`：`detectEnv({HC_TERMINAL_ID:'t1'}, {ghostty:true})` → `'herdr'`
  - `agent-mesh.test.mjs`：`scrubEnv` 移除 `HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`HC_SCOPE`
  - `test_mux_parity.py`：對同一組環境樣本（只 hc、只 herdr、兩者、皆無、`HERDR_ENV=1` 無 pane id），hook 判斷與 `mux.detect_backend(...) != "none"` 結果一致；`POLLUTED_VARS` ⊇ `scrubEnv` 清單中的 `HERDR_*`／`HC_*` 項（以 regex 讀 clis.mjs 原始碼比對）
  - notification.sh：shell 測試，`HC_TERMINAL_ID=t1` 時 exit 0 且不呼叫通知指令（stub `osascript`／`terminal-notifier`）
- [ ] **Step 2：跑測試確認失敗**：`python -m pytest plugins/toolkit/hooks/tests -v`、`node --test plugins/toolkit/skills/agent-dispatch/dispatch.test.mjs plugins/toolkit/skills/agent-mesh-check/agent-mesh.test.mjs`
- [ ] **Step 3：實作**
- [ ] **Step 4：跑測試確認通過**
- [ ] **Step 5：Commit**：`feat(toolkit): hook 認得 Herdr.app 終端`

---

### Task 6: 補狀態回報（缺 OSC 7501 的 CLI）

**範圍依 Task 0 第 2 項結果**；claude 若已有狀態則不做。每個缺狀態的 CLI 一個子項，同一個任務內完成。

**Files（每個缺的 CLI）：**
- Create: `setup/herdr-core/<cli>/…`（整合檔，形式依該 CLI 擴充點：Claude Code hook 腳本、pi extension `.ts`、codex `notify` 腳本、agy 對應機制）
- Modify: `setup/install.sh`、`setup/uninstall.sh`（偵測到 `hc` 與該 CLI 才安裝；uninstall 移除）
- Test: `setup/tests/herdr-core-status.sh`

**Interfaces:**
- Consumes：Task 0 第 3 項 OSC 7501 格式。
- Produces：該 CLI 在 hc 終端內輪次開始送 `working`、結束送 `idle`（或 `done`）、等人送 `blocked`；不在 hc 終端（無 `HC_TERMINAL_ID`）時不輸出任何序列。

- [ ] **Step 1：寫失敗測試**：每個整合腳本以假事件呼叫，驗 stdout（或寫往 `/dev/tty` 的替代檔，由環境變數指定）是 Task 0 記錄的確切位元組；無 `HC_TERMINAL_ID` 時輸出為空；install 在暫存 HOME 下安裝後檔案存在、uninstall 後不存在。
- [ ] **Step 2：跑測試確認失敗**：`sh setup/tests/herdr-core-status.sh`
- [ ] **Step 3：實作**
- [ ] **Step 4：跑測試確認通過**
- [ ] **Step 5：某 CLI 沒有可用擴充點**：`mux.py spawn` 對該 kind 在 hc 後端回 `{"error":"no_status","hint":"改派 claude/codex/pi"}` exit 1（補 test_mux 測試），並停下回報主控轉告使用者。
- [ ] **Step 6：Commit**：`feat(setup): 替 <cli> 補 herdr-core 狀態回報`

---

### Task 7: 文件改用 mux.py

**Files:**
- Modify: `plugins/toolkit/skills/agent-dispatch/SKILL.md`（第 5、6 節，及 :71 的判斷）、`references/herdr-long-task.md`、`references/background-worker.md`（提及處）
- Modify: `plugins/toolkit/skills/handoff/SKILL.md`、`plugins/workspace/skills/unattended/SKILL.md`、`references/autopilot.md`、`plugins/workspace/skills/agent-orchestration/SKILL.md`
- Modify: 四份 `references/advisor-discussion.md`、`consultant-desk.md`、`shared-preludes.md`（lifecycle、tickets、discovery、delivery；discovery 等只差 alias，照 shared-copies 規則）
- Create: `plugins/{lifecycle,tickets,discovery,delivery}/scripts/mux.py` 複本；更新 `scripts/ci/shared-copies.json` mux 群組
- Modify: 四份 `scripts/advisor_last_reply.py` docstring（指令名改 mux.py 動作）
- Modify: `plugins/toolkit/guards/herdr-pane-run-agent.md`：說明文字改指 `mux.py spawn`；若 Task 1 後 `spawn` 是唯一入口，新增 `plugins/toolkit/guards/hc-run-agent.md` 擋 `hc run … (claude|codex|agy|pi)`（deny），並於 `test_guard.py` 加參數化案例（`hc run --bg claude` → deny；`hc run 'npm test'`、`grep 'hc run claude'` → None）
- Modify: `plugins/toolkit/README.md`、`plugins/lifecycle/README.md`

**Interfaces:**
- Consumes：Task 1 的 CLI 介面（文件只能引用這組動作與欄位）。

- [ ] **Step 1：改寫**：所有 `herdr pane/agent/tab` 指令換成 `mux.py` 動作；「在 herdr 內」改成「`mux.py env` 的 backend 不是 none」；回傳欄位改 `id`／`status`；`herdr-long-task.md` 的安裝、升級、`protocol_mismatch`、`server stop` 保留為「TUI 專屬」小節，另加 hc 小節（`hc update`；core 重啟只能請使用者做，禁止自行 stop/restart；core 沒跑請使用者從 Dock 開 app）。
- [ ] **Step 2：機械檢查**：`grep -rnE 'herdr (pane|agent|tab) ' plugins --include=*.md | grep -v CHANGELOG` 只剩 TUI 專屬小節與 guard 檔；`wc -l` 各 SKILL.md ≤ 300；各 SKILL.md frontmatter description 與改前位元組相同（`git diff` 檢視）。
- [ ] **Step 3：`python3 scripts/ci/validate.py` exit 0、`python -m pytest plugins/toolkit/hooks/tests -v` 通過**
- [ ] **Step 4：Commit**：各 plugin CHANGELOG（起因寫 spec 的起因句）與版號（toolkit 若已 minor 則同版內；workspace 同 Task 4 版；lifecycle 4.2.0、tickets 1.2.0、discovery 1.1.0、delivery 1.2.0 — minor，新增 mux.py 腳本）；`docs: 派工文件改用 mux.py`

---

### Task 8: setup 與 user 層規則

**Files:**
- Modify: setup 的 home 目錄 `rules/dispatch.md`、`setup/adapters/runtime.md`
- Modify: `setup/install.sh`（`herdr integration install claude` 維持只在有 `herdr` 時執行；確認現況）
- Test: `setup/tests/*.sh` 既有測試

- [ ] **Step 1：改寫**：「herdr pane worker」「不在 herdr 內」改成涵蓋 Herdr.app 的說法，判斷依據指向 `mux.py env`（在 user 層規則中以白話寫「herdr（TUI 或 Herdr.app）」即可，不寫路徑）；字元數 ≤ 原檔（`wc -m` 前後比對）。
- [ ] **Step 2：驗證**：`for t in setup/tests/*.sh; do sh "$t" || echo FAIL $t; done` 無 FAIL；`wc -m` 不增加；`validate.py` exit 0。
- [ ] **Step 3：Commit**：`docs(setup): 派工規則涵蓋 Herdr.app`

---

### Task 9: 收尾與全套驗證

**Files:**
- Modify: `docs/feature.md`（新增一行 `[x]` 或 `[ ] 🚧`，含使用者 2026-11-17 裁決摘要）
- Modify: `docs/superpowers/specs/2026-11-17-herdr-core-mux-design.md`（若 spike／實作有偏離，補「實作差異」小節）

- [ ] **Step 1：全套本機驗證**（各自記 exit code）：`python3 scripts/ci/validate.py`、`python3 scripts/ci/test_validate.py`、`for t in $(git ls-files 'plugins/**/test_*.py' ':!:plugins/toolkit/hooks/tests/*' ':!:plugins/toolkit/skills/transcribe/tests/*'); do python3 "$t" || echo FAIL $t; done`、`node --test $(git ls-files 'plugins/**/*.test.mjs') 'setup/adapters/tests/*.test.mjs'`、`python -m pytest plugins/toolkit/hooks/tests -v`、`for t in $(git ls-files 'plugins/**/tests/*.sh' ':!:**/tests/lib/*'); do sh "$t" || echo FAIL $t; done`、`for t in $(git ls-files 'setup/tests/*.sh' ':!:setup/tests/lib/*'); do sh "$t" || echo FAIL $t; done`
- [ ] **Step 2：Commit**：`docs: 更新功能清單（Herdr.app 派工）`

---

### Task 10: 實機驗收（使用者在場）

不寫程式；結果記在 spike 筆記末尾「實機驗收」小節。每項分開記通過／失敗／未驗證。

- [ ] app 內（用 `claude --plugin-dir` 載入本 worktree 的 plugin）：claude、codex、agy、pi 各派一個長任務 worker，確認出現在主 session 旁、`status` 會變、結果檔回來、收工後格子關掉
- [ ] app 內跑一次雙顧問（lifecycle advisor-discussion）
- [ ] app 內觸發一次 self-rotate（handoff）
- [ ] app 視窗關著時派一個 worker：`visible:false`、照常完成
- [ ] TUI 內回歸：長任務 worker、雙顧問、self-rotate 各一次
- [ ] Commit 驗收紀錄；push 與開 PR 另問使用者
