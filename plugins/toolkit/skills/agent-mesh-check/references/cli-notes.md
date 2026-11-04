# 四個 agent CLI 的無互動呼叫

`scripts/clis.mjs` 的 `buildArgs` 是權威，本檔記錄參數為什麼這樣選，以及會踩的坑。agent-dispatch 也引用本檔。

## 參數（2026-10-23 在 macOS 實測：claude 2.1.309、codex 0.163.0、agy 1.4.5、pi 1.4.0）

| CLI | 唯讀回話（probe） | 自動執行 shell（driver） | 派工短問答（ask） |
|---|---|---|---|
| claude | `-p <p> --tools ""` | `-p <p> --allowedTools Bash` | `-p <p> --tools Read,Grep,Glob` |
| codex | `exec --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check -s read-only <p>` | 同左，改成 `-s danger-full-access` | `exec --ephemeral --skip-git-repo-check -s read-only <p>` |
| agy | `-p <p> --sandbox --disable-slash-commands` | `-p <p> --dangerously-skip-permissions` | 同 probe |
| pi | `-p <p> --no-tools --no-session` | `-p <p> --tools bash --no-session` | `-p <p> --tools read,grep,find,ls --no-mcp --no-session` |

背景 worker（agent-dispatch `bg.mjs`）另有 `worker` 模式：claude `-p <p> --permission-mode acceptEdits --allowedTools Bash`、pi `-p <p> --tools read,bash,edit,write --no-session`，codex 與 agy 同 driver。

說明：

- ask 模式下 codex 會保留使用者設定（模型、MCP），代表日常實際的用法。
- ask 模式的 claude／pi 給唯讀工具，讓「小型唯讀調查」能自己讀檔。claude `--tools` 吃逗號分隔的內建工具名（`""` 是全關）；pi 1.4.0 文件（`docs/cli.md`）的範例就是 `--tools read,grep,find,ls`，`--tools` 不會移除 MCP 工具，所以另加 `--no-mcp`。2026-11-04 macOS 實測：兩者都能讀 cwd 底下的檔並正確回答。
- prompt 以 `-` 開頭（如 `---` frontmatter）時 claude 會報 `unknown option`（2026-11 實測）。`buildArgs` 在這種 prompt 前補一個半形空格：常見的參數解析器都以第一個字元是不是 `-` 判斷選項，空格開頭就當位置參數或選項值，模型讀到的內容只多一個空格；其他 prompt 原樣傳。2026-11-04 macOS 實測：claude、codex、agy、pi 收到 `---` 開頭的 prompt 都正常回答，沒有被當成選項。
- driver 的 codex 一定要 `danger-full-access`：read-only 沙箱會擋網路，被叫起的 CLI 就連不到模型。

## 指定模型與思考等級（2026-11-04 在 macOS 實測：claude 2.1.317、codex 0.166.0、agy 1.4.12、pi 1.4.0）

`clis.mjs` 的 `buildArgs(name, mode, prompt, { model, effort })` 依下表組參數；agent-dispatch 路由表（`../../agent-dispatch/references/routing.json`）的 12 組都實際 ping 過。

| CLI | 模型 | 思考等級 | 查可用模型 |
|---|---|---|---|
| claude | `--model <別名或 ID>`（`opus`、`sonnet`、`haiku`） | `--effort <level>` | 別名即可 |
| codex | `-m <model>` | `-c model_reasoning_effort=<level>` | 沒有列表指令；看 `~/.codex/config.toml` 的 `model` |
| agy | `--model <id>` | `--effort <level>`（模型 ID 本身也帶等級，如 `gemini-3.8-flash-high`） | `agy models` |
| pi | `--model <provider>/<id>:<thinking>` | 沒給模型時 `--thinking <level>` | `pi --list-models`；走 Claude 訂閱用 `claude-bridge/` |

## 已知坑

- **stdin 一律關閉**：`pi -p` 只要 stdin 沒關，就會無限等待。用 shell 呼叫時加 `< /dev/null`。
- **codex 很耗 token**：保留使用者設定時，一次 PING 約 3 萬 token，因為會載入 user 層的 rules、hooks、plugins。加上 `--ignore-user-config --ignore-rules` 後約 1.4 萬，代價是用 codex 的預設模型。
- **codex 會把 prompt 原文印進輸出**：如果判斷成功的方式是「prompt 叫它照抄，輸出裡有那段字就算過」，就算模型沒回話也會假通過。驗證時改成要求它把隨機字串轉成大寫，再比對大寫版。
- **codex 的回答可能印兩次**，前後還夾著 session 標頭和 token 統計。只檢查輸出裡有沒有預期字串，不要整段比對。
- **agy 常被設成 alias**：使用者的互動 shell 裡可能是 alias，例如帶 `--dangerously-skip-permissions`，但子程序看不到 alias。腳本一律找真正的執行檔，參數自己帶。
- **巢狀 session**：Claude Code 會設 `CLAUDECODE` 和 `CLAUDE_CODE_*`，codex 會設 `CODEX_*`。從某個 CLI 裡再叫另一個之前要清掉這些變數，`scrubEnv` 會處理，但 `CODEX_HOME` 要保留。
- **Windows**：
  - codex 和 pi 常是 `.cmd` 包裝，Node 的 spawn 要經過 shell，參數也要自己加引號，`run()` 已處理。
  - 各 CLI 的 shell 不同：claude 用 Git Bash，codex 用 PowerShell，agy 看起來是 cmd。PowerShell 遇到開頭是帶引號的路徑會報錯，也不認 `\"` 跳脫。所以第 3 層不把 B 的整串指令交給 A，而是先寫一支 `call-<A>-<B>.mjs`，A 只要跑 `node call-<A>-<B>.mjs`（2026-10-23 Windows 實測 codex→claude 因此失敗後修正）。
  - 子程序輸出一律用 UTF-8 解碼。
  - 命令列有長度上限：CreateProcess 32767 字元，經 cmd.exe 8191。`run()` 在 spawn 前估算，超過就直接回「prompt 太長」，不讓 spawn 丟出誤導的錯誤；prompt 太長時改把內容寫進檔案、prompt 只放路徑。
- **逾時要殺整個程序樹**：CLI 起的孫程序握著 stdout 時，只殺直接子程序的話 `close` 要等孫程序結束（實測 `sleep 8 & sleep 8` 逾時 1 秒要 8.4 秒才回）。`run()` 在 POSIX 用 detached 開新程序群組、逾時殺 `-pid`，Windows 用 `taskkill /T /F /PID`；殺完最多再等 2 秒就回 `timedOut`。父程序結束或收到 SIGINT／SIGTERM／SIGHUP 時也會殺掉還在跑的群組。
  - 用 Python 處理時要設 `PYTHONUTF8=1`，否則會用 cp950。
- **agy 沒有真正的唯讀**：
  - `-p` 搭配 `--mode plan` 只會產出計畫檔、等人核准，不會回答問題，所以不用 plan 模式。
  - `--sandbox` 只限制 shell 指令，它自己的 `write_file` 工具照樣能寫檔（2026-10-23 實測寫進暫存目錄）。
  - 使用者的 agy 設定若在 `permissions.allow` 放了 `write_file(*)`、`command(*)`，無互動模式下寫檔不會先問，參數層擋不住。
  - 派工短問答只能在 prompt 開頭加唯讀指示當作軟防線。要硬擋，得由使用者自己收窄 agy 的 allow 清單。
- **agy 回應較慢**：一輪約 8～12 秒；互叫一組約 20 秒。
