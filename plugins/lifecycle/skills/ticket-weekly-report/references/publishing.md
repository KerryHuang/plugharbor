# 落地

## 預設：只留在 `.tmp/weekly-report/`

三份成品（`slides-{週會日}.html`、`report-{週會日}.md`、`tickets-{週會日}.md`）與 `dataset.json` 都在 `.tmp/weekly-report/`（應已 gitignore）。
沒給 `--out-dir` 就停在這裡，回報時直接講明路徑；不要替使用者決定放哪。

## 給了 `--out-dir`

1. 目錄不存在就停下回報，不自建（不自建第一階目錄）。
2. 三份成品複製過去，檔名不變（會議日對得起來）；`dataset.json` 不複製。
3. 複製後 `cmp` 比對與來源位元相同，確認內嵌資料與 JS 沒被改動。
4. 回報每個檔實際落地的路徑。

## 不做的事

本 skill 不 commit、不 push、不寫進票務工具。使用者要提交或發布，另行處理；
動 git 前依專案的 Git 規則（逐檔 add、確認 staged）。

## 發布前必驗

1. **數字↔清單一致性**（SKILL.md Step 6），不一致不得發布
2. **三個 agent 回報都沒有「不建議發布」**
