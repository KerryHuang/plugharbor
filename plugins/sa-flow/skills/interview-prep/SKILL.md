---
name: interview-prep
description: "正式訪談前後準備：把多場會議／訪談素材彙整成已知／未知盤點，或為指定受訪者產出需求訪談大綱；每條標已確認／待確認／推測並附出處。觸發：「需求彙整」「訪談大綱」「下一輪要問什麼」。"
argument-hint: "[素材路徑…] 或 [受訪者／主題]"
---

# 需求訪談準備（interview-prep）

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

進 `explore`／FRD 之前的準備工作：把零碎素材收斂成**已知與未知的盤點**，並把未知轉成**問得出東西的訪談題目**。

**不做**：單場會議記錄（→ `meeting-minutes`）、回饋分類開票（→ `issue-triage`）、六維需求收斂（→ `explore`）、訪談演練角色扮演（→ 專案本地 `requirement-interview-roleplay`，有裝才提）。

> 核心原則 / 前置步驟：依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`（不猜測、先推導再詢問、互動詢問規範）。

## 共用紅線（兩模式一體適用）

依 `${CLAUDE_PLUGIN_ROOT}/skills/interview-prep/references/evidence-labels.md`：

- **【已確認】必附出處**（來源檔／場次＋原句片段）。指不出是誰在哪句話講的 → **不得標已確認**，降級處理。
- **【待確認】**＝資料不足、需再向人確認。
- **【可能推測】保守產出**——只有在原始資料出現**明顯斷點**時才推（提到某流程卻沒說誰負責、提到某狀態卻沒說怎麼結束），每條必寫**推測依據＝原文哪一句**，且**必須對應到一個訪談問題**；推不出依據就不推。集中放段末，不與已確認條目混排。
- **解法 ≠ 需求**：受訪者講的是解法（「要一個按鈕」）就照錄原話，另立一條「背後需求待確認」，不得逕自寫成需求。
- 標示與 `issue-triage` 的信心度對齊：【已確認】≈ Confirmed、【待確認】≈ 待實機、【可能推測】≈ Likely（但門檻更嚴）。

## 0. 選模式

先從輸入推導（有素材路徑＝A，有受訪者對象＝B），推不出才用 `AskUserQuestion` 問：

| 模式 | 何時用 | 輸入 | 產出 |
|------|--------|------|------|
| **A 資料彙整** | 手上一堆零碎會議／訪談資料，要盤已知未知 | 會議記錄路徑／逐字稿／貼入筆記 | 五區塊彙整 ＋ 下一輪優先確認 Top 5 |
| **B 訪談大綱** | 要去訪談某位利害關係人 | 專案背景／目標／已知限制／受訪者 | 缺口檢查 ＋ A~F 六段大綱 ＋ 30 分鐘 8~10 題 |

**A → B 串接**：本 session 或既有檔已有 A 產出時，直接拿它當 B 的輸入（區塊 4 缺口與 Top 5 就是大綱骨幹），**不重問使用者背景與限制**。

## 模式 A：資料彙整

1. **收來源**（三種可混用）：**本機檔案**（路徑，可多份／glob）／**貼入文字**／**Fireflies 逐字稿**（選配，見下方 §A.1a）。逐份記來源代號（`M1`、`M2`…）與日期，供出處引用；Fireflies 場次記成 `M2 = Fireflies「{title}」{date}`。
2. **拆條標籤**：拆成離散事實條目，逐條標三級標示與出處。原文口語改寫成清楚句式，但**只改寫不擴充**。
3. **五區塊歸位**：依 `${CLAUDE_PLUGIN_ROOT}/skills/interview-prep/references/synthesis-format.md` 填入範本 `${CLAUDE_PLUGIN_ROOT}/templates/requirement-synthesis.md` 的五區塊。
4. **矛盾與缺口偵測**：跨場同主題說法不一致 → 進區塊 4，**兩方出處與日期都列**，不以「後面那場為準」自行定案。
5. **Top 5**：依 synthesis-format §排序準則挑出最值得優先確認的 5 題，寫明「為何優先」與「該問誰」。
6. **落檔**：屬既有模組 → `{docs-root}/{模組}/{功能}/{名稱}_需求彙整.md`（模組名取自 `{docs-root}` 既有第一階目錄，**不得自創**）。不屬任一既有模組時**先問使用者**，不要自建第一階目錄（`{docs-root}` 由專案 CLAUDE.md 設定，未設定為 `docs/`）。模組／功能已可確定 → 依 shared-preludes §0.8 一併建 `analysis/_context.yml`；尚不確定則不建，留給 `explore`。
7. **迭代**：第二輪以後**更新既有檔、不重寫**——【待確認】獲答覆升為【已確認】並補出處、【可能推測】被推翻則刪除並記入「已解決」小節（避免同一題再問客戶第二次）。

### A.1a 從 Fireflies 取素材（選配）

腳本 `${CLAUDE_PLUGIN_ROOT}/skills/interview-prep/scripts/fireflies_fetch.py`（stdlib-only，
`python3` 直接跑）。API key 解析順序：env `FIREFLIES_API_KEY` →
`~/.config/fireflies/config.json`（`{"api_key": "..."}`）。

| 使用者說法 | 指令 |
|---|---|
| 沒指定哪一場 | `--list --limit 10` 列近期會議，用 `AskUserQuestion` 讓使用者挑（option label ＝ `{title}（{date}）`），再以選定 id 跑 `--id` 抓全文 |
| 指定了 transcript id | `--id <transcript_id>` |
| 「最近那場」 | `--latest` |

抓回的 JSON 含 `title`、`date`、`transcript_url`、`summary.overview`、`summary.action_items`、
`sentences[]`（每句帶 `text`、`speaker_name`、`start_time`）。

**`speaker_name` ＋ `start_time` 必須保留到出處**——手寫會議記錄常常指不出「誰在哪一段講的」，
依 `evidence-labels.md` §降級規則第 1 條就不得標【已確認】；逐字稿正好補得起這一段，
是 Fireflies 來源相對手寫記錄的唯一實質優勢。出處格式見 `evidence-labels.md` §出處格式。

**逐字稿是素材、不是彙整**：仍照 §A.2 拆條標籤、§A.3 五區塊歸位，
**不得把逐字稿整段貼進彙整檔**。同一主題的零碎發言合併成一條。

退出碼處置：

| 碼 | 意義 | 處置 |
|---|------|------|
| 2 | 無 API key | 引導使用者至 Fireflies → **Settings → Developer Settings** 取 key，寫入 `~/.config/fireflies/config.json` 並 `chmod 600`，然後重試。**不得把 key 回印到對話** |
| 3 | HTTP／網路錯誤（含 401） | 告知 key 可能失效或無網路，終止 |
| 4 | GraphQL 回錯 | 終止並回報原始錯誤訊息 |
| 5 | 查無場次 | 告知並請使用者確認 id，或改用 `--list` 重挑 |

**API live、不快取**：抓取失敗就停，不得改用舊資料或憑記憶湊出逐字稿內容。

## 模式 B：訪談大綱

1. **收四欄**：專案背景／目標／已知限制／受訪者（角色＋這個角色在意什麼）。跑過模式 A 就從其產出取，缺的才問，一次一題。
2. **先檢查再產綱**（順序不可顛倒）：先回答兩題——(1) 專案背景還有哪些資訊不清楚；(2) 站在**這位受訪者的立場**有哪些議題值得確認。以**文字收尾單獨結束一個回合**（依互動詢問規範 §回合可見性），使用者補完再產大綱。
3. **產 A~F 大綱**：依 `${CLAUDE_PLUGIN_ROOT}/skills/interview-prep/references/interview-guide.md`，填入範本 `${CLAUDE_PLUGIN_ROOT}/templates/interview-outline.md`——A 開場與背景／B 現況與使用情境／C 問題與痛點／D 期待成果／E 限制與不可妥協條件／F 最後確認問題。提問技法（問經驗不問意見、追原因與影響、不誘導、不複合題、不早跳解法）為硬性要求。
4. **30 分鐘收斂**：依 interview-guide §30 分鐘版挑 8~10 題，標所屬段落與預估時間，並列出「砍掉的題目改用書面補問」。
5. **落檔**：與模式 A 同目錄，`{名稱}_訪談大綱_{受訪者}.md`。
6. **訪談後**：把逐字稿或筆記餵回**模式 A** 併入彙整（§A.7 迭代），不另起新檔。

## 收尾條件

全部成立才算完成（見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §八）：

**模式 A**：五區塊皆已填（允許留白但不得用推測填滿）；每條【已確認】都附得出出處
（來源檔／場次 ＋ 原句片段，Fireflies 來源另含 `speaker_name` ＋ `start_time`）；
Top 5 已列且各寫明「為何優先」與「該問誰」；檔案已落檔。

**模式 B**：A~F 六段大綱完整；30 分鐘版已挑出 8~10 題並標所屬段落與預估時間；
砍掉的題目已列為書面補問；檔案已落檔。

**共同**：【可能推測】每條都有推測依據且對應到一個訪談問題——
**推不出依據的不得留在文件裡**。

完成後依動線用 AskUserQuestion 建議下一步：模式 A 盤點後已知足以描述需求 → `sa-flow:explore`（盤點出的已知／未知是探索問答的起點）；未知仍多就先排下一場訪談；使用者同意才接著跑，不自動執行。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 無任何輸入 | 請使用者提供素材路徑或專案背景，否則終止——**不得憑空生成大綱** |
| 素材只有一場、資訊極少 | 照跑，但區塊 1~3 允許大量留白；**不得用推測填滿版面**，缺就是缺 |
| 使用者要求「幫我推測客戶想要什麼」 | 產出仍走【可能推測】規則（附依據＋轉成問題），不升格為需求 |
| 受訪者角色不明 | `AskUserQuestion` 問角色與其關注點——問錯對象的題目等於白問 |
| 既有彙整檔已被使用者手改 | 讀當前檔為準，只補自己的更新，保留使用者所有註記 |
| 使用者要用 Fireflies 但無 API key | 依 §A.1a 引導設定；設不成就退回本機檔案／貼入文字，**不因此中止整個彙整** |
| Fireflies 抓取失敗（退出碼 3／4／5） | 停止該來源，回報原因；**不得用舊資料或記憶硬湊**充當逐字稿 |

## 隱私提醒

Fireflies 是雲端服務，逐字稿存於其伺服器。敏感客戶會議若不宜上雲，改走本地 whisper 流程
（專案本地 `transcribing-audio` skill，有裝才提），把產出的逐字稿檔案路徑當本機來源餵進 §A.1。
