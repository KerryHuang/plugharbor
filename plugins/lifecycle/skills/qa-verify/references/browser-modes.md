# 瀏覽器模式

qa-verify 的三個 agent（`qa-planner`／`qa-fixture`／`qa-runner-ui`）都掛 `mcp__chrome-devtools__*` 工具，只有一種跑法。

## chrome-devtools MCP（`--isolated`）

連線走 `--isolated` 標準註冊（做法見 `browser-docs` plugin 的 browser-setup 參考檔）：每個 session 一個拋棄式 Chrome，多 session 並行不撞 profile lock。登入由各 agent 在自己的 isolatedContext 內完成。

起手檢查：`ToolSearch("select:mcp__chrome-devtools__navigate_page")` 要有結果；連不上可跑 `browser-docs` plugin 的 browser-doctor 腳本（輸出非 `OK` 就停，依它印的補）。

## 與 claude-in-chrome 的差異

agent 固定用 `chrome-devtools`（`--isolated`）；`claude-in-chrome` 只給主 session 人機互動。三個 agent 需要 `take_snapshot`／`evaluate_script`／`list_network_requests` 這類 chrome-devtools 專有的結構化讀取能力，工具參數寫法見 `browser-docs` plugin 的 browser-tooling 參考檔。
