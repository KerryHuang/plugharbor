# 收尾關卡

收尾分關卡，每關有「前提」與「通過證據」，逐關記進 ledger 的關卡表。中斷或失敗後，從**第一個沒過的關卡**接續；接續前先重驗該關前提，特別是 HEAD 有沒有變。

## 模式 A 的關卡

| # | 關卡 | 通過證據 |
|---|---|---|
| G1 | commit | `git status --short` 乾淨；記下 `HEAD` SHA |
| G2 | push | `git rev-parse HEAD` 等於 `git rev-parse @{u}` |
| G3 | draft PR／MR | PR 編號與網址記進 ledger |
| G4 | 對已 commit 的最終狀態再審 | 審查報告的 SHA 等於目前 HEAD；重大與主要問題已修 |
| G5 | 端到端／整合測試 | 指令與結果；失敗已修並重跑通過 |
| G6 | 規格回填 | 規格狀態改為已實作、補變更紀錄；比對無缺 |
| G7 | 提示解除 draft | 告知使用者，**不自動 merge** |

模式 B 同 A，每關開跑前先問使用者。模式 D 只到 G1。

## 紀律

- **完成點是 G6**：不是 commit，也不是步驟 7 的實作期審查跑完。G4 對最終狀態的獨立審查常抓到實作期漏掉的整條規則，不能省。
- G4 之後若又有修正 commit → HEAD 變了，回 G4 對新 HEAD 再審，不留「最新 commit 未審」的缺口。
- push 失敗、CI 紅燈 → 該關記「未過」並停在該關，不跳過去做下一關。
- 遇到技術、業務、資料疑慮，先派對應 agent 自解（`lifecycle:debugger`、資料探勘、領域顧問），真的卡住才升級給使用者。
- 長流程每關開始與結束都回報一行進度；單關超過 5 分鐘補一行中途進度。

## 代為 merge（只在使用者明確要求時）

merge 前把通過最後一關檢查時記下的 SHA 帶上，防止檢查後有人推新 commit：

```bash
gh pr merge <n> --merge --match-head-commit <已檢查的 SHA>   # GitHub
glab mr merge <n> --sha <已檢查的 SHA>                        # GitLab 對應參數
```

被拒（HEAD 不符）→ 有新 commit 進來：回 G4 對新 HEAD 重審，不硬 merge。
