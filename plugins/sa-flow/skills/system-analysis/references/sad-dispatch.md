# SAD 撰寫派工樣板

`system-analysis` Step 10 的 `spec-writer` 派工 prompt。
派工**前**必須完成 8.5 確認門（使用者已選定方案）、8.6 決策落檔、Step 9 疑問點清查。

`{}` 為呼叫端填入值；所有路徑一律展開成**絕對路徑**。

> 📌 **`_sad-draft.md` 就是 brief 的載體**——8.5 確認門已把步驟 4-8 的分析結果寫進去，
> 不要再重打一份綱要。主 session 寫的是**分析摘要**（短、是思考的產物），
> agent 依它生成正文（長）。這個分工是本 skill context 隔離的核心。

```
subagent_type: "sa-flow:spec-writer"
prompt: |
  doc_type: SAD
  out_path: {功能目錄}/{功能名稱}_系統分析文件.md
  template: ${CLAUDE_PLUGIN_ROOT}/templates/sad.md
  boundary_row: {spec-dedup-and-budget.md「各文件套用值」表的 **SAD 欄**（表頭是 `項目｜FRD｜SAD｜BFS｜FFS`，要抽的是那一**欄**跨全部項目列）}
  evidence:
    - {功能目錄}/analysis/_sad-draft.md        # ← 主要輸入：步驟 4-8 的分析結果
    - {FRD 路徑}                               # §2 使用者故事、§3 業務流程、§5 業務規則
    - {功能目錄}/analysis/reuse-scan.yml       # A 路勘察：既有路由與 Handler 對照
    - {功能目錄}/analysis/db-analysis.yml      # B 路勘察：欄位／型別／FK
    - {功能目錄}/analysis/ui-survey.md         # C 路勘察（若有）
    - {功能目錄}/analysis/consultant-notes.md  # 顧問桌裁示（若有）
  decisions: {功能目錄}/decisions.md ＋ 本階段編號 {D-0xx…}
  feature: {功能名稱}／{模組}／{功能目錄}
  brief: |
    以 _sad-draft.md 為主體展開成 SAD 正文。各章重點：
    §2.1 泳道工作流（必畫）＋角色互動表；有狀態機時 §2.3 完整狀態機
      （**含非法轉換與並發衝突**，非僅畫正常路徑）
    §3.1 資訊流向圖（必畫，每個處理節點掛 BR 編號）＋處理明細表
    §4.2 ER 圖（必畫）＋資料表清單（標讀/寫）＋CRUD 對應表＋Migration 預判清單
    §5 一張能力結論表（能力｜既有可用／需擴充／需新建｜備註），明細 ref reuse-scan.yml
      ＋ Light API 需求清單（參照實體／已存在／需新建）
    §6.1 只列**有分歧**的方案取捨（實作優先順序由 RD 決定，不寫）
      ＋推薦方案的初步 API 端點建議表（HTTP 方法｜路由｜對應 US｜說明）
    §6.5 NFR → 約束與風險（FRD §6 每項：目標值｜已知現況｜陷阱；**不寫手段**，手段進 TD）
    §6.6 邊界與例外清單（規則 >8 條時**必附決策樹圖**）
    功能代碼判定（Step 7.5 有產出時）：沿用／新編＋撞碼驗證結果／不需代碼＋理由
    確認門已選定的方案：{方案名稱與一句理由}
  mode: new
  extra_checks: |
    ER｜ER 圖**禁用 `PK_FK` 複合角色**（Mermaid 不支援）——
       正確寫法 `uniqueidentifier EntityId PK "FK to OtherTable"`｜
       驗法：grep -n 'PK_FK' 應為 0
    SM｜有狀態機時，§2.3 狀態圖**必須標示非法轉換與並發衝突**——
       只畫正常路徑不算完成（CRITICAL 項，是 §6.6 邊界分析與 BFS §8.4 的依據）
```

## 為什麼 ER／SM 要放 `extra_checks`

兩者都是「寫錯了下游會照著錯下去」的類型：

- **ER**：Mermaid 不支援 `PK_FK`，圖直接渲染失敗——但 agent 不會自己去渲染，只能靠 grep 擋
- **SM**：狀態機只畫正常路徑，`dev-readiness` 的 B4 就會整批退回來，等於這一棒白做


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
