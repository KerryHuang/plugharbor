# 瀏覽器 MCP 標準註冊（每台機器）

sa-flow 的 5 支瀏覽器 agent 全部走 `chrome-devtools` MCP，註冊一律 **`--isolated`**：
每個 session 開自己的拋棄式 Chrome（暫存 profile、獨立 cookie jar、獨立視窗），
session 結束自動消失。跨 session 的 profile lock／登入互踢／分頁互見／resize 互擾
在結構上不存在，不需要任何 daemon 或協調。理由見 `browser-tooling.md`。

## Claude Code — `~/.claude.json` → `mcpServers.chrome-devtools`

macOS／Linux：
```json
{"command": "npx", "args": ["-y", "chrome-devtools-mcp@latest", "--isolated", "--viewport", "1680x1000"]}
```

Windows：
```json
{"command": "cmd", "args": ["/c", "npx", "-y", "chrome-devtools-mcp@latest", "--isolated", "--viewport", "1680x1000"]}
```

## Codex — `~/.codex/config.toml`

```bash
codex mcp remove chrome-devtools
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --isolated --viewport 1680x1000
```

Windows Git Bash 前面加 `MSYS_NO_PATHCONV=1`（否則 `/c` 會被轉成 `C:/`），且 command 用 `cmd /c npx …`。
Codex `exec` 非互動模式：`-s workspace-write`（approval on-request）下 MCP 呼叫不需 approval；`-s read-only` 會被 approval policy `never` 擋。

## 改完之後

- **重啟 session**——MCP 設定在啟動時讀取。
- 跑 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py --host both` 看到 `OK`。
- 每個 session 的 Chrome 是全新的：**agent 要自己登入**（憑證來源見各 skill 的派工契約）。

## 四件不要做的事

- 不要用 `--browserUrl`／`--autoConnect` 附掛共用 Chrome——那是把 cookie jar 與分頁也共用起來，正是要根除的形狀。
- 不要依賴 `--viewport`：它只對第一個分頁做一次 OS 視窗 resize，`isolatedContext` 開的新視窗吃不到、headed 模式還會被螢幕高度夾住。尺寸由 agent 對自己的頁 `emulate(viewport: "1680x1000x2")`。
- 不要在 agent 用 `claude-in-chrome`——它需要 Claude Code `/login` 訂閱帳號，Codex 沒有這條路。主 session 人機互動時可當捷徑。
- 不要用包裝腳本（如 `~/.claude/bin/chrome-devtools-mcp.sh`）代替直接註冊——doctor 看的是 args 裡有沒有 `chrome-devtools-mcp` 與 `--isolated`，包裝腳本會被判「未註冊」。
