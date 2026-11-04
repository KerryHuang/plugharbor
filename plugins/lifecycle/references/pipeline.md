# Development Pipeline

以 `lifecycle` plugin 走完需求到驗收的動線。規模由專案設定 `scale` 決定（`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get scale`），只決定「產出哪些檔、拆幾張票」，不分兩套流程。

```
explore → spec → spec-check → ticket-create → implement → release → qa-verify
```

入口 `triage`（單票或一批回饋）、回流 `ticket-reply`、CR 走 `spec --change {ticket}`、跨 session 協調 full 規格鏈用 `spec-chain`（手動）。

## 規模：lean 與 full

| 規模 | 規格 | 票 |
|------|------|----|
| **lean**（預設） | 一份 `<spec.dir>/<feature>.md`（`spec.dir` 預設 `docs/specs`） | 一張 |
| **full** | `spec --stage frd\|sad\|bfs\|ffs` 依序產 FRD → SAD → BFS → FFS | 父票＋PM／SA／QA／Dev 子票 |

本檔後半（全鏈效率通則、目錄結構）以 full 為主；lean 只有規格一份，見 `lifecycle:spec`。

### full 內的鏈長：先分流再開跑

判準與承接規則見 `chain-profile.md`。**判定在 FRD 定稿後做一次**（`spec --stage frd` Step 9.8），
結果寫進 `analysis/_context.yml` 的 `chain_profile`，下游讀檔取用不重判。

```
standard   ... → spec --stage frd → spec --stage sad → spec --stage bfs → ...
lite       ... → spec --stage frd ───────→ spec --stage bfs → ...
                                ↑ 略過 SAD；其四項必要產物由 BFS 承接
```

**五條全中才可略過 SAD**：單表寫入無跨表交易／無狀態機／單一畫面／無 migration 或僅加欄位／
無金額計算與權限分歧。任一不成立走完整四份；有疑慮的條目點名寫出並由 PO 判一次。

> 為什麼要分流：單欄字典（付款方式、會員等級這類）與含交易、權限、migration 的主檔功能
> 走同一條鏈，前者付的固定成本佔比極高——流程對小功能收的稅太重。

## 架構：主 session 統整派工，agent 落檔

- **主 session** 只做統整、派工、決策與使用者互動；不讀規格正文、不自己掃 codebase／查 DB／開瀏覽器。
- **spec-writer agent** 依範本、證據檔與已拍板決策落檔 FRD／SAD／BFS／FFS；勘察類 agent（`scout`、`browser-surveyor`…）把證據落進 `analysis/`。
- **每棒載 `shared-preludes.md`**（常駐卡），派工慣例見 `dispatch-conventions.md`，棒與棒之間的接力見 `handoff-protocol.md`。

## 標準流程（新功能）

```
┌─────────────────────────────────────────────────────────┐
│                  SPEC PHASE (lifecycle)                 │
│                                                         │
│  [ lifecycle:interview-prep ]（可選，需求還很零碎時）    │
│       模式 A：多場會議／訪談 → 已知未知盤點 ＋ Top 5      │
│       模式 B：產《需求訪談大綱》→ 訪談後回灌模式 A        │
│              ↓                                          │
│  [ lifecycle:explore ]                                  │
│       需求探索、設計確認                                  │
│       輸出：{功能名稱}_探索摘要.md（spec 自動讀取）        │
│              ↓                                          │
│  [ lifecycle:spec ]                                     │
│       lean：<spec.dir>/<feature>.md 一份                │
│       full：--stage frd → sad → bfs → ffs               │
│  FRD（PM）→ SAD（SA，lite 可略過）→ BFS → FFS（無畫面略過）│
│              ↓                                          │
│  [ lifecycle:spec-check --readiness ]                   │
│       開發者視角：獵未答的邊界／業務規則缺口              │
│       輸出：就緒度報告 + 回寫規格                        │
│              ↓                                          │
│  [ lifecycle:spec-check ]                               │
│       驗證已寫內容、DB 實查、跨文件一致性                 │
│       輸出：驗證報告                                     │
│              ↓                                          │
│  [ lifecycle:ticket-create ]                            │
│       經 ticket-ops 開票（lean 一張；full 為票樹）        │
└─────────────────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────┐
│                IMPLEMENTATION (lifecycle)               │
│                                                         │
│  [ lifecycle:implement ]                                │
│       開分支 → 任務清單與進度 ledger → 每 task 派 subagent │
│       → 規格比對 → 審查修正迴圈 → 收尾（可選 TDD）        │
│              ↓                                          │
│  [ lifecycle:release ]（需要發版時）                    │
│       release branch、品質閘、merge、反合；hotfix        │
└─────────────────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────┐
│                 ACCEPTANCE (lifecycle)                  │
│                                                         │
│  [ lifecycle:qa-verify ]                                │
│       Dev 完工後先依 ffs8-to-acceptance 轉 FFS §8，再對實機驗收 │
│       輸出：qa-report.md ＋ 規格校正清單                 │
└─────────────────────────────────────────────────────────┘
```

`spec-check` 三個模式：`verify`（預設）、`--readiness`（實作前獵邊界缺口）、`--sample`（對照實際程式碼驗規格覆蓋度）。

### qa-verify 批次模式

`lifecycle:qa-verify --sweep`：撈指派給我的待測票、分類、逐張驗，依結果寫回階段與留言。單張流程的處置欄由人填，本 skill 不開 Bug 票。

## 入口：票驅動分流（triage）

已有票、要決定「這張票怎麼走」，或手上有一批回饋（會議記錄、需求清單），從 `triage` 起步：

```
[ lifecycle:triage <ticket-id> ]
     ↓ 經 ticket-ops 讀票與留言
     ↓ 判有效性、判型（Feature／CR／Bug），結論附證據
     ├─[Feature／CR]→ 引導進 spec（規格通過後才 ticket-create 開票）
     └─[Bug]→ 找根因（只分析不改碼）→ 確認 → 經 ticket-ops 回票 → 視情況 ticket-create 開修復子票

[ lifecycle:triage <回饋檔> ]
     ↓ 逐項對照現況，分類成 Bug／Enhancement／Feature，輸出分類清單
```

此為**薄派工層**：自己只做判型／分流／根因／回票／觸發開票，其餘委派既有 skill。

## Feedback Loop：票上問題回流

開票後，若 Dev 或 AI agent 在票上提問，需要 PM／SA 介入時：

```
[ lifecycle:ticket-reply <ticket-id> ]
     ↓ 讀取未回覆留言
     ↓ 判角色（PM／SA），逐題預覽草稿確認
     ↓ 更新對應規格（lean 一份；full 為 FRD／SAD／BFS／FFS）
     ↓ 建議跑 lifecycle:spec-check
     ↓ 經 ticket-ops 回覆至票
```

此為非阻塞流程，可在 implementation 任意時間點執行，不影響主流程推進。

## CR 流程（既有功能調整）

> CR 需求已明確，跳過 explore，直接 `spec --change {ticket}`：in-place 修改受影響段落，取代不追加，版本號 +1 並記 CHANGELOG。

```
lean：  spec --change {ticket}   → 直接改那一份規格
full：  spec --stage frd --change {ticket}     輸出：CR-FRD
        （影響系統設計時：in-place 修訂 SAD 或重跑 spec --stage sad——SAD 無 --change）
        spec --stage bfs --change {ticket}     輸出：CR-BFS
        spec --stage ffs --change {ticket}     輸出：CR-FFS
         ↓
spec-check --readiness（CR 改動的邊界同樣要獵）→ spec-check → ticket-create
         ↓
（同標準流程：implement → release → qa-verify）
```

## 舊系統移植

先用 `lifecycle:survey-existing-system` 勘察現役系統的現況，落成現況分析文件；再走 `spec`，撰寫時依 `legacy-parity.md` 對照舊行為。`analysis/_context.yml` 的 `chain_origin` 值為 `legacy`，下游讀它判斷是否走移植鏈。

## 各 Skill 銜接點

| Skill | 前置 | 後續 |
|-------|------|------|
| `lifecycle:explore` | 需求方向大致明確 | `lifecycle:spec` |
| `lifecycle:spec`（lean） | `explore` 摘要（可選） | `lifecycle:spec-check` |
| `lifecycle:spec --stage frd` | `explore`（推薦） | `--stage sad`（lite 直接 `--stage bfs`） |
| `lifecycle:spec --stage sad` | FRD 已完成 | `--stage bfs` |
| `lifecycle:spec --stage bfs` | SAD 已完成（lite 為 FRD） | `--stage ffs` |
| `lifecycle:spec --stage ffs` | BFS 已完成 | `lifecycle:spec-check --readiness` |
| `lifecycle:spec-check --readiness` | 規格已完成 | `lifecycle:spec-check` |
| `lifecycle:spec-check` | readiness 通過 | `lifecycle:ticket-create`（尚未開票時）或 `lifecycle:implement` |
| `lifecycle:ticket-create` | 驗證通過 | `lifecycle:implement` |
| `lifecycle:implement` | 規格已通過檢查 | `lifecycle:release`、`lifecycle:qa-verify` |
| `lifecycle:qa-verify` | Dev 完工（票進 Done／PR 合併） | 規格校正清單回寫規格；Bug 經 `ticket-ops` 開票 |
| `lifecycle:ticket-reply` | 票上有未回覆問題 | `lifecycle:spec-check` |
| `lifecycle:triage` | 有票或一批回饋 | Feature／CR→`lifecycle:spec`；Bug→`lifecycle:ticket-create`（修復子票） |
| `lifecycle:spec-chain` | full 規模，手動叫用，需 herdr | 每棒決定就地做、派 subagent 或開 worker，並獨立驗收 |

## Plugin 分工

| Plugin | 職責 | 必要性 |
|--------|------|--------|
| **lifecycle** | 規格、票務、實作、發版與驗收 | 必要 |
| **workspace** | commit、review、quality-check 等版本控制與工作區工具 | 可選 |
| **browser-docs** | 畫面勘察、實機操作、截圖標註 | 可選 |
| **toolkit** | herdr 派工（`spec-chain` 需要） | 可選 |
| **backend／frontend／database／desktop** | 技術職責：依各自領域提供實作與審查規範 | 依專案技術棧 |

## 全鏈效率通則

跑完一條規格鏈的成本主要在**人機往返**與**重複分析**，不在模型產出。七條通則：

| 通則 | 內容 | 定義處 |
|------|------|--------|
| **分析落檔共用** | DB 結構、既有實作、畫面現況、顧問結論一律落 `analysis/`，下游先讀檔只補缺 | `shared-preludes.md` Step 0.8 |
| **裁決一次一題** | 每個裁決各自一次 `AskUserQuestion`，附建議答案、依影響排序；不批次表決 | `shared-preludes.md` §互動詢問規範 |
| **驗證集中鏈末** | 標準模式不跑中途驗證迴圈；`spec-check --readiness`（獵未寫）→ `spec-check`（驗已寫）各一次 | `auto-verification-loop.md` |
| **顧問桌只開一次** | 主場在 `spec --stage sad`；單顧問 `domain-advisor`，不做例行 cross-review | `consultant-desk.md` |
| **顧問觸發式介入** | SAD Step 4~6 命中 domain 訊號當場單點問，不累積到階段末整份審 | `consultant-desk.md` |
| **邊界三段責任** | ①SAD 盤點 → ②**BFS／FFS 撰寫當下落實** → ③`spec-check --readiness` 複核獵漏 | `boundary-dimensions.md` |
| **條件式自動接棒** | 零阻塞／待確認／分歧時直接續跑下一棒；硬性停點永不自動 | `handoff-protocol.md` |

另：完整畫面欄位表的唯一 owner 是 **FFS §2**（FRD §4 只寫業務層），
Step 0.5／0.7 前置檢查每 session 只做一次。

## 文件目錄結構（full）

`{docs-root}` 即 `spec.dir`（`config.py get spec.dir`，預設 `docs/specs`）。lean 只在其下產 `<feature>.md`（探索摘要為同名的 `<feature>_探索摘要.md`，`<feature>` 為 kebab-case ASCII）。

```
{docs-root}/
  {模組名稱}/
    {功能名稱}/
      {功能名稱}_探索摘要.md          ← lifecycle:explore
      {功能名稱}_需求文件.md           ← lifecycle:spec --stage frd (FRD)
      {功能名稱}_系統分析文件.md        ← lifecycle:spec --stage sad (SAD)
      {功能名稱}_後端功能規格書.md      ← lifecycle:spec --stage bfs (BFS)
      {功能名稱}_前端功能規格書.md      ← lifecycle:spec --stage ffs (FFS)
      {功能名稱}_就緒度報告.md          ← lifecycle:spec-check --readiness
      decisions.md                    ← 全鏈決策落點，見 decision-record.md
      features/
        {功能名稱}.feature             ← lifecycle:spec --stage frd Step 9.5（BDD，可選；FRD §2.2 的機械轉譯）
      analysis/                       ← 管線中間產物（非正式文件），全鏈共用，見 shared-preludes.md Step 0.8
        _context.yml                  ← 功能上下文（純路徑指標，≤5KB；含 chain_profile、chain_origin）
        _sad-draft.md                 ← spec --stage sad 確認門前暫存
        db-analysis.yml               ← DB 結構事實（SAD 首建，BFS／spec-check 共用）
        reuse-scan.yml                ← 既有實作盤點（SAD 首建，BFS／spec-check 共用）
        ui-survey.md                  ← 現有畫面勘察（最先執行 UI 分析者建，FRD／SAD／FFS 共用）
        consultant-notes.md           ← 顧問桌結論（開桌的 skill 建，下游共用不重問）
```
