# 瀏覽器連線、登入、截圖落地（live-drive）

## 連線

MCP 註冊一律 `chrome-devtools-mcp --isolated`——標準與 Codex 寫法見
`${CLAUDE_PLUGIN_ROOT}/references/browser-setup.md`；隔離模型與同 session 三條規則見
`${CLAUDE_PLUGIN_ROOT}/references/browser-tooling.md`。

起手 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py`，非 `OK` 就停：它會印標準註冊寫法，
請使用者改完重啟 session。不要自己開 Chrome、不要開 9222、不要協調 lock。

工具回 `Could not connect to Chrome` 而 doctor 是 `OK`：重試一次；仍失敗回報原始錯誤訊息。

## 登入

每個 session 的 Chrome 是全新的、每個 `isolatedContext` 是全新的 cookie jar，**一定要自己登入**。
憑證讀 workspace 的 `.claude/live-drive.local.md`（`live-drive-url／username／password`）；
登入頁（SSO／表單皆同）：`take_snapshot` 取 uid → `fill` 帳密 → `click` → 驗證回到目標 URL。
憑證不寫進任何產物。

## 截圖落地

`take_screenshot` 的 `filePath` 只准 workspace roots 內：一律先落 `<ws>/.tmp/live-drive/<session>/`，
交付 repo 可能在 workspace 外，由主 session 於 Step 3 複製。

## 收尾

agent 只關自己的分頁。主 session 若手動起過 Chrome，回報完成的同一輪關掉並驗證。
