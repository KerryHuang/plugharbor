---
name: requirement
description: "依功能描述撰寫功能需求文件（FRD），或以 --change 產出 CR-FRD；資深 PM 視角。觸發：「寫 FRD」「需求文件」。"
argument-hint: "[--change] {需求描述}"
---

# 撰寫功能需求文件

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

以**資深產品經理（PM，豐富產業系統經驗）**角色，從使用者的自然語言描述撰寫結構化的功能需求文件，
主動識別隱含需求和邊界條件，把模糊業務需求轉化為清晰、可執行的文件。

## 模式說明

| 模式 | 觸發方式 | 適用情境 | 產出範本 |
|------|---------|---------|---------|
| **標準模式** | `/sa-flow:requirement {描述}` | 全新功能 | `frd.md` 範本 → `{功能名稱}_需求文件.md` |
| **調整模式** | `/sa-flow:requirement --change {ticket} {描述}` | 原功能調整 | 更新主文件 changelog + Linear 票 |

## 輸入參數

```
$ARGUMENTS → [--change] {需求描述}
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `--change` | 否 | 指定調整模式（CR-FRD），省略則為標準模式（FRD） |
| `{需求描述}` | 是 | 自然語言描述，空白則提示輸入後終止 |

## 前置規範

依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`（核心原則：不猜測、Docs 同步、Graphify 查詢〔選配〕）。

---

## 標準模式執行流程

> 適用：全新功能，從零開始撰寫 FRD

### 0. 前置文件檢查

依優先順序搜尋前置探索文件作為需求分析輸入：**①** `sa-flow:explore` 探索摘要（`{docs-root}/**/*_探索摘要.md`）
**②** `superpowers:brainstorming` 設計文件（`{docs-root}/superpowers/specs/` 或 `docs/specs/` 下
`*-design.md`）。找到任一 → 讀取並沿用，繼續下一步；兩者皆未找到 →
`AskUserQuestion`：`先執行 sa-flow:explore（需求大致明確）` / `先執行 superpowers:brainstorming（需求模糊）` /
`需求已明確，直接撰寫 FRD`。選「直接撰寫」才繼續，選其他則終止等待使用者完成。

> 讀取既有規格文件（探索摘要、設計文件、舊版 FRD）一律定向讀取所需章節，不整檔載入。完整 pipeline 見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`。

### 0.5 畫面對焦素材（選配，含 UI 功能適用）

功能含 UI 畫面時，先確認同目錄是否已有 PO／使用者對焦過的畫面素材（線框稿、設計稿、可點原型，
形式不拘）：

- **有** → 讀取其「已定案」結論，直接作為 §2／§4 的輸入證據，
  **也是 FFS §2 完整欄位表的主要取材來源**——素材中的欄位一併記入 `analysis/ui-survey.md`。
  素材上仍未決的「待 PO 確認」項，先清問完畢再往下，不得靜默帶進 FRD。
- **沒有** → 不阻擋；UI 相關疑點記入 FRD §8 開放議題，供 `verifying-specs` 追蹤。
- **豁免**：純後端／排程／資料修正功能。

### 1. 需求分析

> **Step 0 已找到探索摘要／設計文件時，本步驟的五項直接沿用該文件，不重新提取**——只確認「摘要產出後需求有無變動」即可。

以 PM 的專業視角分析使用者輸入，提取：**功能名稱**（2-6 字短名稱）、**所屬模組**、**需求類型**
（新功能／功能調整／系統整合／資料查詢）、**業務痛點**（目前問題或改善動機）、**影響範圍**（角色／
系統／流程）。**若需求描述不夠明確**，依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`「互動
詢問規範」釐清：每題必附建議選項；**答案會改變後續題目者逐題問**（如「新功能 vs 既有調整」），
**彼此獨立的補充題批次問**（角色、整合對象、資料量級等）。

### 1.5 視覺素材收集

依 `references/visual-guide.md`（§1.5 段落）執行。

### 2. 背景調查（**三路平行派工**）

**主 session 不自己掃 codebase、不自己查 DB、不自己開瀏覽器。** 三路用不同工具、寫不同檔，
彼此無共用狀態 → **同一批次一次送出**，不要序列跑。

| 路 | agent | 蒐什麼 | 寫哪個檔 | 觸發 |
|---|---|---|---|---|
| **A** | `sa-flow:scout` | 既有規格書／Entity／Controller／Handler＋舊系統業務規則 | `analysis/background-scan.yml` | 一律 |
| **B** | `sa-flow:scout`（DB 結構模式） | 資料表結構 | `analysis/db-analysis.yml` | 需求涉及既有資料表，且有唯讀 DB 查詢工具 |
| **C** | `sa-flow:browser-surveyor` | 現有畫面與操作動線 | `analysis/ui-survey.md` | 需求涉及既有功能，使用者提供 URL，且有瀏覽器工具 |

**完整派工 prompt、觸發判準、失敗處置** → `references/background-dispatch.md`
（派工前讀該檔，`{功能目錄}` 一律展開成絕對路徑）。C 路啟動前先確認 `ui-survey.md` 是否已涵蓋——
已涵蓋就直接讀用，**不重問 URL、不重跑勘察**；未涵蓋才 `AskUserQuestion`（`提供系統 URL 做現有畫面
分析（推薦）` / `跳過，僅依 codebase/docs 分析`），選提供後以文字詢問 URL 再派。

<law>
**FRD 階段的勘察刻意比 SAD 淺**——只回答「有沒有類似的東西、涉及哪些表、舊系統怎麼做」，完整重用
盤點是 `system-analysis` Step 3 的事，派工時把範圍講清楚。**勘察結果是現況擷取不是需求**，寫進 FRD
前須依 `${CLAUDE_PLUGIN_ROOT}/references/ui-analysis-guide.md` 檔頭對照表轉譯，不得整段複製。
**「這功能需新建」不能只靠 A 路回報**——說新建前必須另查 Graphify 圖譜與 Linear 既有票（可用者；同義文件常
散在不同模組目錄、檔名不同義，grep 檔名會漏）。
</law>

三路全部回報齊了才進 Step 3；任一路失敗都不阻斷 FRD 撰寫，處置見 background-dispatch.md「匯流與失敗
處置」。**不要 Read 截圖進 context。**

### 3. 確定儲存位置

**先讀 `analysis/_context.yml`**（依 `shared-preludes.md` Step 0.8）取功能目錄；未登記才探索專案既有目錄慣例，
確定後**寫入 `_context.yml`**（功能名稱、模組、功能目錄、本文件路徑），供下游直接沿用。
若專案無既有慣例，預設 `{docs-root}/{模組名稱}/{功能名稱}/{功能名稱}_需求文件.md`（模組名取自既有第一階目錄，禁止自創）。

### 4. 載入範本

讀取 `${CLAUDE_PLUGIN_ROOT}/templates/frd.md`（骨架，含撰寫須知）；畫面／欄位規格寫法不確定時按需讀 `templates/examples/frd-sad-guides.md`，圖與算例寫法讀 `templates/examples/diagrams-and-worked-examples.md`，不預先全載。

### 5. FRD 內容規劃（**產 brief，不寫正文**）

正文由 `spec-writer` 在 Step 8 產出。本步驟的產物是**派工用的內容綱要**——
各章要寫什麼、有哪些 US／BR／VR 編號、每條規則的依據是什麼。
**主 session 寫綱要（短，是思考的產物），agent 寫正文（長）**——一旦自己寫 30KB 正文，
後面的分流判定與交棒決策就沒有餘裕了。

> 📎 **文件邊界**：先讀 `${CLAUDE_PLUGIN_ROOT}/references/spec-dedup-and-budget.md`「各文件套用值」的
> **FRD 列**；判不出才查 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md` 對應列。FRD 是「業務
> 狀態語意、業務流程圖、畫面清單與操作表、業務層驗證規則、業務算例」的 owner；**不寫**系統互動、API、
> 資料表結構（交由 SAD/BFS），也**不寫完整畫面欄位表**（owner 是 FFS §2）。下游 ref 本文件的編號要
> 穩定（US/VR/BR 下游沿用；**US-XX 是全鏈追溯鍵**，§2.1 角色欄必填）。

**各章內容要點** → [frd-dispatch.md](references/frd-dispatch.md) 的 `brief` 段（不在此重列，兩處必漂移）。

### 6. PM 專業加值

**先看 `_context.yml` 的 `chain_origin`**（缺欄但功能目錄有 `*_FoxPro分析報告.md` → 補寫 `foxpro`）。（四類偏離與三要件定義見 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`）
**`foxpro` ＝ 舊系統移植鏈**：FRD 以舊系統既有行為為主，本節的「隱含需求」與「業務規則挖掘」**不做**——
只寫舊系統既有行為（可追溯至 FoxPro 分析報告編號）與既有 bug 修正；新增功能只進 FRD 獨立的「偏離候選（預設不做）」節，不主動提、不散進正文。
原因：與舊系統不一致時使用者反彈遠大於「舊做法」，延伸問題會讓決策膨脹。其餘加值（BDD 例子、風險表）照做。

一般鏈：作為資深 PM，必須主動補充：**隱含需求**（權限控管、資料一致性、邊界條件、效能考量）；**BDD 例子思維**——每條關鍵 BR 至少
推導一個正例＋一個反例，落入對應 US 的 §2.2 AC-n，不允許只有規則敘述而無例子的 BR；**業務規則挖掘**
——推導隱含規則標記 `[推論]` 並說明依據，不確定處立即詢問使用者（附建議方案）；**風險評估**——文件
末尾加風險表（描述／影響程度／發生機率／緩解措施）。

### 6.5 顧問桌諮詢（條件式，**預設不開**）

顧問桌主場在 `system-analysis`；FRD 階段僅命中 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md`「FRD 例外」三條之一（全新業務概念／業務邊界未定／聚合根歸屬爭議）時才開，編制與流程依該檔，結論落 `analysis/consultant-notes.md`。未命中 → 直接進 Step 6.7。

### 6.7 決策紀錄落檔（寫檔前必做）

把本次**已拍板**的決策，依 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`（append 協定與欄位
規則的唯一定義處）append 到 `{功能目錄}/decisions.md`（全鏈唯一決策落點，FRD 通常是鏈上第一棒，
檔案不存在就建檔、不視為缺陷；`階段` 填 `FRD`）。**不新增分析步驟、不多問任何問題**——決策來源逐處
掃：Step 0.5 對焦素材「待 PO 確認」清單的裁示；Step 6 標 `[推論]` 後**經使用者確認或推翻**的規則（未確認
屬待澄清，不記）；Step 6.5 顧問桌裁示（`拍板` 填 `顧問`）。FRD `§D` 只列本階段編號與一句結論。

### 6.8 去重與體積（**交給 agent，此處只備輸入**）

去重閘、SPEC-INDEX、必畫圖檢查、正文預算（30KB）與超標拆附錄，全部由 `spec-writer` 在 Step 8 自檢
（其 L2~L5 ＋ 正文預算 `<law>`）。主 session 只做一件事：把 `${CLAUDE_PLUGIN_ROOT}/references/spec-dedup-and-budget.md`
「各文件套用值」表的 **FRD 欄**（是欄不是列，表頭 `項目｜FRD｜SAD｜BFS｜FFS`）取出，Step 8 當
`boundary_row` 傳給 agent。去重判準寫進 brief：**不同視角的圖不算重複**。

### 7. 疑問點總清查（寫文件前必做）

逐一檢查：角色、流程順序、資料來源與格式、規則判斷條件、邊界例外、In/Out of Scope。
仍有疑問 → 回步驟 1-2 重新搜尋或詢問使用者；**多個疑問依「互動詢問規範」逐題問**。全部解決後才進步驟 8。

### 8. 派 `spec-writer` 撰寫

完整派工 prompt → [frd-dispatch.md](references/frd-dispatch.md)。
派工前確認 Step 5~7 都已完成——agent 拿到的必須是已定案的內容。

`extra_checks` 帶三條 FRD 專屬硬閘：

<law>
**BDD**｜每條關鍵 BR 至少一個正例＋一個反例，落入對應 US 的 §2.2 AC-n。
**INF**｜推導出的隱含規則必須標 `[推論]` 並說明依據——**FRD 最容易失真的地方**：
PM 的合理推測一旦寫成肯定句，下游三份文件都會照著實作。
**NUM**｜§2 驗收條件直接代入數字，不寫「數量超過上限時」這種抽象敘述。
</law>

### 9. 判讀複核（**只做 agent 做不到的**）

L9/L10/L14/L15/L16 已由 agent 的 L1~L5 自檢涵蓋，**不要重跑**。只做三件 agent 做不到的：

- **A 與探索摘要／對焦素材「已定案」清單對照**——定案的欄位與流程有沒有被寫歪
- **B 逐條看 `[推論]` 標對了沒**——親口說的被誤標成推論，下游會重問一次
- **C 抽驗 agent 自檢**（見下）

<law>
**不要照單全收「自檢全過」**（理由與通用盲區見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §四）。
本文件的抽驗重點：BDD 至少抽 2~3 條 BR 自己看對應 AC——
「有寫例子」跟「有正例也有反例」是兩回事。
</law>

**不跑驗證迴圈**：正確性與跨文件一致性由鏈末 `sa-flow:verifying-specs` 一次驗完。
處理完待補清單與證據缺口即進 9.5。CR 例外見 `${CLAUDE_PLUGIN_ROOT}/references/auto-verification-loop.md`。

### 9.5 BDD .feature 衍生（可選，條件觸發）

FRD 通過驗證後，若功能有**業務規則分支或狀態轉換**（純 CRUD 查詢、單一 AC 的功能豁免），用
`AskUserQuestion` 詢問是否衍生 Gherkin `.feature` 檔。產出**必須**依 `references/bdd-feature-guide.md`：
FRD §2.2 為唯一權威、.feature 是機械轉譯、`# language: zh-TW`、單檔置於 `{docs-root}/{模組}/{功能}/features/`、
tag 追溯（`@US-xx @BR-xxx @VR-xxx`）。

### 9.8 規格鏈分流判定（寫檔後、交棒前必做）

依 `${CLAUDE_PLUGIN_ROOT}/references/chain-profile.md` 逐條過五條判準，決定本功能走 **standard**
還是 **lite**（lite 跳過 `system-analysis`，其必要產物改由 `specify-backend` 承接）。**有疑慮的條目
點名寫出，交確認時由 PO 判，不以「有疑慮」帶過；票面產出物列了 SAD 不算指定 standard**。執行：①文字列出五條判定結果與依據 ②`AskUserQuestion` 確認（推薦項置首，description
寫明省掉什麼、風險是什麼）③結果寫入 `analysis/_context.yml` 的 `chain_profile`／`profile_reason`／
`profile_decided_at`。分流確認後 append 一列到 `decisions.md`（決策＝「規格鏈分流」、選定＝
`standard`／`lite`、依據＝命中的判準、拍板＝`PO`、階段＝`FRD`），FRD `§D` 列該編號——這一列是
`specify-backend` Step 0.45 分流確認的**唯一書面依據**。

### 10. 報告完成

依 `references/completion-reports.md`（標準模式段落）輸出完成報告。

**下一步**：依 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 判定——續行條件全滿足
（零阻塞／零待確認／無未答 OI／已落檔）→ 依 Step 9.8 的分流結果**自動續跑**：
`chain_profile=standard` → `sa-flow:system-analysis {功能名稱}`；
`chain_profile=lite` → **`sa-flow:specify-backend {功能描述}`**（跳過 SAD）。
有未答開放議題或 PO 未確認的對焦事項 → 停下說明。完整流程見 `${CLAUDE_PLUGIN_ROOT}/references/upstream-workflow.md`。

## 調整模式執行流程

> 適用：原功能的調整，in-place 更新主文件並記錄 changelog

### A0. Docs 同步檢查

依 `shared-preludes.md` Step 0.5：docs 在獨立 repo 時先 pull，確保文件目錄是最新狀態。

### A0.5 Ticket 守門

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 0）執行。

### A1. 識別調整內容

分析使用者描述，提取功能名稱（對應哪個既有功能）、所屬模組、變更類型（新增使用者故事／修改業務規則／
調整欄位規格／多種混合）、Ticket 編號（已由 Step 0 確認）。

### A2. 主文件查找與 Codebase 反推

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 1）搜尋 FRD 主文件。
找不到時：FRD 掃描範圍 → 舊版 CR 需求文件、git log、domain entity；使用 `${CLAUDE_PLUGIN_ROOT}/templates/frd.md` 範本撰寫 v1.0。

### A2.5 現有畫面分析（強烈建議）

- **`analysis/ui-survey.md` 已涵蓋且未過期** → 直接讀用
- **未涵蓋** → `AskUserQuestion`（`提供 URL 做現有畫面分析（推薦：CR 必先看現況）` / `跳過`）；
  選提供 → 以文字詢問 URL，**派 `sa-flow:browser-surveyor`**（樣板見
  `references/background-dispatch.md` C 路），
  它落檔 `analysis/ui-survey.md`
- **勘察失敗** → 依 agent 回報處置，不阻斷；標「未取得畫面證據」續行

> CR 尤其要先看現況——改規格前先勘察已完工的實際行為，勿文件互抄。

### A3. 分析影響範圍與確認

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 2）分析。

### A4. 更新主文件與 Changelog

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 3）執行 in-place 更新（修訂是取代不是追加）。若功能目錄存在 `features/*.feature`，更新 FRD §2.2 後依 `references/bdd-feature-guide.md`「CR 同步」節**整檔覆蓋重轉譯**（不做差異式手改）。

### A5. 更新 Linear 票

依 `${CLAUDE_PLUGIN_ROOT}/references/cr-update-flow.md`（Step 4）更新票 description。

### A6. 品質檢查清單（調整模式）

依 `references/quality-checklists.md`（調整模式段落）逐項自我驗證。

### A7. 報告完成（調整模式）

依 `references/completion-reports.md`（調整模式段落）輸出完成報告。完整開發流程詳見 `${CLAUDE_PLUGIN_ROOT}/references/upstream-workflow.md`。

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| `{需求描述}` 為空 | 提示輸入描述，終止 |
| 範本檔案找不到 | 提示範本路徑錯誤，終止 |
| 主文件找不到（調整模式） | 從 codebase 反推建立 v1.0，再套用 CR 變更 |
