# Harness 用語對照（Claude Code ↔ Pi）

本 plugin 的 skill、agent、reference 以 Claude Code 用語撰寫。
在 Claude Code 照字面執行，本檔不必讀。
在 Pi（或其他非 Claude Code 的 harness）執行時，先讀本檔，把下表左欄換成右欄再照做；步驟、規則、收尾條件不變。
`scripts/test_harness_neutral.py` 會擋下「出現在 skill／agent／reference 裡、本檔卻沒有對照」的 Claude 專屬用語。

## 路徑與參數

| Claude Code | Pi |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | plugin 根目錄＝SKILL.md 所在目錄往上兩層（`skills/<skill>/SKILL.md` → plugin 根）。Pi 不代換這個變數：寫進工具呼叫或 shell 指令前，先換成絕對路徑；shell 裡的 `${CLAUDE_PLUGIN_ROOT}` 在 Pi 是空字串。 |
| `${CLAUDE_SKILL_DIR}` | 本 SKILL.md 所在目錄的絕對路徑。Pi 不代換：寫進工具呼叫或 shell 指令前先換成絕對路徑。 |
| `$ARGUMENTS` | `/skill:<name>` 後面的文字（Pi 把它附在 skill 內容後當使用者請求），沒有就用觸發本 skill 的那則使用者訊息。 |
| `${CLAUDE_CODE_SESSION_ID}` | Pi 沒有對應值。依賴它的量測在 Pi 上略過，回報時註明「Pi 未量測」。 |
| `sa-flow:<skill>`、`/sa-flow:<skill>` | Pi skill 名稱不帶 plugin 前綴：`<skill>`，手動觸發用 `/skill:<skill>`。 |
| `/reload-plugins` | Pi 以本機 checkout 載入，改版後用 `/reload`。 |
| `.claude/rules/`、`CLAUDE.md` | 這些是 workspace 檔案，Pi 上照路徑直接讀。 |

## Skill frontmatter

下列 Claude 專屬欄位在 Pi 上不報錯也不生效：

| 欄位 | Pi 上的處理 |
|---|---|
| `argument-hint:` | 只是提示，參數照 `$ARGUMENTS` 列取得。 |
| `model:` | Pi 用當前 session 的模型跑 skill，不切換。 |
| `context:`（值 `context: fork`） | Claude 會在無對話歷史的子 context 跑本 skill。Pi 上要保留這份隔離時，用 `subagent` 派一個子 session 跑：`skills` 帶本 skill 名，`task` 帶參數與 plugin 根絕對路徑。 |

## 工具

| Claude Code | Pi |
|---|---|
| `AskUserQuestion` | `ask_user`。一次呼叫只問一題：多題批次改成同一回合依序多次呼叫；`options` 的 label／description 對應 `title`／`description`；`multiSelect: true` 對應 `allowMultiple: true`；`header` 併入 `context`。「推薦項置首標（推薦）」等規則照舊。 |
| `TodoWrite`、`TaskCreate` | `todo`（`create`／`update`／`list`）。 |
| `ToolSearch` | 用 `mcp({ search: "<工具名>" })` 或 `mcp({ server: "<server>" })` 確認工具存在；`select:a,b` 逐一確認。 |
| `ListMcpResourcesTool` | `mcp({})` 列出 server 狀態；判斷條件（如「名稱含 linear」）照舊。 |
| `SendMessage` | `intercom`（`action: "send"`，收件人用 `intercom({ action: "list" })` 查到的 session）。 |
| `run_in_background` | Pi 的 `bash` 沒有背景模式，也沒有預設逾時：前景執行並給 `timeout`（秒），值大於被等待指令自己的逾時；等待時間長到會卡住互動時，改派 `subagent` 去等。 |
| `WebFetch`、`WebSearch` | Pi 沒有內建網頁工具：有對應 MCP server 就經 `mcp` gateway 呼叫，沒有就用 `bash` 跑 `curl`，或請使用者貼上內容。 |
| `Read`／`Write`／`Edit`／`Bash`／`Grep`／`Glob`／`Agent` | `read`／`write`／`edit`／`bash`／`grep`／`find`／`subagent`（`grep`、`find` 是 Pi 內建工具但預設未啟用，沒有時用 `bash` 跑 `rg`、`find`）。 |

## MCP 工具

Claude 的 MCP 工具名是 `mcp__<server>__<tool>`。
Pi 經 `mcp` gateway 呼叫：`mcp({ server: "<server>", tool: "<tool>", args: {…} })`。
沒帶前綴的 Linear 工具名（`list_issues`、`get_issue`、`save_issue`、`save_comment` 等）同樣走 gateway。
Server 名依本機設定；下表是本 plugin 用到的 server。
Pi 找不到某個 server 時，照該 skill 對「缺工具」的處理（停下或降級），並告訴使用者缺哪個 server。

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
| `subagent_type`（值 `"sa-flow:<agent>"`） | `subagent` 工具。`name`＝`<agent>`；`systemPrompt`＝`${CLAUDE_PLUGIN_ROOT}/agents/<agent>.md` 去掉 frontmatter 的內文；`task`＝原派工 prompt，開頭加兩行：「`${CLAUDE_PLUGIN_ROOT}`＝<plugin 根絕對路徑>」與「先讀 <plugin 根>/references/harness-terms.md」。 |
| `subagent_type` 值 `general-purpose`、`Explore agent` | 不帶 `systemPrompt` 的 `subagent`；Explore 用途在 `task` 寫明唯讀。 |
| agent frontmatter `model:`（haiku／sonnet／opus）與派工樣板的 `model` | 所需能力等級。Pi 上依當前設定的派工模型策略選同級模型，**一律**明給 `model` 與 `thinking`，不讓 model 留空。 |
| agent frontmatter `tools:` | 依〈工具〉表換成 Pi 工具名，逗號串接傳 `subagent` 的 `tools`（工具層白名單）；MCP 工具有同名 `mcp__<server>__<tool>` 就照列，只有 gateway 就列 `mcp`。`mcp` 與 `bash` 擋不住個別 MCP 工具與改檔，這兩者的邊界寫進 `task`（例如「DB 只用唯讀查詢」「只寫 out_path」）。 |
| 同一則回應送出多個 Agent 呼叫（平行派工） | 同一則回應送出多個 `subagent` 呼叫；結果由 harness 主動送回，不要輪詢。 |

Pi 沒有 `subagent` 工具時無法派工：需要派 agent 的 skill 一開始就告訴使用者改在支援 `subagent` 的 Pi 環境或 Claude Code 執行。
agent 定義檔引用 plugin 內檔案一律寫 `${CLAUDE_PLUGIN_ROOT}/...`，不寫裸相對路徑：`agents/` 沒有 skill 目錄可當基準。
