# 進度 ledger 與任務清單

實作狀態一律落檔，不靠對話記憶：context 被壓縮、session 換手、使用者隔天回來，都從檔案接續。

## 目錄

```
.tmp/implement/<feature>/      # 不進 git；<feature> 只用 ASCII kebab-case
├── ledger.md                  # 進度總帳：主 session 唯一要讀的狀態檔
├── tasks.md                   # 任務清單（規劃 subagent 產出，完成項打勾）
├── briefs/<task-id>.md        # 每個 task 的派工 brief
└── reports/<task-id>.md       # 每個 task 的完整報告；另有 spec-trace.md、review-<輪>.md
```

收尾完成（ledger 關卡表全過）後，經使用者同意再刪整個目錄；可重用的經驗已在 `<spec.dir>/LEARNINGS.md`。

## ledger.md

```markdown
# <功能名> ledger
規格：<spec.dir>/<檔名>（scale: lean｜full）
分支：feature/<name>　基底：<develop｜main>　基線：<綠／紅＋指令>

## 目標
<一段話；無規格時這段就是依據，並標「無規格」>

## 已定決策與注意
- <決策>（來源：使用者／ADR／LEARNINGS yyyy-mm-dd）

## 步驟
| 步驟 | 狀態 | 證據 |
|---|---|---|
| 2 規格閘門 | 通過 | lean 檢查表：spec-check 回報的結論行（不落檔）；verify 模式：lean 單檔 `<spec.dir>/<feature>_規格驗證報告.md`、full `{功能目錄}/{功能名稱}_規格驗證報告[_cross].md` |
| 5 task 派工 | 7/9 | 見 tasks.md |

## 驗收（分開記）
build：　測試：　lint：　規格比對：　審查：

## 收尾關卡
（見 closing.md 的關卡表，逐關記 通過／未過＋時間＋證據）

## 失敗與已排除
- <task-id>：<失敗摘要>；已試：<做法>；排除的假設：<…>
```

狀態只寫「未開始／進行中／通過／未過／跳過（理由）」。每完成一個 task 或一個步驟就更新，不累積。

## tasks.md

```markdown
- [ ] T001 [P] <目標>（規格：§3.2 BL-04）
  - 讀：<檔>　改：<檔>
  - 驗收：`<指令>` 預期 <結果>
  - 依賴：無
```

## brief（briefs/<task-id>.md）

brief 必須自足，subagent 不需要讀對話就做得下去：

- 目標與完成判準（驗收指令＋預期結果）
- 規格段落路徑（只給相關段，不給整份）
- 要讀、要改的檔；不准碰的檔
- 已定決策（從 ledger 抄，不要讓 subagent 重問）
- 試過且排除的做法（重派修正時必附上一份報告路徑與失敗輸出）
- 報告寫到哪：`reports/<task-id>.md`；回覆只回「狀態＋報告路徑」一行

## 報告（reports/<task-id>.md）

第一行固定 `狀態：DONE｜DONE_WITH_CONCERNS｜BLOCKED`，接著：改了哪些檔、跑了哪些指令與結果、偏離 brief 的地方與理由、疑慮。主 session 只讀第一行與疑慮段，需要時才讀其餘。

## 續做

1. 讀 `ledger.md`，找第一個狀態不是「通過／跳過」的步驟。
2. 在 task 派工階段：`tasks.md` 沒打勾、且 `reports/` 沒有 DONE 報告的 task 才重派；有 DONE 報告但沒打勾的，先跑它的驗收指令再決定。
3. 在收尾階段：照 closing.md 從第一個沒過的關卡接續，且先重驗該關的前提（HEAD 有沒有變）。
