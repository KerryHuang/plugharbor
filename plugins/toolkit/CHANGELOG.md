# Changelog

格式：每次改動 `hooks/`、`guards/`、`skills/`、`agents/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。


## [0.9.0] - 2026-11-04

- feat: agent-dispatch 派工可指定模型與思考等級（`clis.mjs` 的 `buildArgs` 加 `model`／`effort`，四個 CLI 各用自己的參數），並能從錯誤訊息辨認額度用盡與重置時間（`quotaInfo`，抓不到時間就預設封鎖 1 小時）。
- feat: 派工路由（`agent-dispatch/references/routing.json`＋`scripts/route.mjs`）：任務類型 × 難度（top／standard／cheap）查表得出有序候選（CLI＋模型＋思考等級），濾掉 agent-mesh-check 最近一次沒通過的 CLI 與額度封鎖中的 CLI；改動碰到安全、資料、DB 結構、公開介面或超過 300 行時要跨家族審查，挑不同家族的審查者，湊不到才退回同家。`node route.mjs block <cli> <到期時間>` 手動標記某家先省著用。
- feat: `ask.mjs` 接上路由：`--type`／`--tier` 查表挑對象（`--to` 仍可直接指定），`--model`／`--effort` 可覆寫；額度用盡自動封鎖該家並改派下一個候選，全部不能用時 exit 75 並印最早解封時間；第一行固定印「交給誰、用哪級、理由」；輸出超過 16000 字元時全文寫進結果檔（預設 `<prompt 檔>.out.md`），只印前 4000 字元摘要。
- feat: 沒有 herdr 時的長任務（`agent-dispatch/scripts/bg.mjs`）。
  - **Ghostty 分割**：macOS 用 Ghostty 1.4 的 AppleScript 開看得見的分割，可帶工作目錄與環境變數，收工時用 id 關掉。spike 結論見 `skills/agent-dispatch/references/background-worker.md`。
  - **背景 worker**：每個 worker 開獨立 git worktree（分支 `dispatch/<名>`），由 detached 監督程序執行，結束後依結果檔寫入 `done`／`failed`／`quota` 狀態並發 macOS 通知。並行上限 4，遇到額度或逾時就降。Windows 尚未實機驗證。
- feat: 新增 Stop hook `dispatch-stop-guard.py`：被派出的 worker（環境變數 `AGENT_DISPATCH_RESULT` 有設）沒寫結果檔就想結束時擋下一次，要它先寫結果；一般 session 不受影響，壞輸入與 `stop_hook_active` 一律放行。

## [0.8.0] - 2026-11-03

- feat: `transcribe record start --source system|both`：錄線上會議時，連同系統播放的對方聲音一起錄。Mac 用 catap（Core Audio process tap，不必裝虛擬音訊驅動）擷取系統輸出，由 detach 的 Python worker 寫進 ffmpeg stdin，沿用 segment 分段；`both` 以 `amix=duration=first` 混入麥克風。Windows 的 WASAPI loopback 程式碼已寫，但尚未驗證，`doctor` 與 `start` 一律拒絕。
- feat: 沒有聲音時（WASAPI 不送資料）依牆鐘補零，時間軸不縮短。`record status` 顯示「對方聲音：尚未收到／最近一次時間」；沒有系統錄音授權時只會收到全零音訊，不會報錯，所以開錄時不對系統軌做靜音警告。
- feat: `transcribe live start`：背景逐段轉錄，模型只載入一次，等 `seg-(N+1)` 出現或錄音停止才轉 `seg-N`，以各段實際長度累加時間戳，追加到 `transcript.md`，每段寫 `<!-- seg-NNN done -->` 標記、全部完成寫 `<!-- live finished -->`；被殺重啟時以標記為準，不重複追加。`record status` 顯示逐字稿進度與落後提示。
- feat: `doctor --record --source system` 檢查 macOS 14.2+、Python 3.11+、catap，並印出系統錄音授權步驟。
- fix（最終審閱）：`live start` 確認程序真的起來（寫出 live.json），一啟動就死時 exit 3 並印 log 尾段；`record status` 在 live 程序已不在時顯示「已中止」；單段轉錄失敗寫 `<!-- seg-NNN failed -->` 後繼續下一段；`--source system|both` 開錄最多等 8 秒第一段（第一次跑要 import catap、建 tap）。
- 實測（Mac）：system 81.08 秒／牆鐘 1:21、7 句全轉出；`both` 33.23 秒／牆鐘 32.92；`live` 在下一段開始後 20 秒內轉好前一段，停止後約 4 秒收尾。測試 80 條。

## [0.7.0] - 2026-11-03

- feat: `transcribe` 新增 `record devices|start|status|stop`：用 ffmpeg 背景錄麥克風（Mac avfoundation 預設 `:default`，不用編號 0；Windows dshow 需指定裝置），每 N 秒（預設 300）寫一個 16 kHz 單聲道 wav 分段。狀態檔 `record.json` 在啟動後立刻寫入；錄音以 detach 方式與 session 脫鉤，任一 session 都能 `stop`。`stop` 會先 SIGINT（Windows 用 taskkill）再以 concat 合併成 `recording.wav`，程序已不在也照樣合併。開錄 3 秒後 max_volume 低於 -70 dB 就警告。
- fix: 實測 Mac 不加大輸入佇列時每 30 秒掉約 3.5 秒音訊，擷取改帶 `-thread_queue_size 4096` 與 `aresample=async=1000`。
- fix: Windows 實測，SSH 連線（及部分終端機）結束時會連同 job 內的子程序一起砍掉；啟動改帶 `CREATE_BREAKAWAY_FROM_JOB`，job 不允許時退回原旗標。
- fix: 硬殺 ffmpeg（Windows 一律 `taskkill /F`、Mac 的 SIGKILL 後備）會丟最後約 8 秒，因為 segment 內層 muxer 每 256 KiB 才寫盤，改帶 `-segment_format_options flush_packets=1`；合併清單每段加 `option ignore_length 1`（硬殺的 wav 檔頭長度沒收尾），並改用絕對路徑（相對 `--out` 會被解析成 `dir/dir/seg`）。
- fix: 目錄已有 `seg-*.wav` 或 `recording.wav` 時 `start` 拒絕（exit 2），避免 segment muxer 從 seg-000 覆蓋前一段錄音；沒裝 ffmpeg 時 `start` 回 exit 3，不再噴 traceback。
- fix: 程序存活判斷改成確認 PID 仍是 ffmpeg（Mac `ps -o comm=`、Windows `tasklist /FO CSV`），當機後 PID 被重用時不會誤殺別的程序；Windows `taskkill` 拿掉 `/T`；啟動檢查先 reap 已結束的子程序（zombie 仍查得到 PID）；`_kill` 遇程序中途自己結束不再丟例外。
- feat: `doctor --record` 一併檢查錄音需要的 ffmpeg（Windows 轉錄本身不需要）。測試 47 條。

## [0.6.2] - 2026-11-03

- fix: `transcribe` mlx 路徑遇靜音會幻覺出「訂閱、點贊」等文字並以 exit 0 結束：改開 `word_timestamps`＋`hallucination_silence_threshold=2.0`，並以 ffmpeg `silencedetect`（-45dB、1 秒）丟掉八成以上落在無聲區段的段落。實測 60 秒純靜音改回 exit 4，長靜音＋語音只留真正的話。
- fix: 術語提示超過約 200 字時印警告（Whisper 上限約 223 tokens，超過會截掉開頭）。
- fix: stderr 不是 TTY（背景執行）時不印逐段進度，免得輸出變成一條數十 KB 的長行。測試 21 條。

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
