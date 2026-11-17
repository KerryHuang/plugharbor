# 後段：對照驗收與回填

計畫的最後一個 task 讀本檔照做（superpowers 路徑與退路都一樣）；**免計畫**時沒有最後一個 task，實作與審查完成後由主控直接讀本檔照做，設計文件路徑由主控傳入，驗收以設計的驗收案例為準。前面的 task 都完成、測試全綠才開始。設計文件路徑看計畫的 **Spec** 欄（免計畫則看主控傳入的路徑）；`spec.dir` 跑 `python3 <plugin 根>/scripts/config.py get spec.dir`（plugin 根＝本檔所在目錄往上三層 `../../../`）。工作檔放 `.tmp/implement/<feature>/`（不進 git；`<feature>` 只用 ASCII kebab-case）。

## 1. 對照驗收

先分流：**無設計文件**（使用者明說不寫、`<spec.dir>` 找不到）→ 對照計畫 Goal 逐項找證據、略過下面的轉檔，回報標「無設計文件」。有設計文件才做：

```bash
python3 <plugin 根>/skills/qa-verify/scripts/spec_to_cases.py <設計文件> .tmp/implement/<feature>/cases.md
```

- exit 非 0（缺欄、找不到驗收一節、其他錯誤）→ 回報 stderr，本 task 不算完成，不繼續。
- 逐案對到證據（測試名或指令輸出），寫 `.tmp/implement/<feature>/acceptance-trace.md`。
- `[ui]` 案例建議收尾後跑 `lifecycle:qa-verify`。
- 有案例沒證據 → 本 task 不算完成，回報主控補做後重跑本檔。

## 2. 回填

- `docs/feature.md`（舊名 `docs/feature-checklist.md`）有才打勾並跑腳本更新數字，照 plugin 根 `references/feature-checklist.md`；沒有就略過並回報一行，不建立。
- 有 `ticket.tool` → 照同檔「同步票」叫 `tickets:ticket-ops`；沒裝 tickets → 只勾清單，回報一行。沒設 → 回報「未設 ticket.tool，略過同步票」。
- 逐檔 `git add`（不用 `-A`／`.`）、commit；`.tmp/` 不進 git。

回報：驗收對照、清單、同步票分開宣稱；沒跑到的標「未驗證」。push、PR 交給收尾，不自動 merge。
