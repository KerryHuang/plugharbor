# Changelog

格式：每次改動 `hooks/`、`guards/`、`skills/`、`agents/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.30.0] - 2026-11-19

起因：Formwright 自動駕駛期間兩筆 skill 摩擦回饋（2026-11-19）。
- feat(tower)：`takeoff --proxy` 代管航班。主控替 Agent tool subagent 登記時，subagent 不送心跳，航班 30 分鐘後被判 lost，與真斷線分不出來；代管航班只在 worktree 不存在時才算 lost，radar 標 `flying*`。SKILL.md 寫明收尾用 `release --id`。測試 `test_proxy_flight_not_lost_by_stale_beat`。
- fix(agent-dispatch)：ask.mjs 對 codex 的最終答案另存 `.answer.md`，stdout 指向它；SKILL.md 寫明 `.out.md` 是整段執行紀錄（可達數百 KB）、重讀結論讀 `.answer.md`。原本只印答案、紀錄存 `.out.md`，但說明只寫「全文在 .out.md」，主控去讀 400KB 的紀錄。
- 刪減候選：兩處皆為增量一行，tower 已知限制與 agent-dispatch 判讀段逐條看過，沒有可合併的重複項。

## [0.29.1] - 2026-11-18

起因：無人值守中收到 subagent 交回，`disabled-skills.py` 的 UserPromptSubmit 因內文提到 migration 要求用 AskUserQuestion 問啟用 database:migration，但那不是使用者訊息、使用者已睡（2026-11-18）。
- fix(disabled-skills)：訊息以 `<task-notification` 開頭（subagent／背景工作交回）或 `AGENT_DISPATCH_UNATTENDED=1` 時，改提示「不要問、不要啟用，需要就記進回來報告待決」。
- test：`test_disabled_skills.py` 新增兩個測試；`run_raw` 清掉環境變數 `AGENT_DISPATCH_UNATTENDED`，避免在無人值守 session 跑測試時誤判。

## [0.29.0] - 2026-11-18

起因：user 層規則早寫「需要我決定的事一律用 AskUserQuestion」，跑 brainstorming 時 agent 仍照 skill 用一段文字一題一題問，使用者回「你怎麼沒用 AskUserQuestion 問我」（2026-11-12，feedback-review 回饋佇列）。同義條文已失效，改成機制。
- feat(hooks)：新增 Stop hook `text-question-guard.py`：去掉程式碼與 inline code 後，回覆最後一段（略過「建議 session 標題」行）有一行以「？」或「?」結尾、且這回合沒呼叫 AskUserQuestion，就擋下一次，要求改用 AskUserQuestion 或把結尾改成陳述句。無人值守 worker（`AGENT_DISPATCH_UNATTENDED=1`）不管；`stop_hook_active` 時放行。以近 30 天 1481 個主 session 回合重播，擋下 8 次，抽查全是真的用文字問使用者，未見誤擋。
- test：`hooks/tests/test_text_question_guard.py`（10 個）；`test_agent_model_guard.py` 的 python hook 數量 24 → 25。

## [0.28.2] - 2026-11-18

起因：Windows 桌機的 Herdr.app 終端跑 `mux.py env` 直接丟 `AttributeError: module 'socket' has no attribute 'AF_UNIX'`（`core_running()`，2026-11-18 重現），Windows 上所有經 mux.py 的派工都不能用。另外 `spawn` 用 `env -u …` 當 argv 前綴（Windows 沒有 `env`），`app_layout.py` import `fcntl`（Windows 沒有）。
- fix(mux.py)：Windows 判斷 core 改用 `hc server status --json`（hc 官方：Windows 上不會啟動 core；Unix 照舊 connect socket）；`spawn` 改用 Python 包一層取代 `env -u`（清掉污染變數、設 `--env`、忽略 Ctrl+C、轉傳 exit code；hc 仍認得底下 agent 的狀態）；沒有 `ps` 時祖先不明照預設；core 沒跑的提示在 Windows 改成開始選單。
- fix(app_layout.py)：Windows 沒有 `fcntl`，臨界區改用 `msvcrt.locking`。
- test：`test_mux.py` 新增以 `sys.platform`／假 socket 模擬 Windows 的 8 個測試；Windows 桌機在 Herdr 終端實跑 env／spawn／send／read／alive／session／wait／close 與 `--env` 傳遞全過，Mac 回歸也過。

## [0.28.1] - 2026-11-18

起因：Windows 桌機的 Codex 0.169.1 每次問答都出現 14 個 `Hook failed / hook exited with code 1`（2026-11-18 實測）。Windows 的 Codex 經 PowerShell 跑 hook，PATH 上沒有 `sh`（Git 的 sh.exe 沒加進 PATH）；`bash` 解析成 WSL，讀不到 `C:/` 路徑。另外 Windows clone 預設 `core.autocrlf=true`，`run-py.sh` 變 CRLF 後找不到腳本，就算找到 sh 也會靜默不跑。
- fix(hooks)：`hooks.json` 每條 hook 加 `commandWindows`（PowerShell 5.1 相容）：UTF-8 讀 stdin，依序找 Git for Windows 的 `sh.exe`（`notification.sh` 找 `bash.exe`），找不到一律 exit 0（fail-open，同 `run-py.sh`）。Codex 在 Windows 只跑這個欄位，Claude Code 不受影響。做法照 sdlc plugin 已在 Windows 驗證過的 `codex-hooks.json`。
- fix：repo 根新增 `.gitattributes`（`*.sh text eol=lf`）；`run-py.sh`、`notification.sh` 更新註解，讓既有 Windows clone pull 後以 LF 重新取出。
- test：`hooks/tests/test_hooks_windows.py`：每條 `commandWindows` 都等於樣板、bash 腳本用 Git Bash、`.sh` 無 CR；Windows 上另外實跑（python hook 有輸出、通知 exit 0、找不到 sh 時 fail-open）。
- test：`test_agent_model_guard.py` 的 python hook 數量 23 → 24（0.28.0 新增 `herdr-tab-title.py` 時漏改，HEAD 上就已失敗）。

## [0.28.0] - 2026-11-18

起因：改用 Herdr.app 後，分頁名稱固定是「Claude Code」或編號，不跟 Claude 的 session 標題（內建 ai-title、`auto-session-title` 套用的 /rename）走，看起來像沒在改名；標題其實有寫進 terminal title（`hc get` 查得到），只是 Herdr.app 分頁不顯示。
- feat(hooks)：新增 Stop hook `herdr-tab-title.py`：在 Herdr.app 內（有 `HC_TERMINAL_ID`）每回合結束把 terminal title 用 `herdr-app do tab.rename` 寫成分頁名稱；只改預設名稱（空、編號、「Claude Code」）或上次自己寫的，手動命名不覆寫；分頁有多個 terminal 時只認第一個，worker 不改主分頁。測試 `hooks/tests/herdr-tab-title.sh`。

## [0.27.0] - 2026-11-18

起因：用短問答（唯讀）派 codex 審查（medium、總時限 1500 秒），codex 說明計畫、讀了 3 個檔後 24 分鐘沒有任何輸出，直到總時限才被中斷、沒交出結論；同一天類似情況 3 次，主控只能等滿總時限才知道卡住。
- feat(agent-dispatch)：`ask.mjs` 新增 `--idle-timeout <秒>`（預設 480，0 關閉）：子程序連續這麼久沒有輸出就中斷、exit 124，訊息「連續 N 秒無輸出，判定卡住」，已收到的輸出照逾時路徑寫入 `.out.md`；卡住不觸發額度改派。`clis.mjs` 的 `run()` 加 `idleMs`／回傳 `idle`。SKILL.md 補說明；總時限 `--timeout` 不變。

## [0.26.3] - 2026-11-18

起因：用短問答（唯讀）派 codex 審查，範本要求「輸出寫到結果檔」，唯讀沙箱寫不了，每次都回報「唯讀與寫入衝突」；範本又沒有範圍與時限，codex 以 high 大範圍讀檔（輸出 8–13 萬字元），三次都逾時沒交出結論；改窄範圍＋限時＋medium 後一次就交付。
- review-prompt 範本：短問答改「結果在回覆中交付」，長任務才寫結果檔；加「範圍」欄與限時。
- SKILL.md 審查：要給範圍與時限，逾時先縮範圍或降 effort，仍逾時退回同家審查。
- ask.mjs：唯讀指示補「結果在回覆中交付」；逾時時一律把已收到的輸出寫入 `.out.md`。

## [0.26.2] - 2026-11-17

起因：自動駕駛一段約 2200 行後端工作花約 5 小時（設計已很細仍另寫計畫再審、每個子單元走全套審查與 CI）；跨家族審查指出 1.19.0 的免計畫與續派原實作者規則沒有接通其他流程。

- docs(agent-dispatch)：`skills/agent-dispatch/SKILL.md` 第 6 節收工步驟加例外：無人值守或自動駕駛的實作者要等審查與修正（續派原實作者），保留到該段修正完成才關，並在帳本記 worker id／session；與 `workspace` 1.19.1 的資源規則同步。frontmatter description 不變。

## [0.26.1] - 2026-11-17

- fix(tower)：`--paths` 改為 `action="extend"`，takeoff 與 amend 重複給旗標時合併（amend 仍是整份取代）；`match()` 對不含 `*` 的路徑視為目錄前綴（`a/b`、`a/b/` 涵蓋其下全部），`_in_scope`、重疊判斷與共用跑道比對一併生效。SKILL.md 補一句用法。測試 `test_tower.py` 新增 3 項。
- 起因：自動駕駛起飛時下 `--paths backend/src --paths backend/tests`，航班只留下後者；落地 land-check 回 10，把兩個目錄下所有檔都判成超出範圍，只好 override。

## [0.26.0] - 2026-11-17

- feat(hooks)：新增 PostToolUse hook `send-retry-hint.py`（matcher `SendMessage`，測試 `hooks/tests/test_send_retry_hint.py`）：回報「No agent named …」時注入提示，要發送方用 ListAgents 找同一個 ref 的目前名稱重送一次，仍失敗才照原指示寫 undelivered。送不到時觸發的是 PostToolUse（`tool_response.success=false`），不是 PostToolUseFailure（`claude -p` 實測）。`agent-dispatch` SKILL 步驟 1「送不到…不重試」改寫成同義的重送一次。
- 起因：送達比對的是名稱；收件方派工後改名就送不到。11-01～11-17 共 5 起（含 2026-11-17 self-rotate 接手回報失敗），10-21 派工批次 61 次；SKILL 既有的「先用 ListAgents 取位址」擋不住（`docs/retrospective/20261117-reply-address/`）。

## [0.25.0] - 2026-11-17

- feat(agent-dispatch)：新增 `skills/agent-dispatch/scripts/mux.py`（與 `test_mux.py`），把派工需要的動作（env、spawn、send、wait、read、alive、session、close、attach-hint）收斂成一支轉接腳本，後端為 Herdr.app（`hc`）或 herdr TUI；狀態統一映射成 `done|idle|working|blocked|error|timeout|gone`。核心行為：兩組環境變數同時存在時看誰的終端是最近祖先；core 沒跑（直接連 socket 判斷，不經 hc）時回 `core_not_running` 且不呼叫任何 hc；`hc send` 前移除 `HC_TERMINAL_ID` 以免訊息被包成 `<hc from>`；`hc run` 的 CLI 先解成絕對路徑（core 的 PATH 不同）、加 `--no-notify`、以 `env -u …` 前綴清掉繼承的污染變數；`done` 與 `idle` 都視為輪次結束。本版只含腳本與測試，skill 文件、hook、self-rotate 尚未改用它。
- feat(agent-dispatch)：新增 `skills/agent-dispatch/scripts/app_layout.py`（`place`，測試 `tests/app_layout.sh`），`mux.py spawn` 在 Herdr.app 視窗開著時把 hc worker 放進主 session 所在 tab：第 1 個從主 pane 往右切，之後只切最新的 worker pane（輪流 down／right），主 pane 不再被切、始終不小於任一格；第 7 個起 `terminal.keep --terminal <t>` 不帶 place（開新 tab，tab 內只有 worker），不重排；`place` 以 flock（`${XDG_STATE_HOME:-~/.local/state}/plugharbor/app-layout.lock`）序列化 ls→focus→keep→還原 focus，避免並行派工時 focus 互相覆蓋。app 沒有指定比例的指令，只能對半切，所以版型與 TUI 的 `PLANS` 不同。放完把 focus 還給主 pane。視窗沒開或主 pane 不在視窗內，worker 照跑、回 `visible:false`。`window` 判斷改為只有 `herdr-app status` exit 2 且訊息含 `no Herdr window` 才算沒開，其他失敗回 `{"error":"window_error"}`（`env` 與 `spawn` 皆然，`spawn` 在 `hc run` 之前判斷）。
- 起因：使用者 2026-11-17 轉用 Herdr.app，派工流程在 app 內無法開 worker。本分支的後續改動（文件、hook、self-rotate）併在同一版。
- feat(hooks)：`herdr-env-context.py` 在 `HC_TERMINAL_ID` 存在時，把 SessionStart 輸入的 `session_id` 寫到 `${XDG_STATE_HOME:-~/.local/state}/plugharbor/hc-sessions/<HC_TERMINAL_ID>`（`/clear` 會覆寫）；讀不到 stdin 或 JSON 壞掉時略過記錄，原輸出與 exit 0 不變。`mux.py session` 的 hc 分支改為 `hc get` 取 address 再讀此檔，沒有檔回 `null`。
- feat(hooks)：「在不在 herdr 內」改為 `HC_TERMINAL_ID` 非空，或 `HERDR_ENV=1` 且 `HERDR_PANE_ID` 非空（與 `mux.py detect_backend` 一致，`tests/test_mux_parity.py` 對照）：`herdr-env-context.py`（注入文字改為不綁變數名、長度不增）、`compact-context.py`（handoff 提示）、`notification.sh`（Herdr.app 內不發桌面通知，`tests/notification-herdr.sh`）、`bg.mjs detectEnv`。`clis.mjs scrubEnv` 另濾掉 `HC_TERMINAL_*`、`HC_SCOPE`、`HERDR_SOCKET_PATH`、`HERDR_TAB_ID`、`HERDR_WORKSPACE_ID`，拋棄式 CLI 不能冒用主 session 身分。
- feat(handoff)：`skills/handoff/scripts/self-rotate.sh` 改經 `mux.py`（找不到同目錄複本時用 `agent-dispatch/scripts/mux.py`），herdr TUI 與 Herdr.app（hc）都能換新；與 workspace unattended 的副本保持一致，`tests/self-rotate.sh` 兩種後端各跑一組情境（hc 版另驗 send 時環境沒有 `HC_TERMINAL_ID`、core 沒跑不呼叫 hc）。
- docs(agent-dispatch)：`SKILL.md` 第 5、6 節、`skills/agent-dispatch/references/herdr-long-task.md`、`skills/agent-dispatch/references/background-worker.md`、`handoff/SKILL.md` 改用 `mux.py` 動作（`env`／`spawn`／`send --file --wait`／`read`／`alive`／`session`／`close`／`attach-hint`）：判斷「在不在 herdr」改成 `mux.py env` 的 `backend` 不是 `none`，開 worker 不再手動切 pane 與跑 `herdr_layout.py`（`spawn` 處理版面），狀態判讀改看 `status`（`done|idle|working|blocked|error|timeout|gone`）；`herdr-long-task.md` 的安裝、升級、`protocol_mismatch`、server 重啟、獨立 tab、收工重排收進「TUI 專屬」小節，另加「Herdr.app（hc）」小節（四種 CLI 原生回報狀態、codex 需 `--no-daemon`、`hc update`、core 重啟只能請使用者做、core 沒跑請從 Dock 開 app）。frontmatter description 不變。
- feat(guards)：新增 `hc-run-agent`（deny）擋 `hc run … claude|codex|agy|pi`（`mux.py spawn` 是唯一啟動 agent 的入口，直接 `hc run` 會漏帶 model／effort 並繞過 PATH 解析、環境清理與版面），`tests/test_guard.py` 補正反案例；`herdr-pane-run-agent`、`herdr-tab-create` 的說明文字改指 `mux.py spawn`。`worker_ctx.py` 說明改指 `mux.py session`，README 同步。
- fix(agent-dispatch)（最終審查）：(1) `mux.py session` 在 hc 讀不到 session 檔時回 `{"session":null,"hint":…}`（hc 下需本 plugin 的 SessionStart hook）；(2) hc 的 `send` 在目標 `turn == 0` 時先 `hc wait --json --timeout <min(--timeout, 60)>`（spawn 剛回傳 status 仍是 null，約 1 秒後才 idle）再加 `--if idle`，status 仍不是 idle（多半停在啟動對話框，此時 status 是 null）就不送，回 `{"status":"blocked","hint":…}` 且不重試，SKILL.md 步驟 2 對應改寫；(3) TUI `spawn` 先用 `herdr pane layout` 數主 tab 的 worker，已滿 6 個就 `herdr tab create --cwd … --label <名稱> --no-focus` 開新 tab、在 `root_pane` 起 CLI，不再把主 session 切小；(4) `env` 的 `herdr-app status` 非「沒視窗」失敗改回 `window:false` 加 `window_error`（`spawn` 仍擋）；(5) hc 狀態映射：已結束且無狀態 → `gone`，`ended:false` 且 `reason` 為 `message` → `timeout` 並把 `reason` 放輸出上層；(6) 刪除 `app_layout.py` 沒有呼叫端的 `relayout`；(7) SKILL.md 補 hc 終端名稱限制（1-32 字、`a-z 0-9 - _`），`herdr-long-task.md` 輪詢改回 `read | tail -24`，guard 與 README 的第 7 個 worker 說法與實作一致。
- fix(handoff／hooks／guards)（最終審查）：`self-rotate.sh` 判斷 `/clear` 生效改為「session id 非空且與換之前不同」，讀不到不算成功；`herdr-env-context.py` 寫 hc-sessions 改為先寫暫存檔再 `os.replace`；`hc-run-agent` 允許 CLI 名稱前有路徑（`hc run --bg /x/bin/pi` 也擋，`--cwd /w/pi` 不誤擋），guard 說明改指 agent-dispatch skill 的 scripts 目錄下的 `mux.py`（不寫 `${CLAUDE_PLUGIN_ROOT}`），evidence 引用 herdr-pane-run-agent 的同類事故；`notification.sh` 註解改為 Herdr.app 比照 TUI 不發、app 是否自帶通知未驗證。
- fix(agent-dispatch)（實機驗收）：`app_layout.py` 的 `terminal.keep` 遇到 `no running terminal` 時重試（最多 10 次、間隔 0.3 秒）。實機上 `hc run --bg` 剛回傳、app 還沒看到新終端，第一次放置必定失敗，worker 變成 `visible:false` 不在畫面上。
- fix(agent-dispatch)（實機驗收）：`mux.py send` 遇到 hc 回 exit 9（agent 停在對話框或提示，打字會回答它）改回 `{"status":"blocked","hint":…}`，不再是 `backend_error`；實機上 agy 開頭的「Auto 模式已成預設」提示就會觸發。

## [0.24.1] - 2026-11-16

- fix(auto-session-title)：建議標題只認行首（可帶縮排、引言、清單或粗體符號）的「建議 session 標題…：/rename」行，句中引用這個句型不再套用；測試補第 7 項。起因：2026-11-16 一個 session 說明這支 hook 時寫了「…「建議 session 標題：/rename …」，要等你下一次送出訊息…」，下一次送出時整段被當成標題，session 改名成「…」，要等你**下一次送出訊息**才會套用…」。

## [0.24.0] - 2026-11-15

- feat(tower): 新增 `tower` skill 與 `skills/tower/scripts/tower.py`（航班登記表 takeoff／amend／beat／radar／override／landed／land-check／release），並新增三支 hook：`tower-context.py`（SessionStart 摘要在飛航班）、`tower-track.py`（PreToolUse／UserPromptSubmit 心跳、PostToolUse 記錄改動並提醒撞檔）、`tower-landing.py`（把東西落到預設分支前跑 land-check，超出範圍、撞檔、落後時擋下或詢問）。plugharbor 自用 `.plugharbor/tower.yml` 登記共用跑道；AGENTS.md「並行」條改成優先看 `tower.py radar`。起因：使用者實際遇過多 session 重工與衝突，未留文字紀錄（2026-11-15 裁決整套一次做完）。
- 實測 hook 延遲（macOS、Python 3.14，每次新開子程序）：beat ≈25.5 ms（100 次平均）、PostToolUse touch ≈25.1 ms（20 次）、beat 經 `run-py.sh` ≈50 ms、空 python 啟動 ≈10.5 ms。
- fix(tower)：整支分支審查修正（同屬 0.24.0）。`tower-landing`：merge／rebase 的目標分支或 push 的來源分支對到別班航班時（含已有自己航班、停在預設分支的 session，與沒有航班的主 checkout），改用那班航班做 land-check；預設分支上以本 worktree 航班 merge／rebase 視為同步，不套用超出範圍與落後；追蹤 `cd` 目標目錄（含 `git -C`、`~` 展開）。`tower-context`：摘要的在飛數排除失聯航班。`tower-track`：寫入前重讀，航班已 release／landed 就不寫，避免復活或改回 flying。`tower.py`：`land_check` 與重疊判斷排除 worktree 相同的他班（takeoff 無鎖造成的同 worktree 雙班）。起因：2026-11-15 整支分支審查（tower 實作完成後）。另含跨家族審查（agy）修正：`tower-landing` 模擬指令中的 `git checkout|switch <既有分支>`（`git checkout main && git merge feat/x` 算在 main 上落地）、預設分支上只有不指定 ref 或遠端預設分支才算同步（併入其他本地分支算落地，並比對其帶進來的檔）；`tower.py` 的 `beat --touched` 相對路徑以 cwd 為基準轉成 repo 相對路徑，`beat`／`amend`／`override` 寫入前重讀（已 release 或非 flying 不寫），`--paths` 反斜線轉正斜線；workspace `unattended` 的 takeoff 範例補必填的 `--goal`。
- 已知限制：`tower.yml` 只支援區塊式 `shared:` 清單；hook 指令解析是字串近似（引號內字樣會誤判，`env`／`sudo`／`bash -c`、`git pull`、`cherry-pick` 不涵蓋）；在預設分支上以本 worktree 航班 merge／rebase 只有不指定 ref 或目標為遠端預設分支才視為同步（不擋落後與超出範圍）；沒有 origin 的本地 repo 在預設分支上已 commit 的改動不計入核對；以他班分支為目標時該班未 commit 的檔也計入；`git push --all`／`--mirror` 與 upstream 為 main 的裸 `git push` 不核對；子 shell 內 `cd` 會外洩；beat／touch 寫入不加鎖；其他 CLI 沒有自動追蹤與硬擋（Codex 可能經 `hooks.json` 載入 hook，未驗證）。

## [0.23.4] - 2026-11-15

- fix(guards): 新增 `herdr-tab-create`（ask）與 `herdr-pane-run-agent`（deny）兩條 guard；`agent-dispatch` 補一行：替別的專案開不回報的長駐獨立 session 時也開新 tab，一樣用 `agent start` 帶模型參數。起因：2026-11-14～15 plugharbor 主 session 沒載入 agent-dispatch，兩次用 `herdr tab create`＋`herdr pane run <pane> claude` 開 session（重啟 Formwright 自動駕駛、lifecycle 3.0 試用），沒帶 model／effort、沒重排，也沒掛 worker 標記。

## [0.23.3] - 2026-11-15

- fix(retrospective): pi 的提問工具名改為 `ask_user_question`。起因：2026-11-15 lifecycle 3.0.0 在 Formwright 用 pi 試用，模型照 harness-terms 找 `ask_user` 找不到；已安裝的 `rpiv-ask-user-question` 擴充註冊的是 `ask_user_question`，參數與 `AskUserQuestion` 同格式，舊寫法的 `title`／`allowMultiple` 對照也不存在。

## [0.23.2] - 2026-11-14

- fix(agent-dispatch): `skills/agent-dispatch/scripts/ask.mjs` 問 codex 時改用 `-o` 把最後答案寫到獨立檔，只印答案；完整執行紀錄（stdout＋stderr，含 hook 訊息與 skill 原文）一律存到結果檔備查，並在答案後註明字元數與路徑。`skills/agent-mesh-check/scripts/clis.mjs` 的 `buildArgs` 加 `lastFile` 選項。起因：2026-11-14 產品化自動駕駛 session 回報 codex 審查的結果檔約 39 萬字元，答案還印兩次，主控只能 grep 最後一個「codex」行之後的段落。

## [0.23.1] - 2026-11-14

- fix(hooks): `reply-language-guard` 只掃最後一個回合起點之後的回覆。跨 session 訊息、subagent 交回、Stop hook 回饋都是 meta 的 user 列，也會開啟新回合；原本只從最後一則真正的提問算起，自動駕駛開場回合的一句英文在之後每個回合都被重擋。起因：2026-11-14 產品化自動駕駛 session 換新後，連續 5 個回合被同一句舊英文擋下（d 類回報）。

## [0.23.0] - 2026-11-14

- feat(handoff): 在 herdr 內（`HERDR_ENV=1`）寫完交接檔後自己換新：背景啟動 `skills/handoff/scripts/self-rotate.sh`，等 pane 閒置後送 `/clear`、`/reload-plugins` 與接續句，不必使用者手動清空。條件是使用者打了 `/handoff`、在 AskUserQuestion 同意，或無人值守；有還在跑的 subagent／背景工作／CI 等待就先等。不在 herdr 內照舊印接續句。腳本與 workspace plugin 的 unattended 換新腳本是同一份副本，測試會比對。
- feat(hooks): `compact-context` 壓縮後提示換新的時機：任務還沒做完、停在沒有背景工作的點才換，任務完成就不換；在 herdr 內指向 handoff 的 SKILL.md（使用者在場先問一次），否則建議使用者打 `/handoff`。版本落後提醒改成只陳述版本，做法統一看這句。
- fix(hooks): `compact-context` 的語言提醒明寫涵蓋工具呼叫的說明文字。
- 起因：2026-11-14 使用者指出換新 session 不只自動駕駛需要，要每個 session 自己判斷；使用者裁決在場先問一次、同意後自己跑完，只在任務中途的穩定點換。同日本 session 壓縮後 Bash 指令說明改用英文，原提醒只寫「回覆語言」。

## [0.22.0] - 2026-11-14

- feat(hooks): `compact-context` 壓縮後比對本 session 載入的 toolkit 版本與 `installed_plugins.json` 的已安裝版本，落後就提醒「告一段落時換新 session」；判斷不了就不提醒。
- feat(hooks): `ask-question-guard` 看到 `AGENT_DISPATCH_UNATTENDED=1` 就擋下 AskUserQuestion，叫 worker 照「（推薦）」做、把題目與選擇寫進結果檔的「主控裁決待確認」，不可逆操作寫進待決後停下。
- feat(agent-dispatch): 腳本一律用 skill 開頭的 Base directory，不 ls／glob 外掛快取；`reviewer` 正常回 JSON 且 `crossFamily: false` 才算湊不到別家，腳本報錯、印用法或輸出不是 JSON 算工具故障，重試一次仍失敗才同家審查並寫「工具故障，退回同家審查」；herdr pane 在無人值守時加 `--env AGENT_DISPATCH_UNATTENDED=1`。
- fix(agent-dispatch): `ask.mjs` 的封鎖到期時間改印本地時間並標時區（例：`2026-11-14 16:41（UTC+8）`）。
- 起因：2026-11-06～14 一個自動駕駛 session（壓縮 49 次）。壓縮後 Claude Code 已自動附上用過的 skill 與正確路徑，主控卻自己 glob 快取挑到舊版 0.9.3（沒有 `reviewer`），把報錯當成湊不到別家，之後十多段審查都悄悄降成同家；該 session 開了 9 天一直跑 0.13.0，漏了 8 版修正；11-08 worker 卡在選擇題，主控臨時寫自動按 Enter 的腳本；11-11 主控把 UTC 08:41 誤讀成本地時間、以為封鎖已過。

## [0.21.3] - 2026-11-13

- fix(hooks): `rm-scratch-allow.py` 先把同一條指令裡以純字面值賦值的變數代回（`S=/路徑; rm -rf $S/x`），重複賦值、在賦值前使用、前置環境變數寫法照舊不放行；多行指令換行後的 rm 原本被切成沒有目標的片段（只會多跳確認），一併修正。起因：使用者回報無人值守仍卡在 rm 確認（「A variable in this command can't be checked」）；重播 1270 條歷史 rm 指令，這兩項只多放行 2 條，其餘多是帶轉向、`$(…)`、迴圈變數的長指令，所以同時在 setup 範本拿掉 rm 的 ask 規則、交給 auto mode 判斷（deny 規則保留）。

## [0.21.2] - 2026-11-13

- transcribe、agent-dispatch、tidy-memory、retrospective、agent-mesh-check：description 壓到 160 字內（原 211～353 字），只留做什麼、何時用、觸發詞；細節在 SKILL.md 本文。起因：context-diet 量測五支合計每 session 約 1,070 tokens。
- user 層 rule `dispatch.md`（setup 範本）：模型等級枚舉縮成一句並指向 agent-dispatch 的 `routing.json`（權威本來就在那裡）。

## [0.21.1] - 2026-11-13

- fix(agent-dispatch): herdr 長任務的 cwd 信任檢查改為沿上層目錄找 `hasTrustDialogAccepted: true`，與 Claude Code 的信任繼承一致；原本只比對 cwd 本身是否出現在 `~/.claude.json`，沒開過的子目錄被誤判 missing，key 存在但未信任的反而判 ok。起因：開 worker 前誤判 yunguang-home 未信任（實際由上層 `/` 繼承），叫使用者先手動開一次 Claude Code，使用者已信任卻被多問一輪。

## [0.21.0] - 2026-11-13

- feat(hooks): 新增 `rm-scratch-allow.py`（PermissionRequest `Bash`）：`rm` 的每個目標解開 `..` 與上層 symlink 後都在暫存區（`<tmp>/claude-<數字>/<專案>/<session>/` 以下、路徑中的 `.tmp`／`.superpowers` 目錄以下），且整條指令只串 echo、cd、ls、grep、head、tail、cat、wc、不帶 `-i` 的 sed、`git status|log|diff|rev-parse|show|branch --show-current`，沒有 `$`、反引號、轉向、萬用字元時自動核准；其他不表態，照常跳確認。起因：自動駕駛與無人值守卡在 user 層 ask 規則（`rm -rf *` 等）的確認畫面，auto mode 也照跳；PreToolUse 回 allow 蓋不過 ask 規則（官方文件），PermissionRequest 回 allow 可放行（`claude -p` 對照實測）。以近一週實際 rm 指令重播，42 條中 17 條改為自動核准，其餘多是串了 heredoc、`git add`、`$(…)`（使用者回報）。

## [0.20.0] - 2026-11-12

- feat(hooks): 新增 `reply-language-guard.py`（Stop）：使用者最後一則提問以 CJK 為主，這回合卻有文字段在去掉程式碼、inline code、URL、路徑後含 3 個以上英文單字且沒有任何 CJK 字，就擋下一次，要求用使用者的語言重述結論。最後一則回覆在 Stop 觸發時常還沒寫進 transcript，所以另讀 payload 的 `last_assistant_message`。使用者在訊息裡明確指定要英文作答時也會擋一次（多一輪重述，第二次放行）。起因：0.19.0 的 `compact-context.py` 在壓縮後確實有注入，但 17:17 那次壓縮後仍連續 4 則英文回覆；以近兩天 transcript 重播，373 個中文回合中有 58 個含英文旁白（抽樣皆為真的英文，未見誤擋），漂移也不只在壓縮後（使用者回報＋feedback-review 回饋佇列 agent friction）。

## [0.19.0] - 2026-11-12

- feat(hooks): 新增 `compact-context.py`（SessionStart `compact`）：context 壓縮後注入一次「回覆語言、回合結尾格式、提問方式照使用者 CLAUDE.md 與 rules；摘要與續接提示的語言不代表要換語言」。起因：壓縮後接續無人值守，回報與 AskUserQuestion 連續多輪改用英文，直到使用者說「說中文」才發現；CLAUDE.md 早有「壓縮後也一樣」的文字，已證明擋不住，所以升級成 hook（feedback-review 回饋佇列 agent friction）。
- fix(hooks): `herdr-env-context.py` 注入句從「能用 subagent 就不開 pane」改為「長任務照判準表開 pane」，與 user 層 `dispatch.md` 同步。起因：這句被拿來推翻判準表的長任務列，一件數小時的實作被派成 subagent，跑 2h10m、context 31 萬，使用者無法 attach。注入字數比原本短。

## [0.18.2] - 2026-11-10

- tidy-memory Task 5 加「判定結果」：每組重複候選只判成合併／刪除其一／保留兩則，並註明換說法不算重複；Task 6 依此出題。
  起因：Windows 端 plugin-harvest（關鍵字 claude code memory management）評估後採納；判準概念借自 mem0 的記憶更新 prompt（Apache-2.0，只借概念，已記 `harvest-lock.json`）。
- tidy-memory「附帶事實」更正 claude-mem 描述：自動寫入 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 是 12.7.2 起的舊版行為，現行版（15.14.0）預設不動設定；「不要裝」的理由改為雙重注入 context 與改變 Read 行為。
  起因：同一次評估讀 claude-mem 原始碼，發現原描述過時。

## [0.18.1] - 2026-11-10

- fix(hooks): `dispatch-stop-guard.py` 的 block 輸出改用 `sys.stdout.buffer.write(... .encode("utf-8"))`，跟同目錄其他 hook 一致。起因：Windows 的 stdout 預設 cp950，Claude Code 以 UTF-8 讀，herdr worker 沒寫結果檔時看到的 Stop hook reason 整段亂碼，worker 讀不懂該做什麼；既有測試在 Windows 也因此 3 個 UnicodeDecodeError。

## [0.18.0] - 2026-11-09

- feat(hooks): `disabled-skills.py` 的 SessionStart 從完整清單改成一行名稱（`[toolkit] plugharbor 停用中：…`）；重開指令、SKILL.md 路徑、忽略指令改寫到 `~/.claude/disabled-skills/<專案雜湊>.md`，需要時才讀。用法也改了：agent 要先用 AskUserQuestion 問使用者（用它並重開／只這次用／不要），問過才用。新增 `disabled-skills.py ignore <項目> --cwd <專案>`：使用者回「不要」就寫進 `~/.claude/disabled-skills/ignore.json`，以停用的單位為準（整個 plugin 或單一 skill），而且只在當下專案生效；項目重新啟用時，自動從清單移除。起因：0.17.0 分不出「少用被 /doctor 關掉」和「刻意不要」（agent 會繞過使用者的決定去用），而且只要沒重開，就在每個 session、每個專案永遠注入，無法消掉。設計見 `docs/superpowers/specs/2026-11-09-disabled-skill-recovery-design.md`。
- feat(hooks): `disabled-skills.py` 加掛 UserPromptSubmit。使用者訊息命中停用 skill 的觸發詞才注入提示：觸發詞來自 SKILL.md 新的 frontmatter 欄位 `triggers`（單行 JSON 陣列，實測不會進 skill 清單），加上 description 裡「」括起的片語，長度不到 4 字的不算；英文字母不分大小寫，一則訊息最多 3 項。同一個 session 裡，同一項只提示一次；session 紀錄放在 `~/.claude/disabled-skills/sessions/`，7 天後清除。
- fix(hooks): 最終審查修正 5 項。
  - 忽略指令改用 `shlex.quote`：專案路徑含 `$(...)` 或 `"` 時，不會被 shell 執行，也不會把指令弄壞。
  - 設定檔存在但壞掉、或讀不到 marketplace 清單時，不清理忽略清單。之前遇到這種暫時性讀檔失敗，會清掉使用者回過的「不要」。
  - 英文片語兩端要求字邊界（`hangfire` 不會命中 `hangfires`）；description 裡不含空白的純英文單字（如 `commit`、`build`）不再當觸發詞。
  - 同 session 去重改以 `plugin:skill` 為單位，同一個停用 plugin 底下的多個 skill 都能被提示。
  - 專案根目錄優先用 `CLAUDE_PROJECT_DIR`，避免 session 內 `cd` 到子目錄後讀錯設定、對不上忽略清單。

## [0.17.0] - 2026-11-09

- feat(hooks): 新增 SessionStart hook `disabled-skills.py`。它依 user → project → local 設定，列出被明確停用的 plugharbor plugin（`enabledPlugins: false`）與被 `skillOverrides` 關掉的 skill，附重開指令（`claude plugin enable <p>@plugharbor --scope <層>`）和 marketplace clone 裡的 SKILL.md 路徑，agent 需要時當輪讀檔照做，再問要不要重開。沒有停用就不輸出。從沒啟用的專案層 plugin 不列，因為那是刻意不裝（例如專案自帶同類 plugin），列出來會誘導重複；只能手動叫用（`disable-model-invocation`）的 skill 也不列。user 層 rule（setup 的 home 目錄下 `shared/engineering.md`）「能力缺口」段同步改成依序找：先找 plugharbor（停用或沒裝的），再用 WebFetch 查 skills.sh 列候選，要安裝走 plugin-harvest，總長 384 → 377 字元。起因：在別的專案跑 /doctor 會把少用的 plugin 寫成 `false`，常寫在 user 層，所有專案一起失效；之後使用者或 agent 要用時，清單裡已經沒有它，也不知道它存在。

## [0.16.6] - 2026-11-09

- docs(agent-dispatch): §1 加「依風險升一級」：改動碰 `crossReview` 路徑樣式或超過 `maxLines` 行可用高一級，偏離查表結果時回報寫「升級理由：…」。§6 的 `herdr agent start` 範例固定帶 `-- <模型參數>`，並列出各家寫法。user 層 rule（setup 的 home 目錄下 `rules/dispatch.md`）同步加「派工帶模型」一行（派 Agent tool 時依等級表設 `model` 與 `effort`），新增 `setup/tests/dispatch-rule-sync.sh` 檢查它跟 `routing.json` 一致。起因是同家 subagent 從沒照等級表選模型、升級不記理由，還有 2 個 pane 啟動時沒帶模型參數。

## [0.16.5] - 2026-11-09

- docs(agent-dispatch): `skills/agent-dispatch/references/background-worker.md` 新增「macOS 防睡眠」：長任務期間不要蓋螢幕（Clamshell Sleep，caffeinate 擋不住）、要蓋就接電源加外接螢幕、`pmset disablesleep` 由使用者自己決定、怎麼查睡眠原因；`herdr-long-task.md` 加一行指路。起因是長任務跑到一半蓋螢幕又拔電源，Mac 睡了 2 小時、測試逾時。

## [0.16.4] - 2026-11-09

- docs(agent-dispatch): 派工 prompt 的共用規則加「授權範圍」：寫明可以改的 repo 與路徑，其他 repo 一律不動，沒寫明可以 push、發版就不做；herdr 收工步驟改成讀完結果檔就關 pane，不留著待命。起因是 worker 交回結果後 pane 沒收，worker 跑去另一個 repo 發版。

## [0.16.3] - 2026-11-09

- fix(agent-dispatch): 額度錯誤抓不到重置時間時，「out of credits」「insufficient credits」「refill」「billing」這類要人儲值的訊息改成封鎖 24 小時，其他維持 1 小時。之前一律 1 小時，codex workspace 沒額度時一小時後又被挑中，跑到一半才失敗。`quotaInfo` 在 `skills/agent-mesh-check/scripts/clis.mjs`，`dispatch.test.mjs` 補兩案例；SKILL.md 的手動延長規則改成只在封鎖到期後仍失敗時使用。

## [0.16.2] - 2026-11-09

- docs(agent-dispatch): 審查流程補三條規則：每次派審查前先跑 `route.mjs reviewer`，`crossFamily` 為 false 就直接走同家審查，不先送別家再等失敗；同家審查一律用新的 context；同一家同一天第二次遇到 workspace 沒額度時，手動延長封鎖到隔天（腳本預設只封鎖 1 小時）。新增 `skills/agent-dispatch/references/review-prompt.md` 審查 prompt 範本（第一輪整份審查、第三輪起定點核對）。起因是一夜的審查都寫死 `--to codex`，額度用盡後跑到一半才失敗。

## [0.16.1] - 2026-11-08

- fix(feedback-capture): 略過開頭是「唯讀任務」的訊息。agent-dispatch 派給 subagent 的唯讀問答 prompt 內文常含「漏掉」「不要再」「錯了」，被當成使用者糾正記進回饋佇列；`feedback-hooks.sh` 補「開頭命中不記、不在開頭仍記」兩案例。

## [0.16.0] - 2026-11-08

- feat(tidy-memory): 確認刪除的記憶檔不再直接刪，改搬到記憶目錄外的 `_gc_trash/<日期>/`，回報附搬回指令，使用者說「真刪」才清空；合併被併掉的檔也一樣。概念借自 affaan-m/ECC 的 config-gc（MIT）。

## [0.15.1] - 2026-11-06

- fix(retrospective): `--apply` 不再把當次情境寫進 skill。刪掉 P1 帶日期的標記、把 `apply-changes.md` 的事故段改寫成一句規則；`improvement-loop.md` 第 2 節新增「本文只寫通則，情境留在報告、帳本或 CHANGELOG」，`feedback-review` 一併適用。

## [0.15.0] - 2026-11-06

- feat(agent-dispatch): herdr pane worker 沒寫結果檔就結束時，Stop hook 也會攔一次。pane 開啟時帶 `AGENT_DISPATCH_RESULT` 與 `AGENT_DISPATCH_INTERACTIVE=1`；互動模式的提示是「做完就寫檔回報，還沒做完就不要寫、直接再結束一次」，避免等人回答時寫出「待決」的結果檔被當成完成。Ghostty 分割維持不設。
- fix: 修正 `dispatch-stop-guard.py` 註解誤寫 Ghostty 分割會設變數。

## [0.14.1] - 2026-11-06

- fix: `herdr-env-context.py` 與 `rules/dispatch.md` 的措辭會被讀成鼓勵開 pane，與「能用 subagent 就不開 pane」牴觸。改成只回答能不能開，該不該開仍照派工判準。

## [0.14.0] - 2026-11-06

- feat: 新增 SessionStart hook `herdr-env-context.py`。在 herdr 內時開場注入一行狀態，agent 不必為了確認能否開 pane 多跑一次檢查、再把它講給使用者聽；不在 herdr 內時不輸出。所有 source 都觸發（resume 可能換 pane，compact 會洗掉注入內容）。`rules/dispatch.md` 同步：有注明就直接開，沒注明才查，且檢查不單獨報告。

## [0.13.1] - 2026-11-06

- fix: Windows 的 Codex 上 11 支 python hook 全部沒跑。Codex 經 `powershell -Command` 執行 hook，`sh -c '…"…"…'` 內層的雙引號被 PowerShell 吃掉，sh 報語法錯誤。改成 `sh "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" <腳本>`，python3／python 的退路與 fail-open 移進新的 `hooks/run-py.sh`；測試鎖定指令只能有一層引號。

## [0.13.0] - 2026-11-05

- feat(agent-dispatch): `route.mjs pick <任務類型>` 只查不派，印出濾掉未登入與額度封鎖後的有序候選 JSON；`route.mjs reviewer <作者 CLI>` 照跨家族規則挑審查者。給要派同家 subagent、只需要知道模型的呼叫端（如 lifecycle:implement）用。

## [0.12.0] - 2026-11-05

- feat(retrospective): Step 3 歸屬表新增「重複出現的能力缺口」，列入轉交段並建議執行 `/research:plugin-harvest <領域關鍵字>`，不自動執行。

## [0.11.4] - 2026-11-04

- test: 並行上限測試在 CI（沒裝 claude）改放假 CLI 到 PATH；0.11.3 先檢查 CLI 是否存在，CI 上測不到上限。

## [0.11.3] - 2026-11-04

agent-dispatch 重新審查的 12 項修正：
- fix: 逾時殺整個程序樹（POSIX 程序群組、Windows `taskkill /T /F`），孫程序握著 stdout 時不再卡住、worker 不會一直停在 running。
- fix: prompt 以 `-` 開頭（如 YAML frontmatter）時，CLI 不再當成選項報錯；背景 worker 的 prompt 加固定前綴。
- fix: 背景 worker 預設不傳 GH_TOKEN／GITHUB_TOKEN／GITLAB_TOKEN 等推送用 token（`AGENT_DISPATCH_KEEP_ENV` 放行），並以 git 協定設定擋下 worker 的 push；文件寫明這是信任模型、不是沙箱。
- fix: Windows 上命令列超過上限時，直接回明確錯誤，不再出現誤導的 spawn 錯誤。
- fix: 並行上限加鎖；狀態檔寫入遇到 EPERM／EBUSY 會重試，寫不進去也不會把結果翻成 failed；pid 被重用時超時的 running 判成 failed。
- fix: 先驗參數與 prompt 檔再建 worktree，失敗不留孤兒分支；`--timeout` 必須是正數。
- fix: 跨家族審查的路徑判斷認得 Windows 反斜線；mesh 結果過時時，新裝的 CLI 不會被濾掉。
- fix: ask 模式的 claude／pi 給唯讀工具（Read、Grep、Glob／read、grep、find、ls），能自己讀檔回答。
- fix: 額度判定只看尾段且要有錯誤字樣，避免誤封鎖；`route.mjs block` 檢查 CLI 名稱。

## [0.11.2] - 2026-11-04

- fix: agent-dispatch 背景 worker（claude）寫不進結果檔。worker 的 cwd 是工作區的 `wt/`，結果檔在上一層，`acceptEdits` 只放行 cwd 底下；改為啟動時帶 `--add-dir <結果檔所在目錄>`。真 CLI 實測由 failed 轉 done。

## [0.11.1] - 2026-11-04

- fix: transcribe 小小 doctor 缺中文語音時的下載路徑改成新版 macOS 名稱（閱讀與朗讀 → 系統聲音 ⓘ → 聲音），舊名稱留在括號。

## [0.11.0] - 2026-11-04

- feat: transcribe 小小依首次真人試用調整。
  - 聲音依系統預設輸出分流：耳機時虛擬麥克風與耳機都播，使用者自己聽得到；喇叭時只從喇叭播、由麥克風收進會議，避免對方聽到兩份。認不出的裝置當耳機。
  - 叫小小「散會」時不送 claude，固定提醒要在 Claude 輸入（小小不能停錄音）。
  - 送 claude 時附完整逐字稿路徑，要它遇到不熟的名詞先查前文；原本只給最近 5 分鐘，前段談過的事會被說成沒提過。

## [0.10.1] - 2026-11-04

- test: advisor 測試的問題範例改用範例票號，不帶真實票號。

## [0.10.0] - 2026-11-04

- feat: transcribe 新增會議 AI 顧問「小小」（`skills/transcribe/scripts/advisor.py`，只支援 Mac）。
  - 線上會議錄音（`--source both`）中有人說「嘿，小小，……」時，以最近 5 分鐘逐字稿＋問題呼叫 `claude -p`，用 `say`（Meijia）經 BlackHole 2ch 與聚合裝置把兩三句口語回答送進會議。
  - 場合檔決定工具白名單、模型、人設與 MCP 設定；含寫入工具或不限指令的 `Bash` 拒絕啟動。範例 `advisor-mode.example.json`。
  - 白名單在 CLI 層鎖死：`--tools` 只開白名單內的內建工具、`--setting-sources user` 不吃專案／本機設定預先允許的工具、`--permission-mode dontAsk`、`--strict-mcp-config`（場合檔沒給 MCP 設定＝不載入任何 MCP）。實測從含 `Edit(/**)` 允許規則的專案目錄執行，仍無法寫檔。
  - 能量式 VAD 切句後才送 Whisper（避免靜音幻覺），轉錄提示不得含「小小」；「嘿」被轉成「黑」也算，單說「小小」不算。
  - 小小自己的聲音會被系統錄音錄到：播放前後 1.5 秒內的句子不比對、不進上下文。思考或播放中又被叫記為略過；只說「嘿，小小」就併下一句當問題（8 秒內沒下文就取消）。啟動時從最新分段的檔尾開始聽，開小小之前錄到的喚醒不補答。
  - 4 秒沒答先說「我查一下。」，30 秒逾時說「這題我會後補在會議記錄。」並記待補。發言寫進 `advisor.md`，與 `transcript.md` 分開。
  - `doctor` 開會前檢查聲音、claude、BlackHole、聚合裝置（缺時印建立步驟）、迴路與麥克風音量。
  - 合成語音驗收（Mac）：喚醒 10/10、非喚醒句誤觸 0/10、回答含「小小」不自我觸發、10 分鐘靜音 0 次發言、句尾到開口 6.4～7.3 秒。真人聲音經會議軟體的辨識率未驗證。

## [0.9.3] - 2026-11-04

- fix: `context-size-reminder.py` 門檻從 200K 拉到 400K，只當安全網；換題要不要 /clear 改由 agent 在主題轉換時建議（只看長度的提醒不知道有沒有換題，實際上沒人照做）。

## [0.9.2] - 2026-11-04

- fix: transcribe 線上會議錄音的審閱遺留問題。
  - worker 收尾時擷取端 `stop()` 拋例外，仍會關 ffmpeg 的 stdin，最後一段照常寫好。
  - 程序存活判斷改比對程式檔名（`python3.14`、`pythonw` 算 python），`notffmpeg`、`ffmpeg-helper` 這類名稱不再被當成錄音程序。
  - 錄音已停後再跑 `record stop`，不再對舊的 `ffmpeg_pid` 送訊號（PID 可能已被重用）。
  - worker 被硬殺、ffmpeg 還在寫最後一段時，`live` 仍視為錄音中，不會提早轉一段沒寫完的檔。
  - `live` 改用作業系統檔案鎖（macOS `flock`、Windows `msvcrt.locking`，程序結束即釋放），同一素材夾連續啟動兩次不會雙開；已完成後再 `live start` 只回報完成，不再多寫一行完成標記。
  - `live` 續做前先刪掉最後一個分段標記之後寫到一半的內容，被殺在寫入途中也不會重複追加。
  - 分段依數字排序，第 1000 段起不再排錯。
  - `live start` 新增 `--language`（預設 zh），並與 `transcribe` 一樣在術語提示超過上限時警告。

## [0.9.1] - 2026-11-04

- fix: agent-dispatch 測試在 Windows 上改用 npm 風格的 `.cmd`＋`.js` 假 CLI（沒有副檔名的 shebang 腳本在 Windows 不能直接執行，ask 與背景 worker 的測試原本全紅）。

## [0.9.0] - 2026-11-04

- feat: agent-dispatch 派工可指定模型與思考等級（`clis.mjs` 的 `buildArgs` 加 `model`／`effort`，四個 CLI 各用自己的參數），並能從錯誤訊息辨認額度用盡與重置時間（`quotaInfo`，抓不到時間就預設封鎖 1 小時）。
- feat: 派工路由（`agent-dispatch/references/routing.json`＋`scripts/route.mjs`）：任務類型 × 難度（top／standard／cheap）查表得出有序候選（CLI＋模型＋思考等級），濾掉 agent-mesh-check 最近一次沒通過的 CLI 與額度封鎖中的 CLI；改動碰到安全、資料、DB 結構、公開介面或超過 300 行時要跨家族審查，挑不同家族的審查者，湊不到才退回同家。`node route.mjs block <cli> <到期時間>` 手動標記某家先省著用。
- feat: `ask.mjs` 接上路由：`--type`／`--tier` 查表挑對象（`--to` 仍可直接指定），`--model`／`--effort` 可覆寫；額度用盡自動封鎖該家並改派下一個候選，全部不能用時 exit 75 並印最早解封時間；第一行固定印「交給誰、用哪級、理由」；輸出超過 16000 字元時全文寫進結果檔（預設 `<prompt 檔>.out.md`），只印前 4000 字元摘要。
- feat: 沒有 herdr 時的長任務（`agent-dispatch/scripts/bg.mjs`）。
  - **Ghostty 分割**：macOS 用 Ghostty 1.4 的 AppleScript 開看得見的分割，可帶工作目錄與環境變數，收工時用 id 關掉。spike 結論見 `skills/agent-dispatch/references/background-worker.md`。
  - **背景 worker**：每個 worker 開獨立 git worktree（分支 `dispatch/<名>`），由 detached 監督程序執行，結束後依結果檔寫入 `done`／`failed`／`quota` 狀態並發 macOS 通知。並行上限 4，遇到額度或逾時就降。Windows 尚未實機驗證。
- feat: 新增 Stop hook `dispatch-stop-guard.py`：被派出的 worker（環境變數 `AGENT_DISPATCH_RESULT` 有設）沒寫結果檔就想結束時擋下一次，要它先寫結果；一般 session 不受影響，壞輸入與 `stop_hook_active` 一律放行。
- docs: agent-dispatch SKILL 改寫。
  - 選對象：沒指定時依任務類型查表，回報照抄「交給誰、用哪級、理由」。
  - 新增「審查」「額度」「交棒」三節。交棒的做法放在新的 `skills/agent-dispatch/references/handoff-protocol.md`：交接上限 8000 字元，對方回覆「已接手」才算交出，否則所有權留在原 session。
  - 長任務改成三層偵測：herdr、Ghostty、背景；不再一律禁止背景 worker，改成條件成立才用。
  - 路由表的 12 組模型都實際 ping 過（2026-11-04），參數表補在 `skills/agent-mesh-check/references/cli-notes.md`。
- fix: Windows 上 npm 的 `.cmd` shim 改用 node 直接執行 JS 入口，不經 cmd.exe，多行 prompt 不再於第一個換行被截斷；解析不了的 `.cmd` 遇到多行參數直接報錯。
- fix: 額度判定只看輸出最後 2000 字元，「in N minutes/hours」優先於 ISO 時間，重置時間不在未來 7 天內就用預設 1 小時；背景 worker 有結果檔一律判 `done`。
- fix: 背景 worker 的並行上限調降 1 小時後自動恢復；`start` 立刻記監督程序 pid；監督程序出錯寫 `failed`，程序已不在時 `status` 顯示 `failed`；新增 `bg.mjs wait` 給沒有完工通知的平台阻塞等待。
- fix: 背景 worker 改用 `worker` 參數模式（claude 自動接受編輯、pi 開讀寫工具）；`scrubEnv` 清掉 `AGENT_DISPATCH_RESULT`，Ghostty 互動分割不再設它，避免 Stop hook 干擾巢狀派工與互動提問。

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
