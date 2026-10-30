# Development Pipeline

完整軟體開發生命週期流程，整合 `sa-flow` plugin（文件產出）與 `superpowers` plugin（流程驅動）。

## 架構：主 session 統整派工，agent 落檔

- **主 session** 只做統整、派工、決策與使用者互動；不讀規格正文、不自己掃 codebase／查 DB／開瀏覽器。
- **spec-writer agent** 依範本、證據檔與已拍板決策落檔 FRD／SAD／BFS／FFS；勘察類 agent（`scout`、`browser-surveyor`…）把證據落進 `analysis/`。
- **每棒載 `shared-preludes.md`**（常駐卡），派工慣例見 `dispatch-conventions.md`，棒與棒之間的接力見 `handoff-protocol.md`。

## 使用注意：Brainstorming 中斷點

`superpowers:brainstorming` 的 terminal state 是自動呼叫 `writing-plans`。

使用 sa-flow+superpowers 完整 pipeline 時，**必須在 brainstorming 第 8 步（使用者確認設計文件）後手動暫停**，不讓它自動跳 `writing-plans`。改由使用者依序執行 sa-flow 文件產出步驟，最後再手動執行 `superpowers:writing-plans`。

```
brainstorming 步驟 1~8（設計文件確認）→ 手動暫停
         ↓ 使用者手動接續
sa-flow:explore（可選）→ sa-flow:requirement → system-analysis → specify-backend → specify-frontend → dev-readiness → verifying-specs → linear-create
         ↓
superpowers:writing-plans（手動執行）→ 實作段 → sa-flow:qa-verify
```

---

## 兩條鏈：standard 與 lite（先分流再開跑）

判準與承接規則見 `chain-profile.md`。**判定在 FRD 定稿後做一次**（`requirement` Step 9.8），
結果寫進 `analysis/_context.yml` 的 `chain_profile`，下游讀檔取用不重判。

```
standard   ... → requirement → system-analysis → specify-backend → ...
lite       ... → requirement ─────────────────→ specify-backend → ...
                                ↑ 跳過 SAD；其四項必要產物由 BFS 承接
```

**五條全中才是 lite**：單表寫入無跨表交易／無狀態機／單一畫面／無 migration 或僅加欄位／
無金額計算與權限分歧。**任一不成立走 standard；有疑慮走 standard。**

> 為什麼要分流：單欄字典（付款方式、會員等級這類）與含交易、權限、migration 的主檔功能
> 走同一條七棒鏈，前者付的固定成本佔比極高——**流程對小功能收的稅太重**。

## 標準流程（新功能）

```
┌─────────────────────────────────────────────────────────┐
│                   UPSTREAM PHASE (sa-flow)                 │
│                                                         │
│  [ sa-flow:interview-prep ]（可選，需求還很零碎時）          │
│       模式 A：多場會議／訪談 → 已知未知盤點 ＋ Top 5      │
│       模式 B：產《需求訪談大綱》→ 訪談後回灌模式 A        │
│       輸出：{名稱}_需求彙整.md／_訪談大綱_{受訪者}.md      │
│              ↓                                          │
│  [ superpowers:brainstorming ]  或  [ sa-flow:explore ]    │
│       需求探索、設計確認                                  │
│       brainstorming 輸出：{docs-root}/superpowers/specs/*-design.md │
│       explore 輸出：{docs-root}/{模組}/{功能}/{功能名稱}_探索摘要.md │
│              ↓                                          │
│  [ sa-flow:requirement ]                                   │
│       PM 角色，撰寫功能需求文件                           │
│       輸出：*_需求文件.md (FRD)                          │
│              ↓                                          │
│  [ sa-flow:system-analysis ]                               │
│       SA 角色，分析工作流/資訊流/資料流                   │
│       輸出：*_系統分析文件.md (SAD)                      │
│              ↓                                          │
│  [ sa-flow:specify-backend ]                               │
│       建立後端 API 規格書                                │
│       輸出：*_後端功能規格書.md (BFS)                    │
│              ↓                                          │
│  [ sa-flow:specify-frontend ]                              │
│       建立前端功能規格書                                 │
│       輸出：*_前端功能規格書.md (FFS)                    │
│              ↓                                          │
│  [ sa-flow:dev-readiness ]                                 │
│       開發者視角：獵未答的邊界/業務規則缺口              │
│       輸出：就緒度報告 + 回寫 BFS/FFS                   │
│              ↓                                          │
│  [ sa-flow:verifying-specs ]                               │
│       架構師視角驗證規格書                               │
│       輸出：驗證報告                                     │
│              ↓                                          │
│  [ sa-flow:linear-create ]                                 │
│       建立 Linear ticket 層級結構                        │
│       輸出：Linear tickets                              │
└─────────────────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────┐
│              IMPLEMENTATION PHASE (superpowers)         │
│                                                         │
│  [ superpowers:writing-plans ]                          │
│       輸入：FRD + SAD + BFS                             │
│       輸出：實作計畫文件                                 │
│              ↓                                          │
│  [ superpowers:subagent-driven-development ]            │
│       平行實作，每個 task 獨立 subagent                  │
│              ↓                                          │
│  [ superpowers:verification-before-completion ]         │
│       實作完成前驗證                                     │
│              ↓                                          │
│  [ superpowers:requesting-code-review ]                 │
│       代碼審查                                          │
│              ↓                                          │
│  [ superpowers:finishing-a-development-branch ]         │
│       收尾，merge/PR                                    │
└─────────────────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────┐
│                   ACCEPTANCE (sa-flow)                     │
│                                                         │
│  [ sa-flow:qa-verify ]                                     │
│       Dev 完工後依 FFS §8 對實機逐條驗收                 │
│       輸出：qa-report.md ＋ 規格校正清單                 │
└─────────────────────────────────────────────────────────┘
```

## 入口：票驅動分流（linear-triage）

已有 Linear 票、要決定「這張票怎麼走」時，從 `linear-triage` 起步：

```
[ sa-flow:linear-triage <ticket-id> ]
     ↓ get_issue + list_comments 讀票
     ↓ AI 判型（Feature / Bug）+ 確認
     ↓ 輸出 /rename [類型] 票號 標題 建議
     ├─[Feature]→ 引導進 requirement → … → verifying-specs（規格通過後才 linear-create 開票）
     └─[Bug]→ AI 選戰場找根因（只分析不改碼不落檔）
            → 回報 → 確認 → save_comment 回票 → 委派 linear-create 開 QA→Dev 修復子票
```

此為**薄派工層**：自己只做判型/分流/根因/回票/觸發開票，其餘委派既有 skill。

## Feedback Loop：票上問題回流

開票後，若 Dev 或 AI agent 在 Linear 票上提問，需要 PM/SA 介入時：

```
[ sa-flow:linear-reply <ticket-id> ]
     ↓ 讀取未回覆 comment
     ↓ PM/SA 角色回覆（自動判斷）
     ↓ 更新對應 spec 文件（FRD / SAD / BFS / FFS）
     ↓ 自動執行 sa-flow:verifying-specs
     ↓ 回覆發佈至 Linear
```

此為非阻塞流程，可在 implementation phase 任意時間點執行，不影響主流程推進。

## CR 流程（既有功能調整）

> CR 流程需求已明確，跳過 brainstorming，直接從 requirement 開始。

```
[ sa-flow:requirement --change ]     輸出：CR-FRD
         ↓
（影響系統設計時：in-place 修訂 SAD 或重跑 system-analysis——SAD 無 --change 模式）
         ↓
[ sa-flow:specify-backend --change ]  輸出：CR-BFS
         ↓
[ sa-flow:specify-frontend --change ] 輸出：CR-FFS
         ↓
[ sa-flow:dev-readiness ]            輸出：就緒度報告 + 回寫（CR 改動的邊界同樣要獵）
         ↓
[ sa-flow:verifying-specs ]          輸出：驗證報告
         ↓
[ sa-flow:linear-create ]            輸出：Linear tickets
         ↓
（同標準流程 → superpowers:writing-plans 之後）
```

## 各 Skill 銜接點

| Skill | 前置 | 後續 |
|-------|------|------|
| `sa-flow:explore` | 需求方向大致明確 | `sa-flow:requirement` |
| `sa-flow:requirement` | `sa-flow:explore` 或 `superpowers:brainstorming`（推薦） | `sa-flow:system-analysis`（lite 鏈直接 `sa-flow:specify-backend`） |
| `sa-flow:system-analysis` | FRD 已完成 | `sa-flow:specify-backend` |
| `sa-flow:specify-backend` | SAD 已完成（lite 鏈為 FRD） | `sa-flow:specify-frontend` |
| `sa-flow:specify-frontend` | BFS 已完成 | `sa-flow:dev-readiness` |
| `sa-flow:dev-readiness` | FFS 已完成 | `sa-flow:verifying-specs` |
| `sa-flow:verifying-specs` | dev-readiness 通過 | `sa-flow:linear-create`（尚未開票時）→ `superpowers:writing-plans` |
| `sa-flow:linear-create` | 驗證通過 | `superpowers:writing-plans` |
| `sa-flow:qa-verify` | Dev 完工（ticket 進 Done／PR 合併） | 規格校正清單回寫規格 |
| `sa-flow:linear-reply` | `linear-create` 已完成，票上有未回覆問題 | `sa-flow:verifying-specs`（自動觸發） |
| `sa-flow:linear-triage` | 已有 Linear 票，要判型決定走向 | Feature→`sa-flow:requirement`；Bug→`sa-flow:linear-create`（開修復子票） |

## Plugin 分工

| Plugin | 職責 | Skills |
|--------|------|--------|
| **sa-flow** | 文件產出（upstream phase）與驗收 | explore, interview-prep, requirement, system-analysis, specify-backend, specify-frontend, dev-readiness, verifying-specs, linear-triage, linear-create, linear-reply, qa-verify, foxpro-analyzer |
| **superpowers** | 流程驅動（process & implementation） | brainstorming, writing-plans, subagent-driven-development, verification-before-completion, requesting-code-review, finishing-a-development-branch |

## 全鏈效率通則

跑完一條規格鏈的成本主要在**人機往返**與**重複分析**，不在模型產出。七條通則：

| 通則 | 內容 | 定義處 |
|------|------|--------|
| **分析落檔共用** | DB 結構、既有實作、畫面現況、顧問結論一律落 `analysis/`，下游先讀檔只補缺 | `shared-preludes.md` Step 0.8 |
| **裁決一次一題** | 每個裁決各自一次 `AskUserQuestion`，附建議答案、依影響排序；不批次表決 | `shared-preludes.md` §互動詢問規範 |
| **驗證集中鏈末** | 標準模式不跑中途驗證迴圈；`dev-readiness`（獵未寫）→ `verifying-specs`（驗已寫）各一次 | `auto-verification-loop.md` |
| **顧問桌只開一次** | 主場在 `system-analysis`；單顧問 `domain-advisor`，不做例行 cross-review | `consultant-desk.md` |
| **顧問觸發式介入** | SAD Step 4~6 命中 domain 訊號當場單點問，不累積到階段末整份審 | `consultant-desk.md` |
| **邊界三段責任** | ①SAD 盤點 → ②**BFS/FFS 撰寫當下落實** → ③dev-readiness 複核獵漏 | `boundary-dimensions.md` |
| **條件式自動接棒** | 零阻塞/待確認/分歧時直接續跑下一棒；硬性停點永不自動 | `handoff-protocol.md` |

另：完整畫面欄位表的唯一 owner 是 **FFS §2**（FRD §4 只寫業務層），
Step 0.5／0.7 前置檢查每 session 只做一次。

## 文件目錄結構

`{docs-root}` 由目標專案 `CLAUDE.md` 的 `sdlc-docs-path` 決定（未設定則為 `docs/`）。

```
{docs-root}/
  {模組名稱}/
    {功能名稱}/
      {功能名稱}_探索摘要.md          ← sa-flow:explore
      {功能名稱}_需求文件.md           ← sa-flow:requirement (FRD)
      {功能名稱}_系統分析文件.md        ← sa-flow:system-analysis (SAD)
      {功能名稱}_後端功能規格書.md      ← sa-flow:specify-backend (BFS)
      {功能名稱}_前端功能規格書.md      ← sa-flow:specify-frontend (FFS)
      {功能名稱}_就緒度報告.md          ← sa-flow:dev-readiness
      {功能名稱}_FoxPro分析報告.md     ← sa-flow:foxpro-analyzer
      decisions.md                    ← 全鏈決策落點，見 decision-record.md
      features/
        {功能名稱}.feature             ← sa-flow:requirement Step 9.5（BDD，可選；FRD §2.2 的機械轉譯）
      analysis/                       ← 管線中間產物（非正式文件），全鏈共用，見 shared-preludes.md Step 0.8
        _context.yml                  ← 功能上下文（純路徑指標，≤5KB）
        _sad-draft.md                 ← system-analysis 確認門前暫存
        db-analysis.yml               ← DB 結構事實（SAD 首建，BFS/dev-readiness/verifying-specs 共用）
        reuse-scan.yml                ← 既有實作盤點（SAD 首建，BFS/verifying-specs 共用）
        ui-survey.md                  ← 現有畫面勘察（最先執行 UI 分析者建，FRD/SAD/FFS 共用）
        consultant-notes.md           ← 顧問桌結論（開桌的 skill 建，下游共用不重問）
  superpowers/
    specs/
      YYYY-MM-DD-{topic}-design.md    ← superpowers:brainstorming
```
