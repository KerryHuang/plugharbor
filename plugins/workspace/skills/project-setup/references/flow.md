# 流程細節

腳本都在 `${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/`，輸出 JSON（用 `python3`）。`<root>` 是專案根絕對路徑。
`install-project.sh` 在 plugharbor clone 的 `setup/`（一般是 `~/plugharbor/setup/install-project.sh`）；找不到就請使用者給 clone 位置，不自己猜。

## 1. 確認 Claude Code

不在 Claude Code 內，回固定訊息「請改到 Claude Code 叫用 project-setup」後停止。

## 2. 盤點

`python3 detect.py <root>`。欄位：

| 欄位 | 用途 |
|---|---|
| `is_empty`、`has_git`、`git_toplevel` | 新目錄判斷；`has_git` 在任何 work tree 內（含既有 repo 的子目錄）都是 true，`git_toplevel` 是該 work tree 頂層路徑（不在 repo 內為 null） |
| `git_mode` | `init`（不在任何 repo 內，或本身是空的 repo 頂層；子目錄絕不是 `init`）、`shared`（git 已追蹤 `AGENTS.md`／`CLAUDE.md`／`.claude`／`.agents`）、`local`（其餘既有 repo） |
| `signals`、`suggested_plugins` | 技術線索（dotnet、vue、react、sql、avalonia、python、node）與機械建議的 plugin |
| `existing` | `agents_md`（present／none）、`claude_md`（none／at-agents／custom）、`claude_skills`、`agents_skills`、`pi_settings` |

使用者說要共用或不要共用時，以使用者說的為準，覆寫 `git_mode`。
`git_toplevel` 不是 null 且不等於 `<root>`（`<root>` 是別人 repo 的子目錄）：不 `git init`，告知使用者「在 <toplevel> 的 repo 內」後，把該 repo 當 git 脈絡繼續；`git_mode` 只看 `<root>` 底下追蹤的 AI 設定。`mirror.py --exclude` 會自動把路徑錨定到頂層（如 `/<子目錄>/.agents/skills/x`）。

## 3. 需求清單與 plugin 對照

需求 = 使用者那句話 + `signals`。拿需求比對下表；`suggested_plugins` 只是起點，不等於全裝。對不上需求的不裝。

| plugin | 對應需求 |
|---|---|
| lifecycle | 要走需求、規格、票務、實作、發版、QA 全流程 |
| backend | 後端：分層、CQRS、資料存取、API、背景作業、單元測試（有 .NET 附錄） |
| frontend | 前端：架構分層、元件、i18n、除錯（有 Vue 3 附錄） |
| database | schema、migration、ORM 同步、資料表文件 |
| desktop | 桌面 App：MVVM、建置發佈（有 Avalonia 附錄） |
| ui-ux | 設計新畫面、風格系統、版面與互動規範 |
| blog | 部落格寫作流程 |

要確認清單與現況是否一致，讀 `plugins/*/.claude-plugin/plugin.json` 的 description。user 層的 plugin（toolkit、research、browser-docs、workspace）不在這裡裝，install-project.sh 會 SKIP。

## 4. plugharbor 安裝

`<plugins>` 是上表選出的 plugin 名，空白分隔。`git_mode` 是 `init` 時先 `git init <root>`（不 commit）；`git_toplevel` 已存在時不 init（見第 2 步）。

| `git_mode` | 指令 |
|---|---|
| `local` | `install-project.sh <root> <plugins>` |
| `shared`、`init` | 1. `install-project.sh --shared <root> <plugins>`<br>2. `install-project.sh --no-claude <root> <plugins>`<br>3. `python3 mirror.py <root> --exclude .agents/plugharbor .pi/settings.json` |

為什麼 shared 要跑兩次：`--shared` 只替 Claude 裝 project scope（進 git、團隊共用），pi、Codex、agy 會被略過（packages 與 symlink 都是本機絕對路徑）；`--no-claude` 補裝這三者（local 規則）並略過 Claude，兩者互斥不能併用。
`--no-claude` 本身已把 `.pi/settings.json`、`.agents/plugharbor/`、`.agents/skills/<skill>` 寫進 `.git/info/exclude`（無錨定寫法）；第 3 步的 `mirror.py --exclude` 只是保險：已有同路徑的行（無錨定寫法也算）就不重複寫，沒有才補錨定專案根的一行。
這兩步的結果是：Claude 部分進 git，其餘三個 CLI 的部分只在本機。**換機器或 clone 後要重跑第 2 步**，寫進清單「換機器要重跑的指令」。

安裝後用 `install-project.sh --check <root> <plugins>` 驗證，應回 exit 0（3 是有差異）：`local` 跑一次；`shared`、`init` 要跑兩次，一次加 `--shared`、一次加 `--no-claude`（與第 4 步的兩個安裝指令對應）。

## 5. 網路

見 `external-search.md`。`vendor.py <skill_dir> <root> --repo <owner/name> --commit <sha> --path <repo 內路徑>` 回傳 `installed`、`pending`（附原因）、`skipped`（已存在）。

## 6. 自寫

- `AGENTS.md`：`existing.agents_md` 是 `none` 才寫。內容：建置與測試指令（實際跑過；跑不了或沒跑就標「未驗證」）、目錄結構、慣例。
- `CLAUDE.md`：`existing.claude_md` 是 `none` 才寫，內容只有一行 `@AGENTS.md`。`custom` 不碰，列「待你決定」；`at-agents` 已完成。
- 缺口 skill：需求裡 plugharbor 與網路都沒涵蓋的工作，才在 `.claude/skills/<名稱>/SKILL.md` 寫，名稱 kebab-case、同名已存在就略過。

## 7. 鏡像與 exclude

`python3 mirror.py <root>`：`.claude/skills/*` 鏡像到 `.agents/skills/*`（相對 symlink，建不了就複製；不覆寫既有同名，列入 `skipped`）。
`git_mode` 是 `local`：`python3 mirror.py <root> --exclude <新增的檔案與目錄…>`，把這次新增的 `AGENTS.md`、`CLAUDE.md`、`.claude/skills/<名稱>`、`.agents/skills/<名稱>`、`.claude/settings.local.json`（`claude plugin install --scope local` 會寫它；Claude Code 是否自動 ignore 未驗證，所以照加）等加進 `.git/info/exclude`（錨定 repo 頂層、冪等；`./x`、結尾 `/` 會正規化，與既有 `x/` 視為同一行），讓 `git status` 乾淨。
`init`、`shared`：不 exclude，什麼時候 commit 由使用者決定。

## 8. 驗證

- `install-project.sh --check`（與安裝時相同旗標）。
- 各 CLI 載入情形：

| CLI | 專案 skill 的位置 | 驗證 |
|---|---|---|
| Claude Code | `.claude/skills/`、project／local scope 的 plugin | `claude plugin list` |
| Codex、agy | `.agents/skills/` | 列 `.agents/skills/` 並確認 symlink 解得開 |
| pi | `.agents/skills/` 與 `.pi/skills/` 都讀，也跟隨 symlink（實測 pi 非互動模式，見 `docs/agent-parity.md`）；專案要先信任（互動時會問，非互動加 `--approve`），沒信任就不載入專案 skill | 在專案目錄跑 `pi --approve -p` 問可用 skill 名稱；沒跑過標未驗證 |

沒實際驗到的標「未驗證」，不推測。

## 移除方式（寫進清單用）

| 種類 | 移除 |
|---|---|
| Claude plugin | `claude plugin uninstall <名>@plugharbor --scope local`（shared 用 `project`） |
| pi | 從 `.pi/settings.json` 的 `packages` 刪該 plugin 路徑 |
| Codex、agy | 刪 `.agents/skills/<skill>` 與 `.agents/plugharbor/<plugin>`（symlink） |
| 外部 skill | 刪 `.claude/skills/<名>` 與對應的 `.agents/skills/<名>` |
| 自寫 skill、`AGENTS.md`、`CLAUDE.md` | 刪檔；`.agents/skills/<名>` 鏡像一併刪 |
| exclude 行 | 刪 `.git/info/exclude` 對應行 |
