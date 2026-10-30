# 瀏覽器模式

qa-verify 的三個 agent（`qa-planner`／`qa-fixture`／`qa-runner-ui`）都掛 `mcp__chrome-devtools__*`
工具。一種跑法。

## chrome-devtools MCP（`--isolated`）

連線走 `--isolated` 標準註冊（`${CLAUDE_PLUGIN_ROOT}/references/browser-setup.md`）：每個 session 一個拋棄式 Chrome，
多 session 並行不撞 profile lock。登入由各 agent 在自己的 isolatedContext 內完成。
起手 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py` 非 `OK` 就停。

## 與 claude-in-chrome 的差異

`references/browser-tooling.md`（plugin 既有）：agent 固定 `chrome-devtools`（`--isolated`）；
`claude-in-chrome` 只給主 session 人機互動。qa-verify 三個 agent 需要
`take_snapshot`／`evaluate_script`／`list_network_requests` 這類 chrome-devtools 專有的
結構化讀取能力，本來就固定走 chrome-devtools MCP。
