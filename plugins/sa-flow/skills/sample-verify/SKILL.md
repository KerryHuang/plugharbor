---
name: sample-verify
description: "對照實際 codebase 行為驗證規格的正確性與完整性：分組平行取樣原始碼、識別業務邏輯區塊、檢查行為規格的覆蓋度，彙整成落差報告。觸發：「驗證規格 vs 程式行為」「規格覆蓋度」「sample-verify」。"
argument-hint: "<規格路徑> [原始碼範圍] [--full]"
---

# Sample-Verify — 規格覆蓋度驗證

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

核心問題：**「這份規格有沒有漏掉程式實際在做的事？寫的那些又對不對？」**

**主 session 不讀原始碼。** 取樣由 `sa-flow:spec-sampler` 分組平行執行——
讀完整原始碼是大量素材，對「彙整結論、決定怎麼補規格」毫無用處卻會擠爆 context。
主 session 只做四件事：定範圍 → 分組 → 派工 → 判讀彙整。

> 與 `verifying-specs` 的分工：那支驗**規格內部**的正確性與跨文件一致性（規格 vs 規格）；
> 本 skill 驗**規格 vs 程式**。兩者不重疊。

## 輸入參數

```
$ARGUMENTS → <規格路徑> [原始碼範圍]
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `規格路徑` | 是 | 行為規格檔路徑；未給時終止並詢問 |
| `原始碼範圍` | 否 | 目錄或檔案清單；未給時由 Step 1 從規格反推。明確給範圍時該範圍走全量 |
| `--full` | 否 | 忽略錨點檔，整份重驗 |

## Step 0：讀實作錨點，決定全量或增量

讀規格所在功能目錄的 `analysis/impl-anchors/{規格檔名}.yml`（格式與判定細節見 [references/impl-anchors.md](references/impl-anchors.md)）。
這份檔記錄每條規則在程式哪裡執行，以及上一輪比對時各 repo 的 commit。

- **不存在**、帶 `--full`、或使用者明確給了原始碼範圍 → 全量，進 Step 1。
- **存在** → 增量：只取「錨點 commit 之後有變動的檔」＋上輪 `deferred` 的檔＋規格改過章節所涉規則的執行檔（規格有沒有改，比對錨點檔記的規格內容 hash，不看日期）。
  錨點 commit 已不存在（rebase、淺 clone）的 repo 改走全量。
  變動集合為空且規格沒改 → 回報「自 <commit> 以來無變動，錨點仍有效」並結束，**不派工**。

為什麼：沒有錨點時每輪都要整份重讀，規格是否過期也無從判斷；有錨點就只看真的動過的地方。
增量模式的 Step 1 只列變動集合，不再從規格整份反推。

## Step 1：定取樣範圍

從規格反推要讀哪些原始碼——**定向讀取**規格（`grep -n 'SPEC-INDEX v1'` → `grep -n "^## "` → `Read` 帶 offset/limit），
取出它宣稱涵蓋的端點、Handler、Entity、資料表，再 `Grep`／`Glob` 定位對應檔案。

**只列檔案路徑清單，不要開始讀內容**——讀是 agent 的事。

範圍過大（>30 支檔）時 `AskUserQuestion` 與使用者確認要不要收窄，
附「本次只驗 X 模組（推薦）」與「全部驗，會派 N 組」兩個選項。

## Step 2：分組（**現場分析，不要照抄範例**）

<law>
**分組方式必須依本次檔案的實際性質分析決定**，不得套用固定分組表——
每個案子的檔案性質不同，寫死的分組換一個案子就分錯。
</law>

分析步驟：

1. **列出每支檔的前置條件**：屬於哪個模組／聚合根、要對照規格的哪幾章
2. **前置相同者歸一組**——同一組共用同一批規格章節，agent 只需定向讀那幾章；
   跨組則各自讀各自的，不重複載入
3. **有副作用的單獨跑**——本 skill 全程唯讀，通常不適用；但若某支檔需要
   額外查 DB 或跑腳本才判得出可達性，把它單獨一組

**組太細會變慢**：每組都有固定啟動成本（定向讀規格章節、建立對照）。
一組只有一支檔通常不值得切，3~6 支是常見的合理區間。

> 以下僅供理解判準，**不要照抄**：某次驗證把「訂單寫入路徑 4 支」歸一組
> （共用規格 §6~§8）、「查詢與投影 5 支」歸另一組（共用 §4），
> 因為兩組要對照的規格章節完全不重疊。換一份規格，這個分法就不成立。

## Step 3：平行派工

同一批次**一次送出多個 tool call**，不要逐組序列跑：

```
subagent_type: "sa-flow:spec-sampler"
prompt: |
  spec_path: {規格絕對路徑}
  files:
    - {本組檔案絕對路徑}
    - ...
  group_name: {組別標籤}
```

各組**彼此獨立、無共用狀態**——不必互相告知，也沒有匯流順序要求。
全部回報齊了才進 Step 4。

## Step 4：彙整與判讀

各組回報的是**結論與定位**（`檔案:行號` ＋ 摘要），不是原始碼。彙整成一份落差報告：

| 區塊 | 內容 |
|------|------|
| 結論 | 一句話：規格能不能直接拿去開發／要補多少 |
| 覆蓋度 | 各組統計加總（SCB 總數、各分類筆數與比率） |
| MISSING | 業務邏輯不在規格——**依影響排序**，每條標建議落點（哪份文件哪一章） |
| INACCURATE | 規格描述有誤——規格原句 vs 實際行為，標建議修正 |
| EDGE CASES | 已載明規則的未涵蓋分支 |
| DEAD CODE | 到不了的程式碼——**只提出，不主動清除** |
| UNCERTAIN | 程式看不出意圖、無法斷言的區塊——**不升格為 MISSING，不替它編規則**，列給使用者判斷 |

<law>
**agent 的量化斷言要複核。** 覆蓋率、SCB 數、「規格實為 VR-001~024」這類數字，
採信前自己抽驗一次——實測曾出現 agent 回報範圍與實際差一筆的情形。
</law>

**寫回錨點檔（每輪必做，不論報告落不落檔）**：依各組回報的「錨點」表與 `UNCERTAIN`，
更新 `analysis/impl-anchors/{規格檔名}.yml`——`_meta.repos` 記本輪各 repo `git -C <repo> rev-parse HEAD`、
`spec_blob` 記規格**最終版**的內容 hash（本輪有修規格就等修完再算，否則下一輪會把自己的修訂當成規格變動），
本輪重驗的規則覆寫、其餘保留。寫完跑 YAML 解析，並逐列確認 `enforced` 指到存在的檔、沒有絕對路徑，
才回報「解析通過」——解析過不代表內容對（實測：shell heredoc 把 `$VAR:方法名` 當修飾子展開，YAML 仍可解析）。規則與格式見 [references/impl-anchors.md](references/impl-anchors.md)。
錨點只記「實際落在哪」，**不寫進規格正文**——規格技術中立，不得出現類別或方法名。

判讀時區分兩種 MISSING：**該補進規格的業務邏輯**，與**本來就不該進規格的實作細節**
（依 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md` 的 owner 矩陣）。
agent 只負責找出「程式有做但規格沒寫」，**哪些值得寫進規格是主 session 的判斷**。

## 收尾條件

全部成立才算完成：

1. `files` 全部分派完畢，沒有檔案落在任何一組之外
2. 每組回報都收到（失敗的組已重派或已在報告標明未涵蓋）
3. 落差報告含結論、覆蓋度統計、五類發現（含 UNCERTAIN），並註明本輪是全量或增量（增量時附基準 commit）
4. 每條 MISSING／INACCURATE 都標了建議落點（哪份文件、哪一章）
5. `analysis/impl-anchors/{規格檔名}.yml` 已寫回且解析通過
6. 已明確告知使用者下一步：補規格走 `sa-flow:requirement --change`／
   `sa-flow:specify-backend --change`，或先開票

**報告落檔位置**由使用者決定（預設不落檔，只在對話輸出）——
這是分析中間產物，不是交付文件。要落檔時放功能目錄的 `analysis/`。

## Red Flags

| 症狀 | 正解 |
|------|------|
| 主 session 自己讀原始碼 | 派 `spec-sampler`。讀碼進主 context ＝ 隔離失效 |
| 逐組序列派工 | 各組無共用狀態，同一批次一次送出 |
| 在 SKILL.md 寫死分組表 | 現場依檔案性質分析，寫死換個案子就分錯 |
| 一支檔一組 | 啟動成本大於效益，3~6 支較合理 |
| 直接採信 agent 的覆蓋率數字 | 量化斷言自己抽驗一次 |
| 把 DEAD_CODE 順手刪掉 | 只提出。既有 dead code 不動 |
| 把所有 MISSING 都當成要補進規格 | 先過 `doc-boundaries.md` 的 owner 矩陣 |
| 把方法名、檔名寫進規格正文當錨點 | 錨點只進 `analysis/impl-anchors/{規格檔名}.yml`，規格維持技術中立 |
| 有錨點檔還每輪全量重驗 | 走 Step 0 增量；要全量請明確帶 `--full` |

## References

- `${CLAUDE_PLUGIN_ROOT}/agents/spec-sampler.md` — 取樣 agent（SCB 定義與分類規則在其定義內）
- `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md` — 文件邊界與 owner 矩陣
- [references/impl-anchors.md](references/impl-anchors.md) — 實作錨點檔格式、增量判定、寫回規則
