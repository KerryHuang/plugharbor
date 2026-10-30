---
name: qa-sweep
description: 批次撈 Linear 指派給我的待測票，交 qa-verify（UI）或後端驗證後依結果寫回狀態、通知父票或開 Dev 子票。觸發：「掃待測票」「qa-sweep」「把待測的票跑一輪」。
---

# qa-sweep — 待測票批次驗收

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

編排者：撈票、分類、測、寫回 Linear。**測試本身交 `qa-verify`**（UI）或 `references/backend-verify.md`（純後端），本 skill 不判定 TC。
`<ws>`＝workspace 根字面絕對路徑；工作區 `<ws>/.tmp/<YYYYMMDD>-qa-sweep/`，`sweep.yml` 記每張票的類別與結果。

```
/qa-sweep            撈票 → 分類 → 勾選 → 測 → 寫回
/qa-sweep <票號>     只跑該張（仍套 S1 兩條規則判定；都不符 → 停並回報實際狀態）
/qa-sweep --dry-run  到 S2 列完分類即停，不測不寫
```

## 狀態對照（S0 先驗）

team 取自專案 `CLAUDE.md` 的 `sdlc-linear-teams`（QA／PM／Dev 三列；SA 與 PM 同 team 時合併）。沒設 → `AskUserQuestion` 讓使用者從 `list_teams` 選。
各 team 的狀態名依專案 Linear 設定，預設如下：

| 角色 | 待測 | 退回 | 通過 |
|---|---|---|---|
| QA team | Ready For QA | Todo | Done |
| PM team | Testing | Todo | Done |
| Dev team | Testing | Todo | Done |

**S0**：各 team 跑 `list_issue_statuses`，表中狀態名任一不存在 → 停，回報實際狀態清單，請使用者給對照（不自行猜同義狀態）。

## 留言標記（冪等鍵）

每則留言首行是一條完整標記，**比對整行**，同一行已存在才跳過：
- 原票：`📌 qa-sweep <YYYY-MM-DD> <票號> <PASS|FAIL|待人工>`
- 父票：`📌 qa-sweep <YYYY-MM-DD> 子票 <票號> PASS`

只比日期會吞掉同日第二張子票的父票通知、或同票先 FAIL 後 PASS 的通過留言。

## S1 撈票

`list_issues assignee=me`（分頁撈完），只留：
- **規則一**：狀態 ∈ 各 team 的「待測」
- **規則二**：狀態屬 `started`／`unstarted` 類型（如 In Progress、Todo），且子票**至少 1 張**、全部 Done／Canceled（沒有子票的不算）

**子票判定不逐張查**（我名下 In Progress／Todo 常破百張，逐張 `list_issues parentId=` 要上百次呼叫）：
1. 各 team 以 `state` ＝ `triage`／`backlog`／`unstarted`／`started` 撈全部票（`fields: ["parentId"]`，分頁撈完），收集出現過的 `parentId` ＝「有未完成子票的票」集合。
2. 規則二候選扣掉這個集合；剩下的才逐張 `list_issues parentId=<票號>` 確認至少 1 張子票。
3. 同一集合也用在 S2 第 1 類（規則一的票若在集合內 → 待人工）。

## S2 分類（一張只歸一類，依序判）

1. **待人工**：
   - Dev team 的票（Dev 票沒有可掛的子票層，交人處理）；
   - 架構／基礎設施／傘票（標題含【架構收斂】【基礎設施】、或描述是多階段計畫）；
   - **規則一的票但還有未完成子票**（修復沒做完就測，會判 FAIL 再重複開票）；
   - 最新一則 qa-sweep 標記是 `待人工`，且其後沒有其他人的留言（避免每輪重問；要重測用單張模式）。
2. **後端驗證**：labels 含 `Bug`，且票面與 Dev 子票只涉及 API／Job／DB（子票 labels 只有 Backend*、標題帶 Job／端點），無畫面可操作。
3. **自動測-票面**：其餘 labels 含 `Bug` 的票，以及**非 Feature 根票**的 CR／Enhancement／[SA]／子需求票。這類票改的是一個點，跑整份 FFS §8 時 §8 未必有對應 TC，會在改動沒驗到的情況下全 PASS 自動結案。
4. **自動測-規格**：**Feature 根票**（labels 含 `Feature` 且沒有 `parentId`），依 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md`「票↔文件雙向註記」反查得到 FFS §8。
5. 都不符 → 待人工。

**部署狀態不在 S2 判**：版本閘要逐張遞迴找 Dev 票完工留言再比對環境，成本高且 `qa-verify` Step 0 本來就會做；改在 S4 逐張判（見下）。`--dry-run` 因此不含「未部署」，摘要註明「部署狀態未判」。

用 `AskUserQuestion`（multiSelect）列出類別 2／3／4 的票（票號＋標題＋類別），讓使用者勾本輪要跑的；待人工只列不選。`--dry-run` 列完即結束。

## S3 規則二先推待測

勾選中屬規則二的票，`save_issue` 改成該 team 的「待測」狀態再測。中斷時票停在待測，下輪由規則一撿回。

**不替子票壓狀態**：批次整理母票時，樹下只要有 QA 票在 `Ready For QA`，整棵樹維持原狀交給 QA 測——把它壓成 Done 等於替 QA 跳過驗收。任何批次改狀態都先列候選、確認後才動，分小批、先改母票，讓中途喊停時的影響最小。
> 曾有批次整理時使用者中途改條件，agent 已壓了數十張子票，只能逐張還原，留下狀態歷史與通知。

## S4 逐張測（不並行）

- **部署閘（每張先判）**：類別 3／4 由 `qa-verify` Step 0 第 5 點判；Dev 票不一定是直屬子票（Feature 樹是 PM→QA→Dev）——**往下遞迴**找 labels 含 `Backend*`／`Frontend*` 的票取完工留言，每張都已部署才算過。類別 2 照 `backend-verify.md` §3。判出未部署、或使用者在版本閘選「等部署」→ 該票記**未部署**，不動票，換下一張。qa-verify 回報「待人工：票面環境 <slug> 無帳密」→ 該票記待人工（原因照抄），不換環境硬跑：換環境跑的結果會因環境特性 TC BLOCKED，白耗三支 agent 也無法自動結案。
- 工作區：類別 3＝`<ws>/.tmp/qa-verify/<票號小寫>/`、類別 4＝`<ws>/.tmp/qa-verify/<功能碼小寫>/`。**invoke 前**若該工作區已有 `verdict.json`，改名 `verdict.prev.json`——舊結果不可被當成本輪結果。
- 類別 3：invoke `sa-flow:qa-verify <票號> --from-ticket --no-comment`；類別 4：`sa-flow:qa-verify <票號> --no-comment`。留言由 S5 統一貼（qa-verify 的 `--linear` 摘要在 `<工作區>/linear-comment.md`）。
- 類別 2：照 `references/backend-verify.md`，結果在 `<sweep 工作區>/<票號小寫>-backend.yml`。
- qa-verify 第一閘停下問使用者時照答；選「先校正規格／歸待人工」→ 該票記待人工，換下一張。
- 環境中斷（瀏覽器／DB 查詢工具／Linear 連不上）→ 停整批，跳 S6 摘要。

**結果可用**：`verdict.json`（或 backend.yml）本輪有產出，且 `總計` 六個值相加＝`plan.yml` cases 數（backend.yml 為 cases 數）。不可用 → 該票記待人工（原因「結果不可用」）。
**判定（嚴格 PASS）**：`總計.PASS` ＝ TC 總數，且 FAIL／前端未擋／BLOCKED／未執行／無法比對 皆 0。FAIL ≥ 1 → FAIL；其餘 → 待人工。

## S5 寫回 Linear

寫前 `list_comments` 查標記（見上）。寫入失敗重試一次，再失敗記入摘要，不靜默略過。

**類別 3／4 嚴格 PASS → 自動**（先改狀態、後留言：狀態沒改成功就不留「已 Done」的話）：
1. 原票 `save_issue` 狀態＝通過；失敗 → 記摘要，本票不留言。
2. 原票 `save_comment`：標記行（PASS）＋`linear-comment.md` 內容。
3. 有 `parentId` → 父票 `save_comment`：父票標記行＋「<票號> 驗收通過，<PASS 數> 條 TC 全過」。**父票狀態不動**（由規則二推）。

**待人工**：原票 `save_comment` 標記行（待人工）＋原因一句；不改狀態。

**FAIL 與類別 2 全部結果 → 收齊後整批預覽**：一張表列 票號／結果／FAIL 的 TC 與證據一句／擬處置（Done 或 開子票＋退 Todo），`AskUserQuestion` 讓使用者逐張勾選要執行的。確認後：
- 類別 2 PASS：同上「自動」三步，但步驟 2 改貼 backend.yml 的總計＋每條 TC 一行證據。
- FAIL：
  1. invoke `sa-flow:linear-create`：「既有 <team> 根票 <票號> 下開 Dev 票（Bug）；內容＝以下 FAIL TC 的預期與觀察證據（內嵌全文，不放本機路徑）」。它會出自己的草稿確認。
  2. **子票建立成功後**才對原票：`save_comment`（標記行（FAIL）＋FAIL 摘要＋新子票號）、`save_issue` 狀態＝Todo。
  **🔴 順序不可顛倒**：原票通常有已 Done 的舊子票，先退 Todo 而開票失敗，會立刻符合規則二被撿回空轉。子票開不成 → 原票不動，記入摘要。

## S6 摘要

一張表：票號／類別／結果（Done、退回＋子票號、待人工原因、未部署、寫入失敗）。
本輪改 Done 的票，`Glob {docs-root}/**/*_<票號>.md` 有命中 → 列「待 `sa-flow:consolidate-docs`」（不自動跑）。

摘要後依動線用 AskUserQuestion 建議下一步：有「待 consolidate-docs」→ `sa-flow:consolidate-docs`；有待人工 → 逐張以單張模式重跑或交人；使用者同意才接著跑，不自動執行。

## 收尾

- 本輪起的 Chrome 照 `qa-verify` 收尾規則關閉並驗證。
- 摘要回報後刪 `<ws>/.tmp/<YYYYMMDD>-qa-sweep/`；`qa-verify` 的工作區由它自己的規則處理。

## 不做

不排程、不並行測、不自行判定 TC、不接 `linear-triage`、不改父票狀態（規則一）、不動待人工／未部署的票狀態。
