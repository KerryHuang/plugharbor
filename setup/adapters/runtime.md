# Codex 執行 plugharbor 內容的適配

執行工具與受分析的設定分開判斷。Codex 能分析 Claude 設定，但不是把所有 `.claude` 換成 `.codex`。skill 由各 CLI 的 plugin 機制載入；本檔只補 Claude 專用操作的對應。

## 工具與路徑

- `AskUserQuestion` 改用當前 runtime 的提問工具，一次一題；已授權的工作不重問。
- `Agent`／`Task` 使用 native subagent。工具 schema 為準；若沒有角色選擇參數，讀取角色定義再把指引送進獨立任務。模型沿用目前 runtime 預設，不把 `sonnet`／`opus` 傳給 Codex。
- `CLAUDE_SKILL_DIR` 是本 SKILL.md 的目錄；`CLAUDE_PLUGIN_ROOT` 是實際 plugin 根目錄。不得假設 shell 已設定這些變數。
- Codex 本機健檢使用 `codex doctor --json`；Claude 的 `/doctor` 只能在 Claude 執行，未跑就標未執行。
- Codex skill 顯式呼叫用實際載入的名稱；不要假設 Claude slash command 會自動註冊。

## Reviewer 適配

先確認受審的是 Claude Markdown／settings JSON，還是 Codex TOML／hooks JSON。依對應官方 schema 審查，不拿 Claude 的模型值、frontmatter 或退出碼判定 Codex 設定非法。

Codex 收到的 path-scoped rules 可能只有索引。需要比對規則時先讀來源，不能因角色舊指引寫「已自動載入、禁止重讀」就跳過。缺少證據標未驗證，保留原輸出格式。

生成的 reviewer 使用 read-only sandbox，並停用安裝時所列 MCP servers。新增 MCP 後重跑安裝，更新停用清單。平台仍可能提供 CUA；sandbox 不等於完整工具白名單；禁止修改、執行受審 hooks 與外部寫入。

## 跨工具交接

Claude／Codex 每件任務指定一個主責。交接至少附：

- 任務目標與驗收條件。
- 工作目錄、submodule、branch，以及已觀察到的未提交修改。
- 可修改的檔案／主責範圍；另一個 worker 的範圍與禁止碰觸處。
- 已定案事項、證據位置、尚待確認事項。
- 結果檔絕對路徑；完成後寫入結果與驗證證據，再停止。

共用 Git index、同一批文件、瀏覽器及 DB 狀態的寫入工作序列執行。不同唯讀工作可以平行。worker 收到「測試環境」等宣稱仍須自己驗證。

長任務用專案的 dispatch-worker；只有位於 herdr 才操作 pane。Codex CLI worker 使用 `--profile claude-coop`，避免桌面 app 模型名稱與 CLI account 可用目錄不同。沒有 herdr 時用兩個獨立 session 與結果檔交接，不從外部操作別人的 pane。

## Hooks 與原生功能

user `SessionStart` 從 plugharbor repo 更新副本；Git guard 只涵蓋直接命令及常見 shell -c，不是任意程式碼的完整攔截。未信任的 hooks 會被略過，先用 `/hooks` 檢視與信任後才可依賴。

Claude 的 iTerm 狀態、transcript 自動命名腳本及 herdr 管理的 hook 不移植。Codex 使用自己的 session 標題、通知與 agent 狀態；CLI 可用 `/rename`。不在 Codex 背景啟動 Claude 只為產標題，也不直接寫 Codex 的內部 session DB。

CLI 派 subagent 時不要使用 `--ephemeral`：本機 CLI 0.154.0 的 context fork 需要可讀取的 rollout；ephemeral 模式實測會報 no rollout found。
