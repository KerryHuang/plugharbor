# Development Pipeline

以 lifecycle 與 tickets 等 plugin 走完需求到驗收的動線；規格到驗收在 lifecycle，票務在 tickets，沒裝的段落照 `shared-preludes.md`「可選依賴」降級。一個功能一份規格 `<spec.dir>/<feature>.md`（`spec.dir` 預設 `docs/superpowers/specs`），一張票（要拆才有子票）。

```
triage／ticket-create → spec → spec-check → implement → release → qa-verify
```

回流 `ticket-reply`；CR（既有功能調整）走 `spec --change {ticket}`。

## 架構：主 session 統整派工，agent 落檔

- **主 session** 只做統整、派工、決策與使用者互動；大量讀碼、查 DB、開瀏覽器交 agent。
- 勘察類 agent（`tickets-scout`、`browser-surveyor`…）把證據落進 `{spec.dir}/analysis/<feature>/`（DB 結構事實全站共用一份）；顧問 `domain-advisor` 的時機見 `consultant-desk.md`（沒有 `lifecycle:domain-advisor` 就跳過顧問層，見 `shared-preludes.md`「可選依賴」）。
- 共通前置見 `shared-preludes.md`（常駐卡），派工慣例見 `dispatch-conventions.md`。

## 標準流程（新功能）

```
[ discovery:interview-prep ]（可選，需求還很零碎時）
     ↓
[ lifecycle:spec ]           一份規格；需求模糊時開頭先問清楚（一次一題）
     ↓                       「驗收」一節＝qa-verify 的輸入
[ lifecycle:spec-check ]     實作前檢查：待澄清清零、驗收可測、引用的元件／表真的存在
     ↓
[ tickets:ticket-create ]  尚未開票時（預設一張）
     ↓
[ lifecycle:implement ]      分支 → 實作前檢查 → 交給 superpowers（沒裝走退路）→ 收尾回填
     ↓
[ lifecycle:release ]        需要發版時：release branch、品質閘、merge、反合；hotfix
     ↓
[ lifecycle:qa-verify ]      設計文件「驗收」轉案例（spec_to_cases.py）後對實機驗收
```

`spec-check --sample`：對照實際程式碼驗規格覆蓋度（逆向補規格或懷疑規格過期時）。

### qa-verify 批次模式

`lifecycle:qa-verify --sweep`：撈指派給我的待測票、分類、逐張驗，依結果寫回階段與留言。單張流程的處置欄由人填，本 skill 不開 Bug 票。

## 入口：票驅動分流（triage）

已有票、要決定「這張票怎麼走」，或手上有一批回饋（會議記錄、需求清單），從 `triage` 起步：

```
[ tickets:triage <ticket-id> ]
     ↓ 經 ticket-ops 讀票與留言
     ↓ 判有效性、判型（Feature／CR／Bug），結論附證據
     ├─[Feature／CR]→ 引導進 spec（規格通過後才 ticket-create 開票）
     └─[Bug]→ 找根因（只分析不改碼）→ 確認 → 經 ticket-ops 回票 → 視情況 ticket-create 開修復票

[ tickets:triage <回饋檔> ]
     ↓ 逐項對照現況，分類成 Bug／Enhancement／Feature，輸出分類清單
```

此為**薄派工層**：自己只做判型／分流／根因／回票／觸發開票，其餘委派既有 skill。

## Feedback Loop：票上問題回流

```
[ tickets:ticket-reply <ticket-id> ]
     ↓ 讀取未回覆留言，判角色（PM／SA），逐題預覽草稿確認
     ↓ 更新規格 → 建議跑 lifecycle:spec-check
     ↓ 經 ticket-ops 回覆至票
```

非阻塞，可在 implementation 任意時間點執行。

## CR 流程（既有功能調整）

`spec --change {ticket}`：in-place 修改受影響段落，取代不追加，並在文末 `## 變更紀錄` 加一行（舊範本為 §7，版本號 +1）→ `spec-check` → 同標準流程。

## 舊系統移植

先用 `discovery:survey-existing-system` 勘察現役系統的現況，落成現況分析文件；再走 `spec`，撰寫時依 `legacy-parity.md` 對照舊行為（設計文件開頭行標「來源：舊系統移植」，舊範本為表頭「來源｜舊系統移植」）。

## 各 Skill 銜接點

| Skill | 前置 | 後續 |
|-------|------|------|
| `lifecycle:spec` | 需求或設計文件（可選） | `lifecycle:spec-check` |
| `lifecycle:spec-check` | 規格已寫完 | `tickets:ticket-create`（尚未開票時）或 `lifecycle:implement` |
| `tickets:ticket-create` | 描述或規格 | `lifecycle:implement` |
| `lifecycle:implement` | 規格已通過檢查 | `lifecycle:release`、`lifecycle:qa-verify` |
| `lifecycle:qa-verify` | Dev 完工（票進 Done／PR 合併） | 規格校正清單回寫規格；Bug 經 `ticket-ops` 開票 |
| `tickets:ticket-reply` | 票上有未回覆問題 | `lifecycle:spec-check` |
| `tickets:triage` | 有票或一批回饋 | Feature／CR→`lifecycle:spec`；Bug→`tickets:ticket-create` |

## Plugin 分工

| Plugin | 職責 | 必要性 |
|--------|------|--------|
| **lifecycle** | 規格、規格檢查、實作入口、發版與驗收 | 規格到驗收必要；只用票務可不裝（可選） |
| **tickets** | 票務（ticket-ops、ticket-create、ticket-reply、ticket-report、triage） | 票務必要 |
| **discovery** | 會議記錄、訪談準備、現況勘察、原型 | 可選 |
| **delivery** | 操作手冊、示範影片 | 可選 |
| **superpowers** | brainstorming、計畫、實作、審查 | 建議（沒裝時 implement 走退路） |
| **workspace** | commit、review、quality-check 等版本控制與工作區工具 | 可選 |
| **browser-docs** | 畫面勘察、實機操作、截圖標註 | 可選 |
| **toolkit** | herdr 派工（雙顧問 pane 模式） | 可選 |
| **backend／frontend／database／desktop** | 技術職責：依各自領域提供實作與審查規範 | 依專案技術棧 |

## 文件目錄

```
{spec.dir}/
  <feature>.md          ← lifecycle:spec（kebab-case ASCII）
  analysis/             ← 勘察中間產物（非正式文件），見 shared-preludes.md Step 0.8
    db-analysis.yml     ← DB 結構事實，全站共用
    <feature>/          ← 每個功能一份：reuse-scan.yml、ui-survey.md、consultant-notes.md、advisor-discussion/
```
