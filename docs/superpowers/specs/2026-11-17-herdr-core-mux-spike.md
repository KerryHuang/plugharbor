# herdr-core mux spike 結果

日期：2026-11-17　對應設計：[2026-11-17-herdr-core-mux-design.md](2026-11-17-herdr-core-mux-design.md)

環境：Herdr.app 視窗開著，core 由 launchd 乾淨環境啟動；`hc` 與 core 為 0.1.21（設計寫的 0.1.19 已過期）、`herdr-app` 0.1.15；
實測的 CLI：claude 2.1.326、codex 0.167.0、agy 1.5.9、pi 1.4.0。實測在自建的 space（`mux-spike`）與 `s-` 開頭的終端內進行，結束後全數 kill＋rm＋關 space。

## 與設計的差異（後續任務必讀）

結論沒有推翻設計的**決定**，但有四個**前提**不成立或要修正，影響後續任務：

1. **第 1b 節的前提不成立：四種 CLI 在 app 內都原生回報 OSC 7501**（見第 2 項）。Task 6「替缺狀態的 CLI 補回報」不需要寫整合檔；
   該任務縮成「驗證＋文件記錄」，不寫 install／uninstall 的新檔。
2. **`terminal.open` 沒有 `--target` 參數**（只有 `argv`、`folder`、`place`、`name`；`place` 相對於「目前 focus 的 pane」）。
   `pane.split --pane <id> --argv` 才有明確目標。另外**沒有調整 pane 比例的指令**（`layout.resize` 作用在版面節點，不是 split）。
   「依 `PLANS` 的比例排列」做不到，只能 50／50 對切＋`pane.swap`（見第 6 項）。這屬於設計已允許的「比例做不到完全一樣」，但 Task 3 的版型表要重寫成只用 50% 的樹。
3. **`hc run` 的 argv 以 core 的 PATH 解析，不是呼叫者的**：core 的 PATH 沒有 `~/.bun/bin`，`hc run --bg … pi` 會 `spawn_failed`。
   `mux.py spawn` 要先在呼叫者環境用 `shutil.which` 解出絕對路徑再交給 hc（Task 1 要加）。
4. **「完成」的狀態是 `done`，且停在 `done`**：輪次結束後 `status` 變 `done` 並維持，不會自己回 `idle`（`idle` 只出現在剛啟動、或使用者看過之後）。
   `mux.py` 的狀態映射把 `done` 與 `idle` 都當「輪次結束」；`hc wait`／`hc send --wait` 在 `done` 就回傳。

## 逐項結果

### 1. 不經 hc 判斷 core 在不在

- 指令：`hc --help`、`hc server --help`、`hc server start --help`、`hc run --help`；對 binary 做 `strings` 找環境變數。
- 結果：**沒有「不自動啟動」的旗標或環境變數**。`hc server status` 也沒有；可調的只有 `HC_SESSION`、`HC_SOCKET`（換 session／socket，不是禁止啟動）。
- 可靠的替代：直接連 Unix socket，不經 hc。
  - core 在跑：`socket.connect(~/.local/state/herdr-core/default/default.sock)` 成功（socket 路徑也寫在同目錄的 `core.lock` 檔內，一行）。
  - 路徑不存在：`FileNotFoundError`（errno 2）。
  - socket 檔還在但沒人聽（stale，實測 bind 後關閉不 unlink）：`ConnectionRefusedError`（errno 61）。
  - 三種情況都能分清楚，**以 connect 成功為準，不用檔案存在判斷**。
- socket 路徑解析：`$HC_SOCKET`，否則 `${XDG_STATE_HOME:-~/.local/state}/herdr-core/${HC_SESSION:-default}/default.sock`（`core.lock` 內容可驗證）。
  路徑太長（> 約 100 字元）時 AF_UNIX 會報 `path too long`，測試用的暫存路徑要短（`HC_SESSION` 也一樣，core 會提示 `use a shorter HC_SESSION`）。
- 不建議 `pgrep -f herdr-core`：會同時命中 `herdr-core connect`（app 的連線）與 `herdr-core hold`（holder），core 掛了而 holder 還在時會誤判。
- 結論：`mux.py` 用 socket connect 判斷 core_running；沒跑回 `{"error":"core_not_running",…}`。
  （未驗證：core 真的沒跑時 `hc` 的行為，因安全規則不能停 core；設計已記錄為會自動啟動。）

### 2. 四種 CLI 的狀態

指令形式：`hc run --bg --no-notify --name s-<kind> --cwd <受信任目錄> <cli> <參數> "<短任務>"`，每 0.5 秒 `hc get --json` 記錄 `status`。

| CLI | 起法 | status 序列 | 結論 |
|---|---|---|---|
| claude | `claude --model haiku --effort low "<任務>"` | `null` → `{app:claude-code,state:working}` → `{state:done}` → `done`＋`msg`（回覆摘要） | 原生回報 |
| codex | `codex --no-daemon -m gpt-6.1-sol -c model_reasoning_effort=low "<任務>"` | `null` → `{app:codex,state:working}` → `done` | 原生回報 |
| agy | `agy --model gemini-3.8-flash-low -i "<任務>"` | 起動時 `blocked`（`kind=auth`「Sign in required」一閃）→ `blocked`（`kind=permission`「Trust this folder?」）→ 信任後 `working` → `done`＋`msg:"OK"` | 原生回報，`app` 為 `antigravity`，含 blocked 與 kind |
| pi | `<絕對路徑>/pi --model claude-bridge/claude-haiku-5-5:low "<任務>"` | `null` → `{app:pi,state:idle}` → `working` → `done`＋`msg` | 原生回報 |

- **沒有缺狀態的 CLI**。pi 原生回報（它的 `herdr-agent-state.ts` 是對 herdr TUI 的 socket 報告，不送 7501，app 內不受它影響）。
- `hc get` 的 `turn` 在每輪結束 +1；`done` 狀態在 `msg` 到達前會先出現一次無 `msg` 的 `done`（claude 觀察到：先 `done` 約 2 秒後才補 `msg`）。
- **各 CLI 啟動時的對話框會卡住第一則訊息**，且多半在對話框期間 `status` 仍是 `null`（只有 agy 會回報 `blocked`）：
  - claude：「Allow external CLAUDE.md file imports?」（目標專案的 `CLAUDE.md` 引用了目錄外檔案）；預設選項是安全的「No」，`hc keys <t> enter` 即可，之後 argv 帶的任務照常送出。
  - codex：「Hooks need review」；選第 3 項「Continue without trusting」（`hc keys <t> down down enter`）。
  - agy：「Trust this folder?」，專案資料夾、家目錄、worktree 都沒被信任；實測用一個空的暫存資料夾、按 enter 信任後才進到 working。
    （副作用：agy 的設定多了一筆該暫存資料夾的信任紀錄；其他三個 CLI 沒有留下持久紀錄，pi 選了「this session only」。）
  - pi：「Trust project folder?」，選「Trust (this session only)」（`down down enter`）。
  - 結論：`mux.py spawn` 回傳後要有「ready 偵測」：`status` 不是 `idle`／`working`／`done` 時用 `read` 檢查畫面，遇到對話框就回報給呼叫端（不替使用者按「信任」）。
- agy 的互動模式 prompt 要用 `-i`，直接放位置參數會報 `unexpected argument`；與 `cli-notes.md` 的 `-p`（無互動）不同。
- 起 agent 時 `hc run` 的回傳：`{"address":"t1d","agent":"claude","cwd":…,"name":"s-claude","state":"live","turn":0}`。

### 3. OSC 7501 格式

- 官方文件（`hc --skill`、`hc schema`、`~/.config/herdr-app/AGENTS.md`）只說「狀態來自 OSC 7501，值為 idle／working／done／blocked／error」，沒寫逸出序列；以下由 `strings` 與實測得到。
- 查詢回應片段：`ESC ] 7501 ; ?:states=idle,working,done,blocked,error:kinds=permission,question,auth`，欄位以 **`:` 分隔**、`key=value`。
- 實測序列（在 hc 終端內，輸出到 `/dev/tty`，且程式要保持在前景，見下）：

  ```sh
  printf '\033]7501;state=working\007' > /dev/tty
  printf '\033]7501;state=blocked:kind=permission\007' > /dev/tty
  printf '\033]7501;state=working:app=myapp:progress=50\007' > /dev/tty
  printf '\033]7501;state=working:id=sub1:app=zz\007' > /dev/tty   # 非 root 記錄，進 hc get 的 records.sub1
  ```

- 欄位：`state`（必填）、`app`、`kind`（`permission|question|auth`，blocked 時）、`progress`（0..100）、`id`（有 id 的是次要記錄，無 id 是 root 記錄，root 才是 `hc get` 的 `status`）。
  `msg`、`title` 在 schema 裡有，但**手送的 `state=working:msg=hello` 會被丟掉**（`state` 生效、`msg` 不進 `status`）；
  真實 CLI（claude、agy、pi）的 `done` 帶 `msg` 有進來，推測只有 `done` 接受 `msg` 或需特定編碼，未驗證。
- 分隔符號用 `;`（`state=working;msg=hello`）時整筆被忽略，**一定要用 `:`**。
- **shell 本身的狀態會在 prompt 回來時被清掉**（文件所述「root interactive shell returns to foreground」）：
  只有「program 在前景執行期間」狀態才存在。測試時要讓 program 跑著（例如 `sleep`）；序列一送完就回 prompt，`hc get` 看到的是 `null`。
- 驗證結果：working／done／idle／blocked（`kind=question`、`permission`）／error 全部改變 `status`；程式結束後 `status` 回 `null`、`reported` 仍為 `true`。
- 由於第 2 項四種 CLI 都原生回報，**Task 6 不需要自己送 7501**；本節格式留作測試 stub 與日後擴充用。

### 4. `<hc from>` 包裝

- 方式：在 hc 終端 `s-sh`（`HC_TERMINAL_ID=t13`）內執行 `hc send --wait s-claude "…"`。
- 包裝：Claude 畫面收到的是 `❯ <hc from="t13 s-sh">測試A：只回 A，不要用工具</hc>`（**對 agent 終端會包裝**，沒有 `reach=` 屬性）。
- 同一終端內改用 `env -u HC_TERMINAL_ID hc send --wait s-claude "…"`：Claude 畫面收到 `❯ 測試B：只回 B，不要用工具`，**原樣、無包裝**。
- 從 TUI 內的 Claude Code Bash（沒有 `HC_TERMINAL_ID`）呼叫 `hc send` 同樣不包裝。
- 結論：設計的決定成立——`mux.py` 呼叫 `hc send` 時從環境移除 `HC_TERMINAL_ID` 即可，不需要 `notes = false`。
- `hc send --wait` 回傳：`{"started":true,"status":"done","turn":3,"wait":{"ended":true,"reason":"status","status":"done","terminal":"t1d","turn":4,…}}`；
  不帶 `--json` 在終端內是人類可讀的兩行（`sent at turn N (...)`、`<t> done, turn M. Read: hc read <t>`）。

### 5. self-send

- 在 claude 終端（`hc run` 起的，環境帶 `HC_TERMINAL_ID`）請它用 Bash 執行 `( sleep 4; env -u HC_TERMINAL_ID hc send "$HC_TERMINAL_ID" /status ) &`；
  輪次結束後 `/status` 被當成 slash command 執行，畫面出現 Status 對話框（版本、cwd、模型），**沒有 `<hc …>` 標籤**。
- 結論：設計第 4 節的 self-rotate 在 hc 下可行，`/clear`、`/reload-plugins` 同理（同為 slash command 原樣送達）。
  實測 `/status` 對話框要 `hc keys <t> esc` 關閉；self-rotate 用的指令沒有對話框。
- 畫面可得到 session id（`/status` 的 `Session ID`），但 `hc get` 沒有；設計第 3 節的 hook 寫檔做法仍需要。
  `hc get --json` 欄位實測：`address, argv, cols, created_ms, cwd, die_with_parent, exit_code, finished_ms, first_message, foreground, identity, keep, labels, name, notify, parent, paste_gap_ms, pid, reason, records, reported, rm, rows, screen, signal, state, status, status_ms, stop, submit, template, title, turn`。
  其中 `title` 是 agent 的 session 名稱（非 id）。

### 6. 版面（視窗開著）

space 與 tab 取得：

- `herdr-app do space.new --name <n> --folder <dir>` → `{"space":"sp…","tab":"tb…","terminal":"t15"}`，自帶一個 zsh 終端（主 pane）。
- `herdr-app ls` 給 `spaces[].tabs[].terminals[]` 的 `terminal`（hc 位址）、`pane`（pane id）、`name`（hc 名稱，沒名稱是 null）、`status`、`app`。
- `herdr-app status` 給目前 `space`／`tab`／`focused_pane`（只有目前 focus 的那個）。**找主 session 的 pane**：用 `ls` 並以主 session 終端的 hc 位址（`HC_TERMINAL_ID`）比對 `terminal` 欄，取其 `pane`。

四種放置法的實測：

| 做法 | 指令 | 回傳 | 位置 | hc 名稱 |
|---|---|---|---|---|
| A. `pane.split` | `herdr-app do pane.split --direction right\|down --pane <pane> --argv '["sh","-c","…"]'` | `{pane, terminal}` | 切**指定 pane**（可精確指定，不必 focus） | 無（`name` 為 null） |
| B. `terminal.open` | `herdr-app do pane.focus --pane <pane>`，再 `terminal.open --place right\|down --name X --argv '[…]'` | `{pane, terminal}` | 切**目前 focus 的 pane**；沒有 `--target` | 無（`--name` 對 right／down 無效） |
| C. `hc run` 加 label | `hc run --bg --name s-x --label herdr.space=<id> --label herdr.tab=<id> …` | hc 的 JSON（`address`）；pane 需再 `herdr-app ls` 查 | **位置由 app 決定**：切該 tab 最後一個 pane 並排在右側（試過先 focus 別的 pane，不影響） | **有**（可帶 `--name`、`--no-notify`、`--parent`） |
| D. `hc run --bg` 後 `terminal.keep` | `hc run --bg --name s-x …`，再 `herdr-app do pane.focus --pane <p>`、`terminal.keep --terminal <tN> --place right\|down` | `{pending:true, terminal, pane, tab}` | 切**目前 focus 的 pane**（在目前 focus 的 tab） | **有** |

- 只有 `herdr.space` 沒有 `herdr.tab` 的 label：在該 space 開**新 tab**（對應設計的「第 7 個起開新 tab」，但新 tab 名稱是編號）。
- C 與 D 的 `terminal` 位址要用 `hc get <name>` 取 `address`；`terminal.keep` 吃 `tN` 位址，**不吃 hc 名稱**（給名稱會報 `no running terminal`）。
- 比例：每次切對半（左右或上下），**沒有指令能指定比例**；`layout.resize {id,px|weight}` 的 `id` 是版面節點（側欄、面板），不是 pane。
  實測：主 pane 切一次 → 主 50%／worker 50%；再切主 pane 一次 → 主 25%／新 25%／舊 50%（**反覆切主 pane 會把主 pane 越切越小**）。
  要保住主 pane：永遠切「worker」，不再切主 pane。
- `pane.swap {pane, target}`：同 tab 內兩 pane 對調位置，實測成功（`{"ok":true}`）；可用來把新 worker 換到想要的位置。
- 副作用：`pane.split`／`terminal.open` 會讓**新 pane 取得 focus**；`pane.focus` 改變使用者目前的 focus。這是使用者可見的行為，設計文件需記一筆。
- 建議（Task 3 builder 採用）：
  - 開 worker：**D**（`hc run --bg --name … --no-notify` 保有名稱＋父子關係，再 `pane.focus` 到要切的 worker pane，用 `terminal.keep --place right|down` 放進視窗）；或不需要名稱時用 **A**。
    要能精確指定被切的 pane，A 最穩（不依賴 focus）；D 的名稱與 `--no-notify`、`--parent` 較好。兩者擇一，其餘不用。
  - 版型只用 50% 切法：1 個 worker 在主右側；2 個再把第 1 個 worker 下切；3 個再把第 2 個 worker 下切；依此往下，主 pane 恆為 50% 寬、所有 worker 擠在右半。
    這滿足設計底線「主 session 不小於其他任一格、不被關、不被搬離」。具體樹狀由 Task 3 決定。
  - 回傳的 ID：A、B 回 `{pane, terminal}`；D 回 `{pending, terminal, pane, tab}`；C 只回 hc 位址。`mux.py spawn` 回傳 `{"id":"<hc 位址>","pane":"<pane id>"}` 即可。
- `herdr.seen` label 由 app 自動加；`keep` 欄位：app 開的終端 `keep:true`（遺失後替換成 shell），`terminal.keep` 剛放進去時先是 `false`（`pending`）。

### 7. 關閉

- `hc kill <t>`（不必 `rm`）後視窗 pane **立即消失**，並且該 tab 只剩這一個 pane 時整個 tab 也消失（實測 C 的 `s-lab`、A 的無名終端、單獨 tab 的 `s-lab2`、D 的 `s-k1`，`herdr-app ls` 都不再列出）。
- 終端狀態變 `finished`（`reason: killed`）；`hc rm <t>` 只移除紀錄，不影響視窗。
- 結論：**不需要 `pane.close`**；設計的「`hc kill`＋`hc rm`」成立。但 `hc kill` 後 `hc get` 仍能看到 `finished` 紀錄，直到 `rm`。
- 另：程式自己結束（如 `sleep 600` 到期）pane 也消失，不留殘影；agent 任務完成後若不 kill，pane 會一直留著。
- `herdr-app do space.close --id <id> --confirmed true` 關 space（含所有終端）；app 的「recent」清單會留下 space 名稱與資料夾（app 內部狀態，沒有指令可清）。

### 8. env 前綴

- hc 終端預設環境（`hc run` 起的、經 `env` 列出）：`HC_SCOPE`、`HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`TERM_PROGRAM=ghostty`、`COLORTERM=truecolor`、`TERM=xterm-256color`，
  加上 core 的登入環境（`HOME`、`PATH`、`SHELL`、`LANG`、`SSH_AUTH_SOCK`、`TMPDIR` 等）。**沒有** `HERDR_*`、`CLAUDECODE*`、`CLAUDE_CODE_*`。
  PATH 是 core 的（`~/.local/bin:/usr/local/bin:系統目錄:…:/opt/homebrew/bin`），**沒有 `~/.bun/bin`**（見差異 3）。
  前景模式（不帶 `--bg`）的 `hc run` 另外多了 `PAGER=cat`、`GH_PAGER=cat`、`GIT_PAGER=cat`；`--bg` 與 shell 終端沒有。
- 實測 `hc run … env -u HC_SCOPE -u HC_TERMINAL_SOCKET -u TERM_PROGRAM MUXK=hello MUXK2='a b' sh -c '…'`：
  `MUXK=hello MUXK2=a b`（K=V 進得去，含空白的值正確），`HC_SCOPE`、`HC_TERMINAL_SOCKET`、`TERM_PROGRAM` 皆為空（被 unset）。
  `--bg` 搭配 `env -u HC_TERMINAL_ID FOO=bar sh -c …` 也成立（`FOO=bar ID=[]`）。
- 結論：`env -u … K=V <cli>` 前綴在 `hc run` argv 下可用。core 不繼承呼叫者環境，所以「清污染」只在 core 是從 TUI／Claude Code 內啟動時才需要；前綴照設計保留，成本低。
- 設計的「`scrubEnv` 再加濾 `HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`HC_SCOPE`」仍有意義：拋棄式 CLI（`ask.mjs` 直接 spawn）不經 hc，會繼承呼叫者的 `HC_*`。

### 9. 視窗沒開時 `herdr-app status`

- 直接關掉使用者視窗不在安全範圍內；改用 `HERDR_APP_HOME=<空的短路徑暫存目錄>` 指向沒有視窗的 home（文件說 `HERDR_APP_HOME` 選擇視窗）。
- `herdr-app status`、`herdr-app ls`、`herdr-app do tab.new --name x` 全部：
  stderr `herdr-app: no Herdr window at <home>/herdr-app.sock: No such file or directory (os error 2)`，**exit code 2**。
- 視窗開著：`status`、`ls`、`do …` exit 0。
- 路徑過長（> SUN_LEN）時訊息變成 `…: path must be shorter than SUN_LEN`，同樣 exit 2；與「沒視窗」同碼，判斷時只看 exit code 2＋訊息前綴 `no Herdr window`。
- 結論：`window` 欄位 = `herdr-app status` exit 0；exit 2 且訊息含 `no Herdr window` 才是沒開（其他失敗不當作沒開）。
  限制：這是以 `HERDR_APP_HOME` 模擬，不是實際關閉視窗，**真實關視窗後的行為未驗證**。

## 其他觀察（給後續任務）

- `hc kill` 對 agent 終端立即結束，無確認；`hc kill`＋`hc rm` 後 `hc ls --all` 乾淨。`hc ls`（不含 `--all`）只列 live。
- 啟動 agent 後第一則訊息放在 argv（`hc run --bg … claude "<任務>"`）有效；`first_message` 欄位只有 template 才有值，非 template 啟動時為 `null`，不能用它判斷任務有沒有送出。
- `hc get`／`hc ls` 的欄位在沒值時會省略（`name`、`labels` 可能缺），解析時用 `.get`。
- app 視窗有「Herdr 0.1.16 is ready／Restart」的更新提示；實測全程沒有點，也沒有動 core。
- 清理確認：`hc ls --all` 只剩實測前就存在的 3 個 finished 終端（`t9`、`t11`、`t12`，不是這次建的）；`herdr-app ls` 的 `spaces` 為空；沒有殘留 `s-*` 終端；`/tmp` 暫存目錄已刪。
