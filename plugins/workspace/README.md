# workspace

git 與工作區工具，加上不依賴規格書的輕量開發核心。裝在 user 層，每個專案都用得到；需要「規格→實作→發版」完整流程的專案另裝流程類 plugin。

## 定位

`[tooling]` 與技術棧、專案流程無關的「怎麼做事」。

## 安裝

由 `setup/install.sh` 裝進 user 層（Claude Code、Codex、agy、pi）。單獨安裝：

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install workspace@plugharbor
```

## 前置需求

| 需要 | 用在哪 | 沒有時 |
|---|---|---|
| git | 所有 git skill | 無法使用 |
| Node.js | `dual-tool-mirror` 的鏡像與 rules 注入腳本 | 只有這個 skill 不能用 |
| `gh` 或 `glab`、`jq` | `triage-branch-cleanup` 交叉比對遠端 PR／MR | 該環節標「狀態未知」，改用本地 git 訊號 |

各 skill 驗證時一律跑專案自帶的 script（README、CI、`package.json`、`Makefile` 找得到的那支）。

## Skills（14）

### git 與工作區
| Skill | 用途 |
|-------|------|
| `commit` | Conventional Commits 語義化提交 |
| `worktree` | git worktree 建立／切換／移除，含結束狀態驗證 |
| `triage-branch-cleanup` | 跨 branch／worktree／PR／ticket 盤點清理 |
| `submodule-relay` | 子模組 commit→push→上層 pointer bump 接力 |
| `tmp-scratch` | 暫存分層：session scratchpad 與專案 `.tmp/<YYYYMMDD>-<slug>/` |

### context 與協作
| Skill | 用途 |
|-------|------|
| `context-hygiene` | 長對話 context 衛生 |
| `convention-first` | 慣例優先：先 grep 既有樣板，不擅自引入新模式 |
| `agent-orchestration` | 派工判準與多階段 agent chain 交棒 |
| `dual-tool-mirror` | Claude Code ↔ Codex 設定鏡像 |
| `unattended` | 無人值守：使用者不在時連續推進工作單元，回來時交報告；「自動駕駛」照 `docs/roadmap.md` 段序推進到喊暫停；專案細節放 `.plugharbor/unattended.md` |
| `project-setup` | 專案補裝（只限 Claude Code）：依需求與目錄現況裝 plugharbor 專案層 plugin、外部純 skill、自寫 AGENTS.md 與缺口 skill，四個 CLI 共用 |

### 輕量開發核心
| Skill | 用途 |
|-------|------|
| `debugging` | 專案指令除錯、規格轉測試案例、無測試舊碼的安全重構（方法交給 superpowers） |
| `review` | 程式碼審查（分層、測試、安全、效能），含發現驗證 |
| `quality-check` | 建置、測試、覆蓋率、問題排序 |
| `cross-platform` | 跨平台路徑、換行、大小寫、shell 差異 |

## 幾個 skill 什麼時候用

**`submodule-relay`**：在 git submodule 容器 repo 工作時用。上層 repo 只記每個子模組的 commit pointer，順序固定是「子模組 commit → 子模組 push 成功 → 上層 bump pointer」。順序反了，上層就會記到一個遠端不存在的 commit，別人 clone 下來直接壞。這個 skill 教你判讀 `git status` 上子模組 `M` 的方向：index 落後才 bump，index 超前代表該 pull，分叉先查是誰的。也提醒 pull／rebase 之後要驗 pointer 有沒有倒退。子模組清單一律從 `.gitmodules` 讀，不寫死。

**`tmp-scratch`**：要產生一次性腳本、中間產物或給人看的暫存時用。只給自己看的放 session scratchpad；要給人看、跨 session 共用的放專案 `.tmp/<YYYYMMDD>-<slug>/`。`.tmp/` 下不准有裸檔，資料夾名只用 ASCII，任務結束當輪清掉。被派出去的 worker 不自己刪暫存，把路徑列在結果裡交給派工方統一清。

**`dual-tool-mirror`**：同一個專案要同時給 Claude Code 和 Codex 用時用。`.claude/` 是唯一的來源，Codex 讀到的 `.agents/skills/`、`.codex/agents/` 都是腳本產生的副本，不手改。rules 不落檔，改在 Codex SessionStart 時注入。安裝時把兩支腳本複製進專案並掛 SessionStart hook，步驟和驗收方式見 skill 本文。

## License

MIT
