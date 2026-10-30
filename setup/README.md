# setup：plugin 帶不了的 user 層設定

`setup/install.sh`（另一個 task 提供）會把這裡的東西裝進 `~/.claude/`。

| 目錄 | 內容 | 裝到 |
|---|---|---|
| `home/` | `CLAUDE.md`、`shared/`、`rules/`（user 層工作原則與語言規則） | `~/.claude/` |
| `config/claude-settings.template.json` | settings 範本，深度合併進 `~/.claude/settings.json` | `~/.claude/settings.json` |
| `config/statusline.sh` | 狀態列 | `~/.claude/statusline.sh` |
| `herdr/` | herdr 設定、側欄 plugin、pi 擴充 | herdr／pi 各自的設定目錄 |
| `tests/` | `statusline.sh`，CI 會跑 | |

## settings 範本的 hooks

大部分 hook（guard、通知、feedback 等）已由 `plugins/toolkit/hooks/hooks.json` 註冊，範本裡不再放。
範本只保留 herdr 的 `herdr-parent-tag`（PreToolUse／PostToolUse，matcher `Bash`），
因為它依賴 herdr 環境，不屬於 toolkit。hook 檔在 `herdr/hooks/herdr-parent-tag.py`，
安裝時要複製到 `~/.claude/hooks/herdr-parent-tag.py`（範本的 command 指向這個路徑）。

## skillOverrides（未驗證）

範本把 handoff、ai-radar 關掉（它們只該手動叫用）。key 的寫法 2026-10-30 實測**沒有任何一種能讓 plugin 的 skill 消失**：

- 用 `claude -p --plugin-dir <toolkit> --plugin-dir <research> --settings '{"skillOverrides":…}' --output-format stream-json --verbose`，
  看 init 事件的 `slash_commands`。
- 對照組：`{"simplify":"off","loop":"off"}` 能讓這兩個內建 skill 消失，所以機制本身有效。
- `handoff`／`ai-radar`、`toolkit:handoff`／`research:ai-radar`、`toolkit/handoff`、`*:handoff` 都試過，
  `toolkit:handoff`、`research:ai-radar` 仍在清單。已有 `handoff: off` 的 user settings 下，`toolkit:handoff` 同樣沒被擋，
  可見裸名稱 key 只管 user 層 skill。
- 限制：測試用 `--plugin-dir`（source 為 `toolkit@inline`），不是 marketplace 安裝的 plugin，且不能裝進使用者設定，
  所以無法排除「inline plugin 不吃 skillOverrides」。

因此範本同時寫 `handoff`／`toolkit:handoff`／`ai-radar`／`research:ai-radar` 四個 key，等 marketplace 安裝後再複測、留下有效的那組。
附帶效果：裸名稱 key 會關掉 user 層舊的 `~/.claude/skills/handoff`、`ai-radar`。

## herdr

- `herdr/pi/herdr-tree.ts` 重排子智慧體所在 tab：設環境變數 `HERDR_TREE_LAYOUT=<python 腳本路徑>` 用自訂重排腳本
  （呼叫方式 `python3 <腳本> --main <pane_id>`）；沒設就用內建版型（主 session 左半、worker 在右半等高堆疊）。
- 側欄 plugin id 為 `plugharbor.sidebar`；`herdr-parent-tag.py` 依這個 id 呼叫 refresh 動作。
