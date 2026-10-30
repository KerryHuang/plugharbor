---
name: verifying-specs
description: "實作前驗證 FRD／SAD／BFS／FFS：架構可行性、資料流正確性、DB 結構實查、跨文件追溯；--cross 做跨文件一致性。觸發：「驗證規格」「verifying-specs」。"
context: fork
model: sonnet
argument-hint: "[文件路徑] [--cross] [--recheck] [--quick|--full]"
---

# Verifying Specs — 架構師級規格書驗證

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

核心問題：**「這份規格書能不能直接寫 code？寫出來能不能在現有架構和真實資料上跑？」**
> **規則依賴**：`${CLAUDE_PLUGIN_ROOT}/references/analysis-standards.md`（業務領域、資料比對、串接分析標準）
## 輸入參數

```
$ARGUMENTS → [document-path] [--cross {功能目錄}] [--recheck] [--quick|--full]
```

| 參數 | 必填 | 模式 | 說明 |
|------|------|------|------|
| `document-path` | 否* | 單文件 | 要驗證的 FRD/SAD/BFS 路徑；執行 Task 1~7 |
| `--cross {目錄}` | 否* | 跨文件 | 驗證目錄下所有相關文件；執行 Task 1+8 |
| `--recheck` | 否 | 複驗 | **修正後的第二輪**：只驗修正是否落地、有無引入新矛盾；不重跑上一輪已通過的事實查證 |
| `--quick` | 否 | 快速 | 跳過 D5／D6，只派 D2/D3/D4；適合迭代修正、純新功能 |
| `--full` | 否 | 完整 | 預設值，可省略；Task 1-7 全執行，含舊系統比對、領域一致性 |

\* 前兩者必填其一；同時提供時以 `--cross` 為主。`--recheck` 為修飾旗標，與前兩者併用。

### `--recheck` 複驗模式

第一輪判 ❌ 修正後，第二輪**預設加 `--recheck`**——首輪已實證通過的事實（既有實作、端點現況、欄位型別、
migration 範本）修正期間不會變，重驗是空轉。

複驗只做三件事：

1. **逐項確認上一輪每個 CRITICAL／WARNING 已落地**（看修正後的實際內容，不可只看 CHANGELOG 怎麼寫）
2. **檢查修正有無引入新矛盾**（常見：改 A 檔忘了同步 B 檔、補說明破壞 Markdown 結構）
3. 其餘維持原判定，一行帶過「首輪已驗證且本輪未觸及」

呼叫時**明列上一輪發現編號與修正落點**供逐項對照。

**修正棒收尾條件（派工樣板必含，主 session 親手小修也適用）**：① 被改文件升版號＋CHANGELOG 列本輪編號；
② 回報「殘留 grep」0 命中；③ 回報行數／正文體積前後。**沒升版視同未修正**——
曾有一輪 20 餘處小修沒留紀錄，下一輪因此多出 5 條 WARNING 且無法溯源。

修正棒**逐條對著報告的 `file:line` 親手改**，不派 subagent 整章重寫——整章重寫會在沒被點名的地方長出新 CRITICAL。

> 實證：首輪 448 秒／5 CRITICAL，收窄範圍複驗 177 秒（省 60%）未漏，還抓到新引入的表格斷裂。
> **複驗仍要獨立判斷，不是走過場**——量化斷言複核要求見下方 Task 2-6 `<law>`。

## Task Initialization (MANDATORY)

### 模式選擇（依旗標，不互動）

本 skill 以 `context: fork` 執行，fork 裡**沒有 `AskUserQuestion`**，不能中途問使用者。
模式一律由 `$ARGUMENTS` 決定：

- 帶 `--quick` → **快速驗證**：跳過 D5／D6
- 不帶旗標或帶 `--full` → **完整驗證**（預設）：Task 1-7 全執行，適合首次驗證、FoxPro 遷移規格書

開始時用一行告知本次採用的模式與判定依據。

若文件 CHANGELOG 提及 "FoxPro"，即使帶了 `--quick` 仍**強制派 D5**，並在開始時告知使用者原因。

若 TodoWrite 可用，依選擇模式建立任務清單。**完整模式**：1. 識別文件類型 2. 平行派五維度（D2~D6）3. 判讀彙整 4. 派報告。**快速模式**：同上但只派 D2/D3/D4。**跨文件**：1. 識別文件 2. Task 8 跨文件一致性 3. 判讀彙整 4. 派報告。各維度的缺失清單由 agent 回報（CRITICAL/WARNING/INFO），主 session 彙整。

## Task 0: 前置規範

依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`（Docs 同步、Graphify 查詢）。

---

## Task 1: 識別文件類型與架構定位

### 1.0 待澄清事項清零（前置門檻）

讀取文件中的「待澄清事項」章節（第 15 節，若為 BFS）。

| 檢查項目 | 等級 |
|---------|------|
| 待澄清章節存在 | CRITICAL |
| 所有待澄清項目狀態為「已解決」或「N/A」 | CRITICAL |
| 無殘留 TODO / 待確認 / TBD 字樣（待澄清章節以外） | WARNING |

發現問題 → 記錄到缺失清單，**繼續**後續驗證（不中止）。

### 1.1 決策傳播比對（機械閘門，`--cross` 與 `--recheck` 皆跑）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/verifying-specs/scripts/check-decision-propagation.py <功能目錄>
```

腳本比對 `decisions.md` 每條 D 與四份規格 `§D`：本階段 D 正文引用卻未列 §D、階段文件 §D 缺該階段 D、
回寫型 D（dev-readiness／verifying-specs／CR）不在任何 §D、編號斷號重號；R5 暫定 D 正文未帶「（暫定，D-xxx 待確認）」或定案 D 殘留標記；
R6 文件資訊版本≠CHANGELOG 最高版本——**每筆 CRITICAL，原樣進缺失清單**，不用 agent 判。
> 曾有一輪 `--cross` 首輪 9 CRITICAL 中有 7 筆是決策未傳播；散文規則擋不住，改腳本。

讀取 `$ARGUMENTS` 指定文件**一律分章定向**（先讀 SPEC-INDEX → `grep -n "^## "` 取章起行 → `Read` 帶 offset/limit 只讀當前 Task 要驗的章）。**完整模式也不整檔載入**（舊「完整模式可整檔讀」例外已取消）。範本同樣只載被查章節（`sed -n '/^## 6\./,/^## /p' ${CLAUDE_PLUGIN_ROOT}/templates/bfs.md`），**必須對照範本比對，不可憑記憶**。需整份逐章比對（章節缺漏、結構完整性）時，派 `general-purpose` subagent（`model: sonnet`）讀文件與範本，只回「章節｜缺失｜等級」清單，主 context 不載全文。

| 文件特徵 | 類型 | 範本路徑 |
|----------|------|---------|
| `FRD-*` | 功能需求文件 | `${CLAUDE_PLUGIN_ROOT}/templates/frd.md` |
| `BFS-*` | 後端功能規格書 | `${CLAUDE_PLUGIN_ROOT}/templates/bfs.md` |
| `CR-*` | 功能調整文件 | 對應 CR 範本；**必須**執行 [CR 交叉驗證](references/cr-validation.md) |

---

## Task 2~6: 五維度平行驗證（**派工，主 session 不逐項查**）

五個維度**彼此獨立、都不寫檔**（結果進回報）→ **同批次一次送出五個 tool call**，不要序列跑。

完整派工樣板、各維度的檢查清單與額外輸入 → [verify-dispatch.md](references/verify-dispatch.md)。

| 維度 | 查什麼 | 條件 |
|---|---|:--:|
| **D2 資料流**（核心） | DB 結構逐欄比對、**實際資料真實性**、資料流向追蹤、表頭-明細一致性 | 一律 |
| **D3 資訊流** | API 端點架構、讀寫邏輯可行性、驗證規則完整性、現有系統整合、外部服務、例外處理 | 一律 |
| **D4 架構可行性** | 見 `task-checklists.md` Task 4 段落 | 一律 |
| **D5 舊系統交叉比對** | 畫面欄位→Request/Response、驗證規則→VR/BR、CRUD 事件→API、實際資料三方比對 | 舊系統遷移時 |
| **D6 領域一致性** | 生命週期定位、狀態流轉、前後置依賴、金額／數量歸集、主檔與明細結構、跨模組 FK | 一律 |

**D2 是核心**：DB 是 Single Source of Truth。且**實際資料驗證不適用快取**——
對已存在且有資料的表必須當場查詢，因為驗的正是「規格假設與現實資料是否相符」。

> 📌 **`--quick` 模式**：跳過 D5／D6，只派 D2/D3/D4；FoxPro 例外見上方「模式選擇」。

<law>
**彙整時要複核量化斷言。** 曾出現 agent 宣稱「分析報告實為 VR-001~024」，實查是 **025**。
五個維度回報的數量、範圍、筆數，抽驗後再寫進報告。
通用盲區見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §四。
</law>

**匯流**：五個維度全部回報齊了才進 Task 7。任一維度失敗的處置見 verify-dispatch.md
（D2 因唯讀 DB 查詢工具不可用而未驗 → **最終結論自動降為 ⚠️**）。

---
## Task 7: 生成架構師驗證報告

**先判讀再派工**：五個維度回來的是缺失清單，**「整體可否開發」的結論只有主 session 判得出來**
（agent 被明令不得下此結論）。判定結論、複核量化斷言、決定每條缺失的等級之後，
再派 `sa-flow:report-writer` 產出報告檔。

```
subagent_type: "sa-flow:report-writer"
prompt: |
  report_type: verification
  out_path: {報告絕對路徑}
  template: ${CLAUDE_PLUGIN_ROOT}/skills/verifying-specs/references/report-template.md
  dataset: {五維度缺失清單彙整檔的絕對路徑}
  constraints: |
    結論等級由呼叫端判定，**不得自行改判**：{✅/⚠️/❌ 與理由}
    每條缺失保留原始等級與證據定位，不得合併或省略
  siblings: 無
```

**報告必須包含**：架構師評估摘要（一段話結論）、驗證結果表、缺失清單、
DB 實際資料驗證明細、現有資源盤點。

| 結論 | 條件 |
|------|------|
| ✅ **可直接開發** | 0 CRITICAL, 0 BLOCKER, 0 WARNING |
| ⚠️ **需修正後開發** | 0 CRITICAL, 0 BLOCKER, >0 WARNING |
| ❌ **不可開發，需重大修訂** | >0 CRITICAL 或 >0 BLOCKER（BLOCKER 等同 CRITICAL，未清零不得標示可開發） |

> BLOCKER 具體項目清單見 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md`「撰寫/驗證時的引用」表；本表判定邏輯以此處為準。

**驗證通過後的下一步**（結論為 ✅ 或 ⚠️ 修正完成後）：

1. **尚未開票** → `sa-flow:linear-create {功能描述}` 建立票樹。這是
   `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 的**硬性停點**——開票是對外動作
   （指派他人、產生 SLA），**一律先確認**，不自動接棒。已有票樹（回票迭代）→ 不重開，必要時 `sa-flow:linear-reply`
2. 進入實作 → 執行 `superpowers:writing-plans`（輸入文件：FRD、SAD、BFS）

收尾提醒：feature 資料夾殘留 `{功能名稱}_就緒度報告.md`（dev-readiness 暫存產物）→ 最終報告一行提示即可
（如「殘留就緒度報告，可自行刪除」），**不另開詢問**（owner 是 `dev-readiness` Task 7，問兩次是往返浪費）。

完整 pipeline 詳見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`。

## Task 7.5: Graphify 知識圖譜更新（條件式）
> 參考 `${CLAUDE_PLUGIN_ROOT}/references/graphify-integration.md` — **Update 區塊**（graphify 未安裝時靜默跳過）

## Task 8: 跨文件一致性驗證（--cross 模式）

**觸發條件：** `$ARGUMENTS` 包含 `--cross` 時執行。

### 8.1 定位所有相關文件

探索專案文件目錄，搜尋所有相關文件（FRD / SAD / BFS / 實作計劃 / 任務列表），標記 ✅/❌/N/A。

### 8.2 FRD ↔ SAD 一致性 / 8.3 SAD ↔ BFS 一致性 / 8.4 BFS ↔ 計劃/任務 一致性

檢查項目與等級 → [references/cross-doc-checklists.md](references/cross-doc-checklists.md)（8.2～8.4 段落）。

### 8.5 追溯矩陣（--cross --full 時產出）

詳見 [references/cr-validation.md](references/cr-validation.md)。

### 8.6 FFS ↔ BFS 驗證規則對齊（`--cross` 模式）／8.7 BFS 內部邏輯一致性（多入口 / Bug Fix）

8.7 **觸發**：BFS 描述含「兩入口/三入口/共用 Mapper/Bug Fix/對齊」關鍵字。檢查項目與等級 → [references/cross-doc-checklists.md](references/cross-doc-checklists.md)（8.6／8.7 段落，8.7 另附詳細規則連結）。

### 8.8 文件邊界去重（`--cross` 模式）

**技術決策留置（TD）三項**（依 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`「技術決策留置」）：① 規格正文出現手段定案（指定鎖種類／快取／佇列／儲存實作／重試做法）而 `decisions.md` 無對應 TD → WARNING「越線定案」；② TD 的依據缺「約束／現況／陷阱」任一 → WARNING；③ CHANGELOG 含「完工回寫」但 `decisions.md` 仍有「待實作定案」的 TD → WARNING。TD 未定案本身**不是** CRITICAL，不擋開發。

依 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md`「撰寫/驗證時的引用」逐項檢查：**去重三項為 BLOCKER**——
下游未重抄上游 owner 產物（狀態圖/流程圖/ER/快照）改 ref+增量、跨文件編號一致（VR-001 不寫 VR-01）、
BFS 內部無自我重複（§2.4↔§4.2、§3↔§4.1、§12/13/14）；**SPEC-INDEX、正文體積（FRD/SAD/FFS ≤30KB、BFS ≤45KB）
與另五項（版本資訊雙寫／必畫圖缺／公式無算例／引用檔不存在／§D 未指向 decisions.md）為 WARNING**。
逐項判準、偵測指令與門檻細節 → [references/cross-doc-checklists.md](references/cross-doc-checklists.md)「8.8」、
[references/index-and-size-checks.md](references/index-and-size-checks.md)。
另：功能目錄存在 `features/*.feature` 時，其場景 AC 編號集合須與 FRD §2.2 AC 編號集合一一對應
（無多無少，**CRITICAL**），不一致要求依 FRD 重新機械轉譯（規範見 `${CLAUDE_PLUGIN_ROOT}/skills/requirement/references/bdd-feature-guide.md`）。

### 8.9 參數化來源一致性（`--cross` 模式，B13）

**這一節與 8.2~8.8 相反**：其餘各節比對「兩份文件說的是否一樣」，本節抓「**兩份文件說得一樣、但來源不同**」——
一處寫 `8`、另一處寫「推導成 8」，字面一致，一般一致性比對抓不到（實例：「衍生號基底 8 碼」跑五輪
零告警都沒攔下，因兩處字面都是 8——本節即為此新增）。維度定義見 `${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md` B13。

判等級：**同一個值一處標推導來源、另一處寫字面常數＝CRITICAL**（設定調整後兩端會靜默分裂）；
**值有設定檔／參數表落點但規格全篇只寫字面值＝CRITICAL**（產生端與驗證端會各算一次）；
值出自 schema（欄寬／精度）但未標來源與勘察日期＝WARNING；業務常數（無設定落點）各處字面一致＝通過；
敘述性複述／實證統計／TC 測資不列入。**修法**：不逐處改公式，在最上游文件設一張「參數→推導式→現行值」表，
其餘章節引用它。掃描步驟與過濾規則（如何從全文抓出候選值、如何排除敘述性語句） →
[references/param-source-consistency.md](references/param-source-consistency.md)。

### 8.10 平台事實抽驗（`--cross` 模式，固定三項）

`--cross` 只比文件互相一致，**文件一致地寫錯平台事實它抓不到**。固定抽驗三項，任一不符＝CRITICAL：
① 可見性閘門鏈——規格「開通」是否等於專案實際的功能開通機制（以專案文件或 codebase 為準，如開關旗標＋授權列＋測試版旗標；不要把「看起來像開關」的欄位當閘門）；
② 功能代碼登記——專案若有功能代碼清冊，已有該碼、route 與 FFS 一致（無清冊則略過此項）；
③ 既有端點慣例——BFS「沿用既有」的端點/參數命名/錯誤形狀，grep codebase 一筆實證。
> 實例：四輪 `--cross` 零 CRITICAL，`--full` 才抓到「逐客戶開通」機制寫錯，五處文件一致地錯。

### 8.11 FoxPro 對齊追溯（`--cross`，功能目錄有 `*_FoxPro分析報告.md` 時）

每條 VR／BR 必須對到 `analysis/validation-rules.yml` 的 `FX-VR`／`FX-BR` 編號，**或** `decisions.md` 一條標 P-FIX／P-EXT 的 D；（四類偏離與三要件定義見 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`）
兩者皆無＝孤兒規則（CRITICAL）。

## 鏈末條件（交棒 `linear-create` 前）

`--cross` 達 0 CRITICAL／BLOCKER 後，**必須再跑一次 BFS 單文件 `--full`**（D2 DB 逐欄／D4 平台／D5 FoxPro 是 cross 沒有的維度），兩者皆過才進 `handoff-protocol.md` 的硬性停點。
同一鏈 `--cross` 超過兩輪＝修正棒在製造新缺口，停下回報使用者，不要第三輪。單文件 `--full`／`--recheck` 亦同：同一文件連續第三輪就停下回報。


## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| 無參數（兩者皆缺） | 先從對話上下文推斷最近提及或讀取的規格書路徑；若能確認則自動使用並告知用戶「偵測到：\<path\>，開始驗證」；若無法確認才提示用法並終止 |
| 文件路徑找不到 | 提示路徑錯誤，終止 |
| 唯讀 DB 查詢工具不可用 | Task 2 全部標記「未驗證 — 唯讀 DB 查詢工具不可用」，繼續其他 Task；報告最終結論自動降為 ⚠️ |
| Grep/Glob 找不到現有資源 | 標注「現有資源未找到」，不視為 CRITICAL，繼續 |

## Red Flags

**禁止捷徑**：標題在 ≠ 內容完整、必須用唯讀 DB 查詢工具查 DB 比對、必須查資料值、必須 Grep 搜尋現有 API/Entity、驗證規則逐一比對、必須追蹤完整資料流路徑。

## References

- [checklist-details.md](references/checklist-details.md) — 結構檢查／舊系統事件對應
- [data-flow-checklists.md](references/data-flow-checklists.md) — Task 2.1／2.2
- [info-flow-checklists.md](references/info-flow-checklists.md) — Task 3.1～3.4
- [cross-doc-checklists.md](references/cross-doc-checklists.md) — Task 8.2～8.4／8.6～8.8
- [param-source-consistency.md](references/param-source-consistency.md) — Task 8.9 掃描步驟
- [db-validation-queries.md](references/db-validation-queries.md) — DB 驗證 SQL 模板
- [existing-resources-check.md](references/existing-resources-check.md) — 現有資源盤點指令
- [cr-validation.md](references/cr-validation.md) — CR 交叉驗證規則／追溯矩陣
- [report-template.md](references/report-template.md) — 報告格式範本
- [index-and-size-checks.md](references/index-and-size-checks.md) — SPEC-INDEX／體積判準
- [analysis-standards.md](../../references/analysis-standards.md) — 業務領域分析標準
- [response-structure-standards.md](../../references/response-structure-standards.md) — Response 參照欄位巢狀結構
- [doc-boundaries.md](../../references/doc-boundaries.md) — 文件邊界與去重（產物 owner 矩陣）
