# plugharbor

公開的 Claude Code plugin marketplace，也是所有 AI 工作模式的唯一來源，供 Claude Code、Codex、pi、agy 共用。
內容：`plugins/`（11 個 plugin）、`setup/`（user 層設定、install／bootstrap／uninstall、adapters）、`scripts/ci/validate.py`、`.github/workflows/validate.yml`。
各 CLI 差異見 `docs/agent-parity.md`，安裝與 user 層設定見 `setup/README.md`。

## 慣例

- 繁體中文，技術名詞保留英文；文件簡潔。
- plugin 結構：`plugins/<name>/.claude-plugin/plugin.json`、`skills/<skill>/SKILL.md`、`agents/<agent>.md`（kebab-case）；共用素材放 `references/`、`templates/`，以 `${CLAUDE_PLUGIN_ROOT}/` 引用。plugin 不支援 `rules/`。
- SKILL.md 300 行以內，實作邏輯放 `references/` 或 `scripts/`。
- 要讓 pi 載入的 plugin 需有 `package.json`（`pi.skills`）。
- 細則見 `.claude/rules/`（plugin-structure、skill-conventions、version-consistency）。

## 版號同步

改 `skills/`、`agents/`、`references/`、`templates/` 時，同一個 commit 內：

1. 該 plugin 的 `CHANGELOG.md` 最上方新增 `## [x.y.z] - yyyy-mm-dd`
2. bump `plugin.json`、`.claude-plugin/marketplace.json`、根 `README.md` 版本欄（`release-plugin` skill 會同步三處）

級距：fix → patch；feat → minor；BREAKING → major；docs／chore／refactor → patch。
新增、改名、刪除 skill 或 agent 時，同步根 `README.md` 的「skills 與 agents」表與該 plugin 的 README。

## 驗證

commit 前執行 `python3 scripts/ci/validate.py`（版號一致、frontmatter、交互引用、README 清單、外洩樣式）。
CI（`.github/workflows/validate.yml`）另跑 plugin 腳本測試、`node --test`、toolkit hook 測試（pytest 與 shell）、`setup/tests/*.sh`。
本機啟用 pre-commit：`git config core.hooksPath scripts/hooks`。

## 外洩規則

本 repo 是公開的：不得出現個人絕對路徑、非範例 email、內網 IP、公司名稱、小孩姓名、部落格網域。

- `.leak-denylist`（gitignore、只存在本機）一行一個不得出現的字串，`regex:` 開頭為正規式；validate.py 與 pre-commit 會讀。
- 命中時改內容，**絕不**用白名單放行。
- `.private/` 與 `.superpowers/` 絕不提交（已在 `.gitignore`）。

## Git

- 一律逐檔指名 `git add <檔>`，不用 `git add -A` 或 `git add .`；commit 前用 `git status` 確認 staged 只有本次檔案。
- 不用 `--no-verify`。force push 前先取得使用者明確同意。
