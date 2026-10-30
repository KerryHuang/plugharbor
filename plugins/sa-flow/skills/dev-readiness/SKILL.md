---
name: dev-readiness
description: "BFS＋FFS 寫完、verifying-specs 之前用：對抗式獵出邊界缺口（空值／極值／狀態／並發／例外），逐項裁決並回寫規格，迴圈到零阻塞。觸發：「就緒度」「dev-readiness」。"
argument-hint: "[功能目錄]"
---

# Dev-Readiness — 開發者就緒度檢核閘門

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

核心問題：**「開發者現在坐下來,光看這份 BFS+FFS,有沒有得用猜的地方?」**

> `verifying-specs` 驗**已寫的**(正確性/一致性);本 skill 獵**未寫的**(邊界覆蓋完整性)。兩者不重疊。
> **規則依賴**：`${CLAUDE_PLUGIN_ROOT}/references/analysis-standards.md`(領域分析標準)、`${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md`(邊界維度庫,與 SA 共用)、`${CLAUDE_PLUGIN_ROOT}/skills/dev-readiness/references/boundary-checklist.md`(本 skill 的用法與阻塞判定)。

## 輸入參數

```
$ARGUMENTS → [功能目錄]
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `功能目錄` | 否 | 功能文件所在目錄(含 FRD/SAD/BFS/FFS);未給時從對話上下文推斷最近處理的功能,確認後繼續 |

## Task 0: 前置規範

> 核心原則 / 前置步驟：依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`(不猜測、Graphify 查詢、技術中立)。

若 TodoWrite 可用,建立任務清單:1. 建操作清單 2. 分組 3. 平行派工獵邊界 4. 匯流判讀 5. 派報告 6. 裁決回寫迴圈 7. 報告清理。

## Task 1: 建操作清單

> 讀取 FRD／SAD／BFS／FFS 一律定向讀取（先 `grep -n 'SPEC-INDEX v1'` 定位索引，再依章節 offset/limit 讀），不整檔載入。

讀取功能目錄下的 FRD + SAD + BFS + FFS(讀不到的標 N/A,不中止)。萃取**操作清單**:每個 CRUD / 查詢 / 動作 / 狀態轉換為一列。每列記錄:操作名、涉及資料表、對應 API 端點(BFS)、對應畫面(FFS)。

**同時讀 `analysis/_context.yml` 的 `chain_origin`**(缺欄但功能目錄有 `*_FoxPro分析報告.md` → 補寫 `foxpro`)。`foxpro` = **parity 鏈**,獵到的每個缺口先查 FoxPro 現行行為再分流:（四類偏離與三要件定義見 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`）
FoxPro 有 → 建議答案就是 FoxPro 行為(附 `FX-` 編號或 .PRG/.SCT 出處),標「對齊」,不當新問題;FoxPro 本身是 bug → 標 P-FIX,預設修;
FoxPro 沒有、也非平台必要 → 標「不處理(parity)」,**不列阻塞、不提案新規則**。Task 6 的裁決批次只放 P-FIX 與平台必要項。
原因:FoxPro 鏈到這一棒最容易長出延伸問題,每一條都會變成 PO 要否決的決策。派工時把 `chain_origin` 與分析報告路徑帶進 prompt。

## Task 2~4: 分組平行獵邊界（**派工，主 session 不逐項獵**）

對抗式獵邊界、DB 接地、覆蓋判定對**同一組操作**是連貫的三步，
由同一個 agent 一次做完；**組與組之間彼此獨立** → 同批次一次送出多個 tool call。

分組判準、派工 prompt、維度分派 → [hunt-dispatch.md](references/hunt-dispatch.md)。

<law>
**分組方式現場分析，不要照抄範例。** 判準是「前置條件相同者歸一組」——
同組共用同一批規格章節與 DB 表，agent 只需載入一次。
操作數 ≤4 時不必分組；**B13 一律單獨一組**（它不逐操作問，而是對全文掃一次「值」）。
</law>

維度速覽（定義見 `${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md`，與 SA 盤點共用編號）：
B1 空值/必填、B2 邊界值與精度、B3 唯一性(含已刪除)、**B4 狀態轉換合法性**、B5 並發衝突、
**B6 主從連動(含表頭重算,阻塞)**、B7 權限可見性、B8 整合/一致性、B9 既有資料相容性、
**B10 排序完備性(阻塞)**、**B11 畫面內容規格完備性(阻塞)**、
**B12 輸出類管道中立(阻塞,僅匯出/列印/報表適用)**、**B13 參數化來源一致性(阻塞,全文掃一次)**、
**M1~M4 領域特有**(單據狀態流轉/流程步驟依賴/金額歸集/階層結構)。

**本 skill 是三段責任的第 ③ 段：複核 ＋ 獵漏網**（見 `boundary-dimensions.md`「三段責任」）。
① SA 已盤點(SAD §6.6)、② BFS/FFS 撰寫當下已逐條落實——此處驗**②有沒有真的落實**，
並獵①②都沒想到的漏網，**不重新盤點**。B11/B12 是本階段才驗得了的維度（SA 盤點時 FFS 尚不存在）。

> ⚠️ 若某組一次獵出**大量**未落實項，那是 ② 沒做，不是本 skill 做得好——
> 在報告中明說，讓下次的 BFS/FFS 撰寫補上對照，而不是默默把它們當成本階段的功勞。

### 匯流與判讀

各組回報齊了才進 Task 5。主 session 做四件事：

1. **合併覆蓋矩陣**，確認沒有操作落在任何一組之外
2. **複核量化斷言**（阻塞項筆數、覆蓋率抽驗）——見
   `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §四
3. **判斷阻塞項是否真的阻塞**——agent 可能把技術手段誤判成業務契約
4. **lite 鏈的升級訊號**：任一組回報 B4／B5／B6／B10 有實質內容 → **分流判定有誤**，
   停下告知使用者，補做 `system-analysis` 後回 standard

## Task 5: 產就緒度報告

**先判讀再派工**：就緒度結論（✅／⚠️／❌）由主 session 判定——agent 只回各組的覆蓋矩陣，
**整體是否可進開發只有彙整後才判得出來**。判定完成後派 `report-writer` 產出報告檔：

```
subagent_type: "sa-flow:report-writer"
prompt: |
  report_type: readiness
  out_path: {功能目錄}/{功能名稱}_就緒度報告.md
  template: ${CLAUDE_PLUGIN_ROOT}/skills/dev-readiness/references/report-template.md
  dataset: {各組回報彙整檔的絕對路徑}
  constraints: |
    就緒度結論由呼叫端判定，**不得自行改判**：{✅/⚠️/❌ 與理由}
    阻塞項每條保留：問題、開發者會卡在哪、建議答案、應回寫文件＋章節
    邊界覆蓋矩陣（操作 × 維度）完整呈現，不得省略「不適用」的格
  siblings: 無
```

報告存檔至功能目錄 `{功能名稱}_就緒度報告.md`（Task 7 達 ✅ 時會問是否刪除）。

## Task 6: 裁決 → 回寫 → 重檢 迴圈

阻塞項依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`「互動詢問規範」**一次一題**,不批次表決:

1. **逐條 `AskUserQuestion`**:依影響大小排序(相依項先問被依賴的那條),每題含問題、開發者會卡在哪、
   **建議答案(必附,推薦置首)**、回寫落點(文件 + 章節)。**技術手段桶的建議答案是約束句**（如「快照不可用時降級唯讀」），不是手段（不寫「改用 Redis」）。
2. 不先列全部清單請使用者挑,不寫「未回覆視同採納」;完整清單已在就緒度報告裡。
3. 某條裁決改變其他條的選項時,先回寫再問受影響的那幾條,不沿用舊選項。
4. 裁決結果回寫對應文件:後端規則 → BFS §7 VR/BR;前端欄位/互動 → FFS §4;技術手段桶 → `decisions.md` 追加 **TD**（拍板 Dev、階段 實作、選定「待實作定案」）並在 BFS 對應章加一段 `> ⚠ TD-xxx（見 decisions.md）` 提醒;
   跨流程邊界 → SAD §6.6。**回寫前先重讀該檔取最新內容**,寫完向使用者提示 diff 摘要。
   **回寫是「取代」不是「追加」**:被裁決取代的舊敘述必刪,不留兩個版本並存;
   回寫後正文淨增 >10% 要在 `decisions.md` 記一列理由。
   **同時 append `{功能目錄}/decisions.md`**(全鏈連號,`grep -n '^| D-' decisions.md | tail -1`
   取最大號接續;`階段` 填 `dev-readiness`、`依據` 指向就緒度報告的阻塞項編號),
   並在被改文件的 `§D` 清單補一行「D-0xx｜題目｜結論」。照建議採納且無實質取捨的項不記,
   只記「使用者改選過的項」與「有實質取捨的項」。規則見
   `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`。
   `decisions.md` 不存在 → 該功能尚無決策落檔,**建檔不視為缺陷**;不要因此略過回寫。
5. 全部處理完 → **同一輪重跑覆蓋判定**：僅針對受影響操作重派該組 agent(帶上已回寫的章節),不整輪重跑。
6. 直到 0 阻塞 → 結論 ✅。

## 結論三級與交棒

| 結論 | 條件 | 下一步 |
|------|------|--------|
| ✅ 可進開發 | 0 阻塞 | 依 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` **自動續跑** `sa-flow:verifying-specs --cross`(條件全滿足時直接執行,不另問) |
| ⚠️ 有非阻塞建議 | 0 阻塞、>0 建議 | 可進,建議擇優補強後交棒 |
| ❌ 有阻塞,需先補 | >0 未答邊界 | 進入 Task 6 迴圈,不放行 |

## Task 7: 就緒度報告清理（達 ✅ 時）

結論為 ✅(0 阻塞,初次或迴圈後達成),交棒前:`{功能名稱}_就緒度報告.md` 是**驅動本次檢核的暫存產物**,任務已達成,不應遺留在版控的 feature 資料夾。

詢問使用者是否刪除報告(優先用 `AskUserQuestion`,附建議「建議刪除」;若該工具在當前執行環境不可用,改以文字明確詢問並**等待回覆**)。**經使用者確認後才刪除**,不自動刪。

⚠️ 僅可刪除本 skill 產出的 `_就緒度報告.md`,**禁止**刪除 FRD/SAD/BFS/FFS 等正式文件。

完整 pipeline 詳見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`。

## 邊界（明確不做）

- 不逐欄比對 DB 結構(`verifying-specs` D2 資料流維度的事)。
- 不做跨文件追溯矩陣(`verifying-specs` Task 8 `--cross` 模式的事)。
- 不評架構可行性 / 技術選型。
- 只獵「業務規則 / 邊界覆蓋的完整性」。

## Red Flags

**禁止捷徑**:把「規格已寫的」當成「就緒」(要主動獵未寫的)、生成無關痛癢的假問題稀釋阻塞訊號(必須 DB/業務接地)、用 `[待確認]` 帶過(必須走裁決迴圈解決)、回寫時覆蓋使用者手改(必先重讀)、**把技術手段當阻塞逼 SA 選型**(手段留置 TD,只驗約束/現況/陷阱)。

## References

- [boundary-checklist.md](references/boundary-checklist.md) — 邊界維度的 dev-readiness 用法與阻塞判定(維度定義在 plugin root 的 boundary-dimensions.md)
- [report-template.md](references/report-template.md) — 就緒度報告 + 覆蓋矩陣格式
- [analysis-standards.md](../../references/analysis-standards.md) — 領域分析標準
