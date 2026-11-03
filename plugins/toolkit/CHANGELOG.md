# Changelog

格式：每次改動 `hooks/`、`guards/`、`skills/`、`agents/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。


## [0.6.1] - 2026-11-03

- fix: `transcribe` Windows 實測修正。faster-whisper 以 PyAV 自帶解碼，ffmpeg 只在 mlx-whisper（Mac）路徑檢查與列入 `doctor`；faster-whisper 1.2.x 遇 PyAV 17+ 會因 `metadata_errors` 參數失敗，`doctor` 改為檢查 `av<17` 並給安裝指令。測試 16 條。

## [0.6.0] - 2026-11-03

- feat: 新增 skill `transcribe`：本機把錄音檔轉成帶時間戳的逐字稿 Markdown。Mac Apple Silicon 用 mlx-whisper（預設 `mlx-community/whisper-large-v3-turbo`），其他平台用 faster-whisper（CPU int8、有 CUDA 用 float16），輸出經 OpenCC `s2twp` 並把「臺」統一為「台」；可帶 `--prompt-file` 術語提示。`doctor` 子命令檢查 ffmpeg／轉錄套件／OpenCC 並印安裝指令，不自動裝。靜音音檔 exit 4 不產檔、輸出已存在不覆寫（`--force`）、缺 OpenCC 或 ffmpeg 在轉錄前就停。
- test: 新增 `plugins/toolkit/skills/transcribe/tests/test_transcribe.py`（13 條，假 backend，不需模型）；CI 的 pytest 步驟加跑並安裝 opencc。

## [0.5.0] - 2026-11-03

- feat: 新增 hook `plugins/toolkit/hooks/loop-guard.py`（失敗迴圈提醒）：同一輪內同一失敗指紋出現 3 次，注入「停下重估、換方向前落檔、必要時 friction」提示進 context，之後同指紋再犯只給使用者 systemMessage；不中止、不寫 friction 佇列。指紋＝工具名＋錯誤第一個有意義的行（跳過 `Exit code N`），去數字／十六進位位址／路徑（借自 microsoft/TokenEconomizer loopguard）。主 session 與 subagent 依 `agent_id` 各自計數。Claude Code 註冊 PostToolUseFailure 與 UserPromptSubmit（重置主 session）；狀態在 `~/.claude/loop-guard/`，7 天前的 session 狀態自動清掉。
- feat: 同一支腳本也吃 Codex 的 PostToolUse payload：Codex 沒有失敗事件，成敗查 `transcript_path` 同 `tool_use_id` 的 `item_completed`；輪界用 `turn_id`；狀態在 `~/.codex/loop-guard/`。adapter 新增 `setup/adapters/loop-guard.mjs`（stdin 轉給 repo 內的 `loop-guard.py`）並註冊進 `~/.codex/hooks.json` 的 PostToolUse，安裝後需在 Codex `/hooks` 信任。
- test: 新增 `plugins/toolkit/hooks/tests/test_loop_guard.py`（21 條）；`setup/adapters/tests/sync-user.test.mjs` 新增 wrapper 解析與轉送測試；`test_agent_model_guard.py` 的 python hook 數改為 10。
- docs: `docs/agent-parity.md`、toolkit README 補 loop-guard。

## [0.4.1] - 2026-11-03

- docs: `plugins/toolkit/skills/agent-dispatch/SKILL.md` 長任務模式拿掉「開 pane 前已有 3 個活著的 worker 先問使用者」的前置步驟；派工數量不再設門檻。

## [0.4.0] - 2026-11-02

- feat: 新增 SessionStart hook `plugins/toolkit/hooks/retro-due-reminder.py`：讀 `.plugharbor/toolkit.yml` 的 `retrospective.path`，帳本 `metrics.yml` 有 `status: open` 的指標到期（`date` 已到；`new_chains` 依 `units_glob` 以 git 首次 commit 日期計數達標）就提議跑 `toolkit:retrospective`；`checks` 最後一筆不早於最新證據時視為已驗、不再提醒。regex 解析不依賴 PyYAML；沒設定、沒帳本、不是 git repo、解析失敗一律靜默放行。對應 sdlc 2.94.0／2.94.1。
- feat: `plugins/toolkit/skills/retrospective/SKILL.md` Step 3 改為「判歸屬，再分類」：被檢討的 plugin 照五類處理；專案層／使用者層根因以 `feedback_queue.py friction` 轉交 feedback-review 佇列；記憶類列報告。Step 1 收 feedback-review 轉入的糾正群；`--apply` 只改 plugin 歸屬項；收尾條件加「非 plugin 根因都有去向」。對應 sdlc 2.95.0。
- feat: `plugins/toolkit/skills/retrospective/references/report-template.md` 新增「轉交」段；`plugins/toolkit/skills/retrospective/references/metrics-ledger.md` 註明提醒以 checks 最後一筆為準。
- test: 新增 `plugins/toolkit/hooks/tests/test_retro_due_reminder.py`（15 條）；`plugins/toolkit/hooks/tests/test_agent_model_guard.py` 的 python hook 數改為 8。

## [0.3.3] - 2026-11-02

- test: `plugins/toolkit/skills/agent-dispatch/tests/herdr_layout.sh` 的非 UTF-8 案例改為把未指定 encoding 的 `subprocess.run` 換成 ascii 解碼來模擬，不再靠 `LC_ALL=C`（Linux C locale 下參數「★」本身就編碼不了，CI 誤判失敗）。

## [0.3.2] - 2026-11-02

- fix: `plugins/toolkit/skills/agent-dispatch/scripts/herdr_layout.py` 讀 herdr 輸出時指定 `encoding="utf-8"`；Windows 預設 cp950，pane 標題含中文或 emoji 時解碼失敗、重排崩潰（對應 sdlc 2.95.1）。
- test: `plugins/toolkit/skills/agent-dispatch/tests/herdr_layout.sh` 新增非 UTF-8 locale 下 herdr 輸出含中文／emoji 的案例。

## [0.3.1] - 2026-11-02

- fix: `plugins/toolkit/hooks/hooks.json` 七條 python hook 在 `exec` 前先檢查腳本存在（`[ -f "$S" ] || exit 0`），缺檔時 fail-open；先前缺 `guard.py` 會 exit 2，擋掉全部 Bash、Write、Edit。
- fix: `plugins/toolkit/package.json` 移除 `version`（版本只在 `plugins/toolkit/.claude-plugin/plugin.json` 同步，原本 0.1.0 已漂移），補 `private`、`description`、`keywords`。
- test: 新增 `plugins/toolkit/hooks/tests/test_agent_model_guard.py`（agent-model-guard 行為與 hooks.json 缺檔 fail-open）與 `plugins/toolkit/hooks/tests/test_manifest.py`（package.json 不得有 version）。
- fix: `plugins/toolkit/skills/retrospective/` 的 `plugins/toolkit/skills/retrospective/references/metrics-ledger.md` 範例與 `plugins/toolkit/skills/retrospective/SKILL.md` Step 0 改為依指標記的 `units_glob` 計數，避免口徑漂移；`plugins/toolkit/skills/retrospective/scripts/chain_cost.py` docstring 說明單位目錄只認其內的路徑、樣式尾端 `/` 會自動去掉。
- fix: `plugins/toolkit/skills/agent-dispatch/SKILL.md` 把「濾掉 `HERDR_*` 環境變數」從收工步驟移到步驟 0 前置。

## [0.3.0] - 2026-11-02

- feat: 新增 `retrospective` skill——檢討 agent 工作流程與 plugin 本身（含評估流程改版、回測某個方向）。Step 0 先讀指標帳本 `metrics.yml`（`due` 為 `new_chains` 或 `date`，未到期記 `not-due`），Step 5 追加新指標；帳本與報告放專案設定的版控目錄（`.plugharbor/toolkit.yml` 的 `retrospective.path`）。取自 sdlc 2.93.1，「規格鏈」泛化為「工作單位」，移除 lite／standard 分流。
- feat: `retrospective/scripts/chain_cost.py` 與 `test_chain_cost.py`——統計工作單位的 session、輪數、token；新增 `--units-glob`（預設 `docs/*/*`）與 `--projects-dir`；只支援 Claude Code。
- refactor: 新增共用 reference `plugins/toolkit/references/improvement-loop.md`（先驗上一輪、人審、記帳），`feedback-review` 的 SKILL.md 與 `principles.md` 改為引用，刪除重複段落。

## [0.2.0] - 2026-11-02

- feat: `agent-dispatch` 長任務模式併入 `dispatch-worker` 的做法——預設在同一個 tab `pane split`，再跑 `skills/agent-dispatch/scripts/herdr_layout.py` 重排（主 session 最大並掛「★」標籤，同 tab 最多 6 個 worker，第 7 個起開新 tab）；收工後同樣重排。
- feat: 新增 `--agent <plugin>:<agent>` 指定 agent 定義；兩個 Claude 專屬坑（不要在 Claude Code 內啟 herdr server、`claude -p` 啟動前濾掉 `HERDR_*`）；reference 新增 herdr 安裝與升級（`protocol_mismatch`）一節。
- refactor: 刪除「專案有 dispatch-worker 就讓位」條款與「未實測」引言。
- test: `skills/agent-dispatch/tests/herdr_layout.sh`（stub herdr，驗 1／6／7 個 worker 的版型與 ★ 標籤）。

## [0.1.0] - 2026-10-30

- feat: 初版 hooks——`guard.py`（PreToolUse，分層 guard）、`agent-model-guard.py`、`ask-question-guard.py`、`auto-session-title.py`、`feedback-capture.py`、`feedback-reminder.py`、`context-size-reminder.py`、`notification.sh`（macOS 播系統 Glass 音，不附音效檔）。
- feat: 分層 guard——讀取順序 `plugin/guards` → `~/.claude/guards` → `<專案>/.claude/guards`，同名檔由後讀的覆寫；規則檔 CRLF 也能解析。內建 `git-add-all`、`git-destructive` 兩條。
- feat: `hooks.json` 以 `${CLAUDE_PLUGIN_ROOT}` 註冊，保留「找得到能跑的 python 才執行，否則 exit 0」外殼。
- feat: 7 個 skill——`config-doctor`（設定健檢）、`context-diet`（context 瘦身）、`tidy-memory`（整理 auto-memory）、`feedback-review`（回顧糾正佇列，含 `friction` 子命令說明）、`handoff`（交接）、`agent-dispatch`（派工給其他 agent CLI）、`agent-mesh-check`（驗證 agent CLI 互叫）。
- feat: 5 支 reviewer agent——`claudemd-reviewer`、`hook-reviewer`、`rule-reviewer`、`skill-reviewer`、`subagent-reviewer`（取自 Reflexive-Claude-Code，MIT，見 `agents/NOTICE.txt`）。
- test: `feedback_queue.py` 單元測試（`test_feedback_queue.py`）、`agent-mesh.test.mjs`（node --test）。
- test: `hooks/tests/test_guard.py` 與四支 shell 測試（ask-question-guard、auto-session-title、context-reminder、feedback-hooks）。
