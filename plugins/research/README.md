# research

探索與研究用的三個 skill。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install research@plugharbor
```

## Skills

| Skill | 用途 |
|-------|------|
| `graphify` | 把任何資料夾（程式碼、文件、論文、圖片、影音）建成知識圖譜，輸出互動 HTML、GraphRAG JSON 與 `GRAPH_REPORT.md`；支援 `--update` 增量與 `query`／`path`／`explain` 查詢。需自行安裝 `graphifyy`（Python 套件）。只能手動 `/graphify` 觸發。 |
| `ai-radar` | 每週掃描大廠更新、社群實踐，反查現行 agent 設定的最佳化機會，並把建議對帳進跨週的採納待辦；週報的 plugin 排行與深讀交給 `plugin-harvest --lean`。只能手動觸發。 |
| `plugin-harvest` | 給一個領域就搜尋最多人用的 plugin，深讀對照自家 plugin（裝用／借鑒／不理），把值得借的寫成「改哪個 skill 哪一段」的提案，逐條核准後才改檔；採納時寫 `harvest-lock.json`（來源、commit、授權），`--check-lock` 檢查上游更新與授權變動。只能手動觸發。 |

`ai-radar` 的輸出目錄：專案 `CLAUDE.md` 宣告 `ai-radar-output: <路徑>` 就寫在專案內，否則寫到 `~/.claude/ai-radar/`（不進版控）。
`plugin-harvest` 用同一個輸出目錄：評估卡在 `plugin-eval/`、提案在 `plugin-harvest/`。
單獨評估一個 repo：`/research:plugin-harvest https://github.com/<owner>/<repo>`（舊的 `/research:ai-radar --plugin <網址>` 仍可用，會轉交）。
`ai-radar` 的設定健檢步驟會交給 toolkit plugin 的 `config-doctor`；沒裝就略過該步。
