# BFS 撰寫派工樣板

`specify-backend` Step 5.4 的 `spec-writer` 派工 prompt。
派工**前**必須完成 5.1 邊界落實對照、5.2 疑問點總清查、5.3 決策落檔。

`{}` 為呼叫端填入值；所有路徑一律展開成**絕對路徑**。

```
subagent_type: "sa-flow:spec-writer"
prompt: |
  doc_type: BFS
  out_path: {功能目錄}/{功能名稱}_後端功能規格書.md
  template: ${CLAUDE_PLUGIN_ROOT}/templates/bfs.md
  boundary_row: {spec-dedup-and-budget.md「各文件套用值」表的 **BFS 欄**（表頭是 `項目｜FRD｜SAD｜BFS｜FFS`，要抽的是那一**欄**跨全部項目列）}
  evidence:
    - {FRD 路徑}                              # §4 畫面設計、§5 業務規則
    - {SAD 路徑}                              # §6.6 邊界、§5 重用結論（lite 鏈無此項）
    - {功能目錄}/analysis/db-analysis.yml     # 欄位型別／長度／可空性
    - {功能目錄}/analysis/reuse-scan.yml      # 既有路由與 Handler 對照
  decisions: {功能目錄}/decisions.md ＋ 本階段編號 {D-0xx…}
  feature: {功能名稱}／{模組}／{功能目錄}
  brief: |
    §A 重用結論：逐項標「既有可用／需擴充／需新建」，標的是**能力**不是類別
      （寫「品項查詢能力：既有可用」，不寫「ItemQueryHandler：延用」）；
      類別名／檔案路徑／行號一律留在 reuse-scan.yml，不進正文
    §5 欄位定義表加註來源連線與查詢日期；型別用中性寫法（文字(N)／整數／日期／唯一識別碼）
    §6 端點契約：路由、method、狀態碼、Request/Response 欄位與型別
    §6.0 列表／報表 DoR（條件式）：{4.3 的解析結果}
    §7 VR/BR、§8 例外、§8.4 並發 ← 5.1 邊界落實對照的落點：{逐項}
    §2.5 核心計算／歸集（有計算時必填）：匯流圖 ＋ 算例表
      （數值型給數字；條件判定型給條件組合→結果，不要假設一定是算術）
      （數字取自具代表性的 Staging 資料並註來源；業務算例已在 FRD §5.3 者 ref 之）
    §M Migration 規格（條件式）：§M.1 資料模型契約是 SA 定案的契約；
      §M.3 實作做法（DB 先行或 code 先行、migration 寫法、索引、分批）寫 decisions.md TD 由 Dev 定
    功能代碼段落（條件式）：代碼與描述、來源、seed 方式、授權端影響（不變也要明寫理由）
    內容規範必讀：
      ${CLAUDE_PLUGIN_ROOT}/skills/specify-backend/references/naming-conventions.md
      ${CLAUDE_PLUGIN_ROOT}/skills/specify-backend/references/content-rules.md
      ${CLAUDE_PLUGIN_ROOT}/references/response-structure-standards.md
      ${CLAUDE_PLUGIN_ROOT}/references/sort-order-standards.md
  mode: new
  extra_checks: |
    TN｜**技術中立**（plugin <law>，最高優先）｜全文不得指定實作技術——
       framework／library／ORM／元件／設計模式／類別命名，**以及手段層**：
       快取、鎖、佇列、儲存位置、併發原語、重試與補償做法、索引策略。
       手段層問題一律寫成 decisions.md 的 **TD 技術決策留置**（約束＋現況＋陷阱），
       **不得在規格正文定案**。驗法：grep -nE '{ORM／快取／佇列／排程等技術名詞，依專案技術棧列舉}|Repository|
       Handler|快取|分散式鎖|佇列|索引策略|重試' 逐處判斷是契約還是手段；
       另查 §5.3 不得有「Entity 屬性」欄、§5.4 不得有索引表（既有索引在 reuse-scan.yml，新需求進 TD）
    LINT｜依 ${CLAUDE_PLUGIN_ROOT}/skills/specify-backend/references/spec-lint.md
       L1~L8 逐項自檢（禁「沿用既有 DTO」籠統描述、端點命名風格、TBD 清零、
       章節矛盾、模糊條件、路由存在性、列表/報表 DoR、API 回應契約完整性）
```

## 為什麼技術中立要放 `extra_checks` 而非 brief

brief 是「寫什麼」，`extra_checks` 是「不通過就不算完成」。技術中立是 plugin 的
`<law>`（見 plugin 的 `CLAUDE.md`），越線的代價是 Dev 照著規格實作了 SA 無權決定的手段，
且完工回寫時無從分辨哪些是契約、哪些是當初順手寫的建議。屬硬閘，不是撰寫偏好。


---

## ⚠ 派工前必做：確認引用的章節實際存在

<law>
**章號是變數不是常數。** 每份上游文件的章節編號都不同——實測：
某份 BFS 的 **§6 是「排程／背景作業」而 API 在 §5**、**§7 是「讀寫元件規劃」而非驗證規則**；
某份 SAD **根本沒有 §6.6**，全文也找不到 B1~B13 那套邊界編號。

照樣板字面填「ref BFS §7 同編號 VR」，agent 會 ref 到錯的章；
指向不存在的章節，它**既無法對照也無法回報未落實**——只能自己猜，那正是派工要避免的。
</law>

派工前逐項驗：

```bash
grep -n "^## " {BFS 絕對路徑}    # API 章、驗證規則章的實際編號
grep -n "^## " {SAD 絕對路徑}    # 邊界清單章是否存在
grep -n "^## " {FRD 絕對路徑}    # 畫面設計章、業務規則章
```

**brief 裡一律寫「語意 ＋ 實際章號」**：

- ✅ `ref BFS 的驗證規則章（本份為 §4.3 PR-01~PR-06）`
- ❌ `ref BFS §7 同編號 VR`

**另外掃一次編號引用**（避免改編號讓既有交叉引用靜默斷掉）：

```bash
grep -rn "FFS-TC-\|BFS-VR-\|FRD-BR-\|-TC-[0-9]\|-VR-[0-9]" {功能目錄}
```

同目錄有文件引用了本文件的編號 → **brief 裡明說用哪一套**（遷就既有，不要照範本另起）。

**引用的章節不存在時**：不要照樣板填。改寫成實際可依循的指示
（如「本功能 SAD 無邊界清單章，§4 依 FRD §5.2 VR 落實」），或先補做該分析再派工。
