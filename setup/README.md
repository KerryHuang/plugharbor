# setup：plugin 帶不了的 user 層設定

`setup/install.sh [--check] [--force] [--yes]` 會把這裡的東西裝進 `~/.claude/`，並替有裝的 CLI（claude、codex、agy、pi、herdr）註冊 user 層 plugin；`setup/uninstall.sh` 只移除它放進去的東西。

`--check`（install.sh 與 install-project.sh 都有）只報不改，exit code：0 一致、3 有差異、1 有步驟失敗、2 用法錯誤。

`install.sh --check-projects` 找出這台機器上落後的專案：從 `claude plugin list --json` 裡帶 `projectPath` 的 plugharbor 項目推算裝過專案層 plugin 的專案，逐一跑 `install-project.sh --check`，落後的印出修正指令，目錄已不存在的報 `STALE:`。清單不另存，每台機器讀自己的狀態；exit code 同 `--check`。更新後，開著的舊 session 要 `/reload-plugins`（pi 用 `/reload`）才會載入新版。

## plugin 分層

- **user 層**（`lib.sh` 的 `PH_USER_PLUGINS`：toolkit、research、browser-docs、workspace）：install.sh 裝進四個 CLI。`PLUGHARBOR_PLUGINS` 可覆寫要裝哪些。
- **專案層**（其餘 7 個）：install.sh 發現它們裝在 user 層會自動移除（`PLUGHARBOR_PLUGINS` 明確指定的除外；`--check` 只報 `STALE:`），改用：

  ```bash
  setup/install-project.sh [--shared] [--check] <專案根> <plugin…>
  ```

  | CLI | 預設（只自己用） | `--shared`（進 git，團隊共用） |
  |---|---|---|
  | Claude Code | `plugin install --scope local` | 專案 scope 登記 marketplace 後 `plugin install --scope project` |
  | pi | 寫 `<專案>/.pi/settings.json` 的 packages，並加進 `.git/info/exclude` | 略過 |
  | Codex、agy | 在 `<專案>/.agents/skills/` 建 symlink（見下），並加進 `.git/info/exclude` | 略過 |

  Codex 與 agy 都讀 `<專案>/.agents/skills/<skill>/SKILL.md` 並跟隨 symlink，兩者共用一份：
  `.agents/plugharbor/<plugin>` 指向 clone 的 `plugins/<plugin>`，`.agents/skills/<skill>` 指向 `../plugharbor/<plugin>/skills/<skill>`。
  skill 的 plugin 根以 SKILL.md 的 realpath 往上兩層為準，所以 references 讀得到。
  已存在、不是 plugharbor 的同名項目（例如 `dual-tool-mirror` 鏡像出來的 skill）一律 `SKIP:` 不動；指向 plugharbor 但失效的 link，`--check` 報 `BROKEN:`、實跑移除。
  建不了 symlink（Windows 沒開開發人員模式）時改複製 skill，同目錄寫 `.plugharbor-root` 記 plugin 根，印 WARN；plugharbor 更新後要重跑。

  pi 的 packages 是本機絕對路徑，所以 `--shared` 不寫；該檔已進版控時也不寫，只印 WARN。第一次在 pi 開該專案要信任專案。

  裝 `lifecycle` 時（Claude Code 有裝才做），lifecycle 取代 Superpowers，所以在 `<專案>/.claude/settings.local.json` 的 `enabledPlugins` 把
  `superpowers@claude-plugins-official`，以及 `claude plugin list` 看到的其他 marketplace 的 `superpowers@…` 設成 `false`，其他鍵不動。
  不論 `--shared` 與否都寫 `settings.local.json`（不進版控，並加進 `.git/info/exclude`）；`--check` 只印 `DISABLE: superpowers@…`（已是 false 不報）。
  沒有專案層移除入口，想在該專案恢復 Superpowers，就手動刪掉 `enabledPlugins` 裡這幾個 `superpowers@…` 鍵。
- 專案層移除：在專案根 `claude plugin uninstall <p>@plugharbor --scope local`（或 `project`），pi 從 `.pi/settings.json` 刪掉對應項，Codex／agy 刪掉 `.agents/skills/` 下對應的 link 與 `.agents/plugharbor/<p>`。
- **改名對照**：plugin 改名時在 `lib.sh` 的 `PH_RENAMES_DEFAULT` 加 `舊名:新名`（空白分隔）。目前開放：`backend-dotnet→backend`、`frontend-vue→frontend`、`database-sqlserver→database`、`desktop-avalonia→desktop`、`kid-ui→ui-ux`、
  `sa-flow→lifecycle`、`delivery-flow→lifecycle`、`dev-flow→workspace`。
  install.sh 把 user 層的舊名從四個 CLI 卸掉、新名照常安裝（已是最新就不重裝）；install-project.sh 對本專案裝著的舊名先卸再裝新名，命令列給舊名會自動換新名。
  多個舊名對同一新名時各卸一次、新名只裝一次（例如專案同時裝著 sa-flow 與 delivery-flow，只裝一次 lifecycle）。
  dev-flow 原本在 user 層，通用部分已併進 user 層的 workspace，由 install.sh 處理；sa-flow、delivery-flow 是專案層，要在各專案跑 install-project.sh。
  `--check` 以 `RENAME: <cli> <舊> → <新>` 列出待處理的舊名。

## Claude Code 的 marketplace 來源

Claude Code 的 `plugharbor` marketplace 指向 GitHub（`PLUGHARBOR_REPO`，預設 `https://github.com/KerryHuang/plugharbor.git`），是快取副本：push 並 bump 版號後，`install.sh` 或 `claude plugin marketplace update plugharbor` 才拿得到新版。
舊的本機目錄來源（就地載入、版號不起作用）會被 install.sh 移除後改成 GitHub 來源。改 plugin 時，push 前用 `claude --plugin-dir plugins/<name>` 測。Codex 仍從 clone 快照安裝，pi、agy 讀 clone。

| 目錄 | 內容 | 裝到 |
|---|---|---|
| `home/` | `CLAUDE.md`、`shared/`、`rules/`（user 層工作原則與語言規則） | `~/.claude/` |
| `config/claude-settings.template.json` | settings 範本，深度合併進 `~/.claude/settings.json` | `~/.claude/settings.json` |
| `config/statusline.sh` | 狀態列 | `~/.claude/statusline.sh` |
| `herdr/` | herdr 設定、側欄 plugin、pi 擴充 | herdr／pi 各自的設定目錄 |
| `tests/` | `statusline.sh`，CI 會跑 | |

## install.sh 的升級與舊 hook

- 版號不同才重裝；claude 重裝前先 `plugin marketplace update plugharbor`，失敗只印 WARN。codex 的 marketplace 是本機 clone 目錄，`plugin add` 直接讀，不需要（也無法）`marketplace upgrade`。
- pi 的路徑交給 python 前，Git Bash 上（有 `cygpath`）先轉成 `C:/...`，Windows 原生 python 才認得。
  這段只用 stub 測過，真 CLI 的升級行為在切換（cutover）步驟實機驗證。
- 舊 claude-home 的 guard 等 hook 只在 claude 的 toolkit plugin 這次裝好（或已是最新）後才備份移除；沒裝 claude、沒選 toolkit 或安裝失敗，只印 `STALE:`。

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

- `herdr/pi/herdr-tree.ts` 重排子智慧體所在 tab：跑 toolkit 的 `herdr_layout.py`（路徑由同目錄 `layout-path.ts` 從 repo 往上找；
  `HERDR_TREE_LAYOUT=<python 腳本路徑>` 可覆寫，呼叫方式 `python3 <腳本> --main <pane_id>`）。找不到腳本只印警告、不重排，沒有內建版型。
  重排由子智慧體在自己的新 pane 裡執行，pi-herdr-agents 不把父 pi 的環境變數帶過去：覆寫要放在 herdr 新 pane 的 shell 環境（如 shell rc 的 `export`），
  `HERDR_TREE_LAYOUT=… pi` 無效；警告寫到子智慧體的 stderr，會被 pi 的 TUI 蓋掉。
- 側欄 plugin id 為 `plugharbor.sidebar`；`herdr-parent-tag.py` 依這個 id 呼叫 refresh 動作。
