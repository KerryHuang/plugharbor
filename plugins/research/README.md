# research

探索與研究用的兩個 skill。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install research@plugharbor
```

## Skills

| Skill | 用途 |
|-------|------|
| `graphify` | 把任何資料夾（程式碼、文件、論文、圖片、影音）建成知識圖譜，輸出互動 HTML、GraphRAG JSON 與 `GRAPH_REPORT.md`；支援 `--update` 增量與 `query`／`path`／`explain` 查詢。需自行安裝 `graphifyy`（Python 套件）。只能手動 `/graphify` 觸發。 |
| `ai-radar` | 每週掃描大廠更新、社群實踐、plugin 排行，反查現行 agent 設定的最佳化機會，並把建議對帳進跨週的採納待辦。只能手動觸發。 |

`ai-radar` 的輸出目錄：專案 `CLAUDE.md` 宣告 `ai-radar-output: <路徑>` 就寫在專案內，否則寫到 `~/.claude/ai-radar/`（不進版控）。
`ai-radar` 的設定健檢步驟會交給 toolkit plugin 的 `config-doctor`；沒裝就略過該步。
