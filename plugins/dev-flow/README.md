# dev-flow

規格→實作→發版的開發流程 plugin，與技術棧無關。

## 定位

`[tooling / sdlc]` 與技術棧無關的「怎麼做事」，不綁任何專案業務。

## 安裝

```bash
# 1. 註冊 marketplace（一次性）
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git

# 2. 安裝外掛
claude plugin install dev-flow@plugharbor
```

## 前置需求

| 需要 | 用在哪 | 沒有時 |
|---|---|---|
| git | 所有 Git 生命週期 skill | 無法使用 |

各 skill 驗證時一律跑**專案自帶**的 script（README、CI 設定、`package.json`、`Makefile` 裡找得到的那支），不另外要求安裝工具。

## Skills（5）

| Skill | 用途 |
|-------|------|
| `work-on` | 端到端 規劃-實作-測試-提交編排 |
| `feature` | 新功能分支 + 領域邊界規劃鷹架 |
| `spec` | 功能規格文件建立/狀態追蹤 |
| `implement` | 從規格自動執行完整實作流程（標準/TDD 模式） |
| `release` | release/hotfix 分支與合併回 develop，多 remote tag 污染防範 |

git 與工作區工具（commit、worktree、分支清理、submodule、暫存檔、context 治理）與輕量開發核心（debugging、review、quality-check）在 [workspace](../workspace/README.md)。dev-flow 叫用它們都是可選，沒裝時 skill 內寫有退路。

## License

MIT
