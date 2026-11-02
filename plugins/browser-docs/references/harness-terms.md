# Harness 用語對照（Claude Code ↔ Pi）

本 plugin 的 skill、agent、reference 以 Claude Code 用語撰寫。
在 Claude Code 照字面執行，本檔不必讀。
在 Pi 執行時，先讀本檔，把下表左欄換成右欄再照做；步驟、規則、收尾條件不變。
**本檔右欄只適用 Pi**：Codex 等其他 harness 讀到本檔時忽略對照表，照自己原本的工具與慣例執行；
Codex 沒有 `AskUserQuestion` 時，提問改純文字、一次一題，建議選項置首標（推薦）。
Pi 經 claude-bridge 時模型會自稱 Claude Code，仍以本檔為準。

## 路徑與參數

| Claude Code | Pi |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | plugin 根目錄＝SKILL.md 所在目錄往上兩層（`skills/<skill>/SKILL.md` → plugin 根）。Pi 不代換這個變數：寫進工具呼叫或 shell 指令前，先換成絕對路徑；shell 裡的 `${CLAUDE_PLUGIN_ROOT}` 在 Pi 是空字串。 |
| `$ARGUMENTS` | `/skill:<name>` 後面的文字（Pi 把它附在 skill 內容後當使用者請求），沒有就用觸發本 skill 的那則使用者訊息。 |
| `${CLAUDE_CODE_SESSION_ID}` | Pi 沒有對應值。依賴它的量測（例如讀 Claude transcript 估算 context 用量）在 Pi 上略過，回報時註明「Pi 未量測」。 |
| `<plugin>:<skill>`、`/<plugin>:<skill>` | Pi skill 名稱不帶 plugin 前綴：`<skill>`，手動觸發用 `/skill:<skill>`。 |
| `/reload-plugins` | Pi 以本機 checkout 載入，改版後用 `/reload`。 |
| `.claude/rules/`、`CLAUDE.md` | 這些是 workspace 檔案，Pi 上照路徑直接讀。 |

## Skill frontmatter

下列 Claude 專屬欄位在 Pi 上不報錯也不生效：

| 欄位 | Pi 上的處理 |
|---|---|
| `argument-hint:` | 只是提示，參數照 `$ARGUMENTS` 列取得。 |
| `model:` | Pi 用當前 session 的模型跑 skill，不切換。 |
| `context:`（值 `context: fork`） | Claude 會在無對話歷史的子 context 跑本 skill。Pi 上要保留這份隔離時，派一個子 session 跑：互動 session 用 `subagent`（`skills` 帶本 skill 名，`task` 帶參數與 plugin 根絕對路徑）；自動退出的 session 用下方「同步派工」的 `pi -p`。 |

## 工具

| Claude Code | Pi |
|---|---|
| `AskUserQuestion` | `ask_user`。一次呼叫只問一題：多題批次改成同一回合依序多次呼叫；`options` 的 label／description 對應 `title`／`description`；`multiSelect: true` 對應 `allowMultiple: true`；`header` 併入 `context`。「推薦項置首標（推薦）」等規則照舊。 |
| `TodoWrite`、`TaskCreate` | `todo`（`create`／`update`／`list`）。 |
| `ToolSearch` | `direct` 工具已直接宣告，看工具清單即可；其餘在 `codemode` 腳本裡用 `await searchTools("<工具名>")` 或 `await describeNamespace("mcp__<server>")` 確認存在；`select:a,b` 逐一確認。 |
| `ListMcpResourcesTool` | system prompt 的 `mcp_servers` 段列出 `codemode`／`deferred` server；`codemode` 腳本讀 `ALL_TOOLS` 可列全部。判斷條件（如「名稱含 linear」）照舊。 |
| `SendMessage` | `intercom`（`action: "send"`，收件人用 `intercom({ action: "list" })` 查到的 session）。 |
| `run_in_background` | Pi 的 `bash` 沒有背景模式，也沒有預設逾時：前景執行並給 `timeout`（秒），值大於被等待指令自己的逾時；等待時間長到會卡住互動時，改派 `subagent` 去等。 |
| `Read`／`Write`／`Edit`／`Bash`／`Grep`／`Glob`／`Agent` | `read`／`write`／`edit`／`bash`／`grep`／`find`／`subagent`（`grep`、`find` 是 Pi 內建工具但預設未啟用，沒有時用 `bash` 跑 `rg`、`find`）。 |

## MCP 工具

Claude 的 MCP 工具名是 `mcp__<server>__<tool>`。
Pi 沒有 `mcp` gateway 工具，呼叫方式依 `~/.pi/agent/mcp.json` 的 `toolExposure` 而定：

- `direct`：工具已直接宣告，名稱 `mcp__<server>__<tool>`，照一般工具呼叫。
- `codemode`（預設）：在 `codemode` 工具的腳本裡呼叫 `await tools.mcp__<server>__<tool>({…})`，回傳 `{ content, structuredContent?, isError? }`。
- `hidden`：Pi 看不到，等同缺工具。

工具名裡的 server 段**連字號換成底線**：`linear-server` → `mcp__linear_server__save_issue`。
沒帶前綴的 Linear 工具名（`list_issues`、`get_issue`、`save_issue`、`save_comment` 等）同樣補成 `mcp__linear_server__<tool>`。
Server 名依本機設定；下表列常見 server。
Pi 找不到某個 server 時，照該 skill 對「缺工具」的處理（停下或降級），並告訴使用者缺哪個 server。
skill 要用 `codebase-memory-mcp`（`search_graph`、`trace_path`、`get_code_snippet`、`search_code` 等）而 Pi 上沒有時，改用 `bash` 跑 `rg`／`find` 加 `read` 查同一件事，回報時註明「未用程式圖譜」。

| Claude 前綴 | Pi `server` |
|---|---|
| `mcp__linear__`、`mcp__claude_ai_Linear__` | `linear-server` |
| `mcp__chrome-devtools__` | `chrome-devtools` |
| `mcp__playwright__` | `playwright` |
| `mcp__mssql__` | `mssql` |
| `mcp__claude-in-chrome__` | Claude 專屬瀏覽器擴充，Pi 沒有；改用 `chrome-devtools` 或 `playwright`。 |

## 派 agent

| Claude Code | Pi |
|---|---|
| `subagent_type`（值 `"<plugin>:<agent>"`） | `subagent` 工具。`name`＝`<agent>`；`systemPrompt`＝`${CLAUDE_PLUGIN_ROOT}/agents/<agent>.md` 去掉 frontmatter 的內文；`task`＝原派工 prompt，開頭加兩行：「`${CLAUDE_PLUGIN_ROOT}`＝<plugin 根絕對路徑>」與「先讀 <plugin 根>/references/harness-terms.md」。 |
| `subagent_type` 值 `general-purpose`、`Explore agent` | 不帶 `systemPrompt` 的 `subagent`；Explore 用途在 `task` 寫明唯讀。 |
| agent frontmatter `model:`（haiku／sonnet／opus）與派工樣板的 `model` | 所需能力等級。Pi 上依當前設定的派工模型策略選同級模型，**一律**明給 `model` 與 `thinking`（不讓 model 留空）。 |
| agent frontmatter `tools:` | 依〈工具〉表換成 Pi 工具名，逗號串接傳 `subagent` 的 `tools`（工具層白名單）；MCP 工具列 `mcp__<server>__<tool>`（server 段連字號換底線）。列 `codemode` 會開放所有非 `hidden` 的 MCP 工具（codemode 呼叫不受白名單限制），`codemode` 與 `bash` 擋不住個別 MCP 工具與改檔，這兩者的邊界寫進 `task`（例如「DB 只用 execute_readonly_sql」「只寫 out_path」）。Pi 內建 MCP 預設 `codemode` 曝露：白名單列 `mcp__<server>__<tool>` 時，子 session 只拿得到在 `mcp.json` 的 `toolExposure` 設為 `direct` 的工具（`deferred`、`codemode` 都拿不到）。agent 需要的 MCP 工具不是 `direct` 時，派工前告訴使用者缺哪幾個、要在 `mcp.json` 設 `direct`，不要悄悄從 `tools` 拿掉。 |
| 同一則回應送出多個 Agent 呼叫（平行派工） | 互動 session：同一則回應送出多個 `subagent` 呼叫；結果由 harness 主動送回，不要輪詢。自動退出的 session：同一個 `bash` 呼叫裡把多個 `pi -p ... > <輸出檔> &` 放背景、最後 `wait`，再讀各輸出檔。 |

### 同步派工（自動退出的 session 必用）

`subagent` 是非同步的：派出後結果要等下一輪才送回。
本 session 若會在結束這一輪時自動退出（被派出來的 worker、`pi -p`、以 `subagent` 跑的 `context: fork` skill），派完一結束這輪就退出，子 agent 的結果遺失。
這類 session 派 agent 一律用 `bash` 同步跑，`timeout` 給 600 以上：

```bash
pi -p --no-session --model <provider/model> --thinking <level> \
  --system-prompt "$(awk 'BEGIN{n=0} /^---$/ && n<2 {n++; next} n>=2' <plugin 根>/agents/<agent>.md)" \
  --tools <白名單> "<task>" < /dev/null
```

- `<task>` 開頭一樣加 plugin 根與 harness-terms 兩行；`--tools` 照上表 agent frontmatter `tools:` 的換法。
- `general-purpose`／Explore 省略 `--system-prompt`。
- `pi -p` 沒有介面：workspace guard 會直接擋下需要確認的寫入，需要使用者確認的步驟不要交給它。

Pi 沒有 `subagent` 工具（未在 Herdr 內執行）時，同樣用上面的 `pi -p` 同步派工。


agent 定義檔引用 plugin 內檔案一律寫 `${CLAUDE_PLUGIN_ROOT}/...`，不寫裸相對路徑：`agents/` 沒有 skill 目錄可當基準。
