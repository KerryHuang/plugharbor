# 後段：規格比對、整合測試、經驗與回填

計畫的最後一個 task 讀本檔照做（superpowers 路徑與極簡退路都一樣）。前面的 task 都完成、測試全綠才開始。規格路徑與 `spec.dir` 看計畫開頭；計畫沒寫就跑 `python3 <plugin 根>/scripts/config.py get spec.dir`（plugin 根＝本檔所在目錄往上三層 `../../../`）。工作檔放 `.tmp/implement/<feature>/`（不進 git；`<feature>` 只用 ASCII kebab-case）。

## 1. 規格系統性比對

對照規格逐條比對（不抽查），結果寫 `.tmp/implement/<feature>/spec-trace.md`：

- **層一 介面**：規格列的端點／畫面／指令 vs 實際存在的，逐一確認。
- **層二 規則**：規格的業務／驗證規則 ID vs 實作＋測試，逐條確認有實作也有測試。
- **層三 勾選**：比對無缺後，把規格與計畫的完成項打勾。

| 結果 | 處理 |
|------|------|
| 有介面或規則未實作 | 本 task 不算完成：列出缺項回報主控，補做後重跑本檔 |
| 有實作缺測試 | 派 `lifecycle:tester` 補（沒有 subagent 工具或該 agent 不存在就自己補） |
| 全部完成 | 進步驟 2 |

無規格時，改對照計畫寫的目標比對，回報標「無規格」。

## 2. 端到端／整合測試

- 跑專案的端到端或整合測試；涉及資料存取組態、原生 SQL、特殊型別或定序、軟刪除、分頁、查詢轉譯時一定要跑。環境不可用可標 skip 並註明原因，邏輯錯一定要修。
- 再跑一次完整的 build、全部測試、lint：用 `workspace:quality-check`（可選；沒裝就跑專案自帶的指令）。
- 失敗就修、重跑到通過；修之前三方比對（規格、程式、真實資料）。技術或資料疑慮先派 `lifecycle:debugger` 自解，真的卡住才問使用者。
- 記下每條指令與結果，build、測試、lint、整合測試各自宣稱，不拿一項代替另一項。

## 3. 寫經驗（LEARNINGS.md）

在 `<spec.dir>/LEARNINGS.md` 最上方加一段（檔案不存在就建立）：

```markdown
## yyyy-mm-dd <功能名>
- <下次規劃前該先知道的事：踩過的坑、規格常漏的地方、拆 task 的教訓、哪個指令會騙人>
- 否決：<被否決的方案>——<使用者的理由>
```

只寫下次用得上的通則，一段最多 5 條，不寫流水帳；「否決」只記這次使用者明確拒絕的方案，沒有就不寫；跟既有條目重複就改寫舊條目而不是再加。

## 4. 規格回填

規格狀態改為「已實作」、補變更紀錄；只改 `<spec.dir>` 下的文件，不動程式碼。無規格時略過。
有 `docs/feature-checklist.md` 就把本功能的項目打勾並跑腳本更新數字（格式見 plugin 根的 `references/feature-checklist.md`）。

LEARNINGS、規格回填與功能清單要進 git：照計畫其他 task 的慣例逐檔 `git add`、commit（不用 `git add -A`／`.`）；`spec-trace.md` 不進 git。

## 回報

規格比對、整合測試、LEARNINGS、規格回填四項分開宣稱；沒跑到的標「未驗證」。之後的 push、PR 交給收尾（superpowers 的 finishing 選單，或極簡退路的步驟 4），不自動 merge。
