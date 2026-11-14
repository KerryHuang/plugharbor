# Changelog

格式：每次改動 `hooks/`、`guards/`、`skills/`、`agents/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

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
