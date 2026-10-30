# dev-flow

跨語言開發工作流 plugin — 把散在多個專案裡逐字重複的 git 生命週期與工作編排做法，收斂成一套通用能力。

## 定位

`[tooling / sdlc]` 與技術棧無關的「怎麼做事」，不綁任何專案業務。

## 安裝

```bash
# 1. 註冊 marketplace（一次性）
claude plugin marketplace add https://github.com/KerryHuang/kerryhuang-plugins.git

# 2. 安裝外掛
claude plugin install dev-flow
```

## 前置需求

| 需要 | 用在哪 | 沒有時 |
|---|---|---|
| git | 所有 Git 生命週期 skill | 無法使用 |
| Node.js | `dual-tool-mirror` 的鏡像與 rules 注入腳本 | 只有這個 skill 不能用 |
| `gh` 或 `glab`、`jq` | `triage-branch-cleanup` 交叉比對遠端 PR／MR 狀態 | 該環節標「無此來源，狀態未知」，改用本地 git 訊號判斷 |

各 skill 驗證時一律跑**專案自帶**的 script（README、CI 設定、`package.json`、`Makefile` 裡找得到的那支），不另外要求安裝工具。

## Skills（17）

### Git 生命週期
| Skill | 用途 |
|-------|------|
| `commit` | Conventional Commits 語義化提交（Git Flow + Semantic Release） |
| `worktree` | git worktree 建立/切換/移除，含 observable-end-state 驗證 |
| `release` | release/hotfix 分支與合併回 develop，多 remote tag 污染防範 |
| `triage-branch-cleanup` | 跨 branch/worktree/PR/ticket 盤點清理，四道硬 gate |
| `submodule-relay` | submodule 容器接力：子模組 commit→push→pointer bump，`M` 方向判讀、pull／rebase 後驗 pointer |

### 工作編排
| Skill | 用途 |
|-------|------|
| `work-on` | 端到端 規劃-實作-測試-提交編排 |
| `feature` | 新功能分支 + 領域邊界規劃鷹架 |
| `spec` | 功能規格文件建立/狀態追蹤 |
| `implement` | 從規格自動執行完整實作流程（標準/TDD 模式） |
| `quality-check` | 建置驗證/測試/覆蓋率/問題排序 |
| `review` | 程式碼審查（架構/分層/品質指標） |
| `debugging` | TDD 系統性除錯 |

### Context 與協作治理
| Skill | 用途 |
|-------|------|
| `context-hygiene` | 長對話 context 衛生，六動作決策樹 |
| `convention-first` | 慣例優先，grep 既有樣板禁止擅自引入新模式 |
| `agent-orchestration` | 派工判準（自己做／subagent／獨立 worker）、多階段 agent chain / output handoff / 階段清理 |
| `tmp-scratch` | 暫存分層：session scratchpad vs 專案 `.tmp/<YYYYMMDD>-<slug>/`、命名與清理 |
| `dual-tool-mirror` | Claude Code ↔ Codex 設定鏡像：`.claude/` 單一來源、鏡像與 rules 注入腳本 |

## 新增 skill 什麼時候用

**`submodule-relay`**：在 git submodule 容器 repo 工作時用。上層 repo 只記每個子模組的 commit pointer，順序固定是「子模組 commit → 子模組 push 成功 → 上層 bump pointer」。順序反了，上層就會記到一個遠端不存在的 commit，別人 clone 下來直接壞。這個 skill 教你判讀 `git status` 上子模組 `M` 的方向：index 落後才 bump，index 超前代表該 pull，分叉先查是誰的。也提醒 pull／rebase 之後要驗 pointer 有沒有倒退。子模組清單一律從 `.gitmodules` 讀，不寫死。

**`tmp-scratch`**：要產生一次性腳本、中間產物或給人看的暫存時用。只給自己看的放 session scratchpad；要給人看、跨 session 共用的放專案 `.tmp/<YYYYMMDD>-<slug>/`。`.tmp/` 下不准有裸檔，資料夾名只用 ASCII，任務結束當輪清掉。被派出去的 worker 不自己刪暫存，把路徑列在結果裡交給派工方統一清。

**`dual-tool-mirror`**：同一個專案要同時給 Claude Code 和 Codex 用時用。`.claude/` 是唯一的來源，Codex 讀到的 `.agents/skills/`、`.codex/agents/` 都是腳本產生的副本，不手改。rules 不落檔，改在 Codex SessionStart 時注入。安裝時把兩支腳本複製進專案並掛 SessionStart hook，步驟和驗收方式見 skill 本文。

## License

MIT
