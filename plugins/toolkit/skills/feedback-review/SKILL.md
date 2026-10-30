---
name: feedback-review
description: 處理 hook 收集的「使用者糾正 agent」回饋佇列：驗證上一輪規則改動是否生效，把新糾正分群後逐群提增量改動，經人審才套用並記帳。Use when 使用者說「回顧回饋」「處理回饋佇列」「feedback review」，使用者答應了 SessionStart 佇列積壓提醒後的提議，或輸入 /feedback-review。
---

# 回饋佇列回顧

`feedback-capture` hook 把使用者糾正 agent 的語句記進 `~/.claude/feedback-loop/queue.jsonl`，
agent 自記的摩擦（`feedback_queue.py friction`）也進同一個佇列；
本 skill 是閉環的後半段：**Check 上一輪 → 分群 → 定目標 → 人審 → 改 → 記帳 → 歸檔**。

三條不能破的原則（理由見 `references/principles.md`）：

1. **人審**：每條改動都經使用者核准，不自動套用。
2. **只增量**：Edit 局部，不整檔重寫；每加一條就附一個可刪或可合併的候選。
3. **要能驗效**：改動寫進帳本並附驗效訊號，下次回顧先驗它。

## 檔案位置

| 檔 | 位置 | 進 git？ |
|---|---|---|
| 佇列（未處理） | `~/.claude/feedback-loop/queue.jsonl` | ❌ 使用者原話，只放本機 |
| 歸檔（已處理） | `~/.claude/feedback-loop/archive.jsonl` | ❌ |
| 上次回顧時間 | `~/.claude/feedback-loop/last-review` | ❌ |
| user 層改動帳本 | `~/.claude/feedback-loop/ledger.md` | ❌ |
| 專案層改動帳本 | `<該專案 git 根>/.claude/feedback-ledger.md` | 專案決定 |

佇列是全域的（所有專案共用），每筆帶 `cwd`。**帳本跟著改動目標走**，不跟著執行位置走：
改 user 層記 user 帳本，改某專案記那個專案的帳本。

佇列操作一律走腳本，不手改 jsonl（`<PY>` 用 `"$(command -v python3 || command -v python)"`）：

```bash
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py pending [--since <日期>]
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py archived [--since <日期>]
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py context <id> --turns 3   # 糾正前 3 輪對話
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py archive <id>... --disposition <處置>
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py stamp                    # 只更新 last-review
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py ledger --user | --cwd <目錄>
```

`--since` 給日期＝該日之後（不含當日）。

## Task 1：Check 上一輪

1. 取要檢查的帳本：`ledger --user`，加上佇列與 archive 裡出現過的每個 `cwd` 各跑一次
   `ledger --cwd <cwd>`（去重；目錄已不存在就跳過）。帳本不存在的略過。
2. 對每條**狀態＝觀察中**的改動：用 `pending --since <改動日>` 與 `archived --since <改動日>`
   找符合「驗效訊號」的糾正；專案帳本只看 `cwd` 落在該專案內的筆數。
3. 依 `references/ledger-format.md` 的判準標 ✅ 生效／❌ 無效／⏳ 樣本不足，
   在「驗效紀錄」追加一行、更新狀態欄，不動其他欄。
4. ❌ 的條目連同復發的佇列 id 帶進 Task 2，**自成一群並排在最前面**。

## Task 2：讀佇列、去重分群

1. `pending`。佇列空且 Task 1 沒有 ❌ → `stamp` 後回報「無待處理」結束。
2. 每筆先看 `excerpt`、`matched`、`cwd`；判斷不了是不是在糾正、或糾正什麼時，才跑
   `context <id>` 看前後文。**只讀片段，不整檔讀 transcript。**
3. 分群：**同一個根因算一群**，不是同一個關鍵字。例：「改用 X」「又用 Y 了」若根因都是
   「沒先查專案慣例就選工具」，就是同一群。一群記下：根因一句話、佇列 id、代表性原話、涉及的 `cwd`。
4. 符合某條 ❌ 條目驗效訊號的筆數，併入那個 ❌ 群，不另開新群。
5. 明顯不是糾正 agent 的（句中的「不對」在描述資料、引用別人的話）標為**雜訊**。
6. `source: agent` 的是 agent 自記摩擦，先分類：`led_by` 指向的條文說法和 `found` 矛盾＝**誤導**，
   目標就是修或刪那條文字；沒有條文講到 `found`＝**缺口**，照 Task 3 的表定目標。

## Task 3：判斷改動目標

每群依下表定目標（細節與邊界案例見 `references/targets.md`）：

| 根因屬於 | 目標 |
|---|---|
| 換到任何專案都成立的行為（溝通、工程習慣、工具用法） | user 層：`~/.claude` 的 CLAUDE.md／rules |
| 跟某專案的結構、流程、業務、工具設定有關 | 專案層：該群 `cwd` 所在專案的 CLAUDE.md／`.claude/rules` |
| 一次性的事實或踩坑，不是行為規則 | memory |
| 某個 plugin 的 skill 行為不對 | plugin（見下） |
| 不是糾正、或已不成立 | 雜訊，直接歸檔 |

- **user 層只放通用行為**：提到任何特定專案、公司、客戶、內部工具名稱的，一律歸專案層。
- **專案層的群橫跨多個專案**：分專案各問一題；目標專案不在本機或沒有寫入權限就延後。
- **plugin 目標不直接改**：若該 plugin 提供 retrospective 類 skill，就把這群的證據清單
  （佇列 id、原話、根因、建議）交給它處理；沒有就只列在報告，不動 plugin 檔。

## friction 子命令：agent 自記摩擦

agent 發現自己被規則／文件／記憶帶偏、或該有規則卻沒寫時，用 `friction` 記進同一個佇列
（打錯字、工具一時失敗不記）：

```bash
<PY> ${CLAUDE_SKILL_DIR}/scripts/feedback_queue.py friction --tried "<試了什麼>" --found "<發現什麼>" [--led-by "<帶偏的規則／文件／記憶>"]
```

`--tried` 與 `--found` 必填，`--led-by` 選填。記錄的 `source` 為 `agent`，之後跟使用者糾正一樣由本 skill 回顧。

## Task 4：逐群提案、人審

1. 先讀目標檔現況。已有同義條文卻沒被遵守、或本群是 ❌ 群＝文字已證明無效：
   提案**升級成強制機制**（`references/targets.md`「升級成機制」），不再改寫或加文字。
2. 每群提**一個增量改動**：要插入／修改的確切文字與位置（old → new），不整檔重寫。
3. **每加一條規則，同時附一個可刪或可合併的候選**：同檔或同層裡與其他條文重複、已過時、
   或已由工具／hook 強制執行的條文。沒找到就明說「無可刪候選」並說明找過哪些檔。
4. 用 AskUserQuestion **一次問一群**，選項含：核准／改寫後核准／歸雜訊／延後。
   題目附建議與理由；❌ 群要註明「上次改法無效」、上次改了什麼、復發的原話。
5. 不合併題目、不先列清單讓使用者挑。

## Task 5：套用與記帳

1. 核准的才 Edit；可刪候選也經核准才刪。
2. 依 Task 3 的目標取帳本（user 層 `ledger --user`；專案層 `ledger --cwd <該群 cwd>`），
   不存在就依 `references/ledger-format.md` 建立。每條一個小節：日期、來源佇列 id、目標檔、
   改了什麼、預期效果、驗效訊號、狀態＝觀察中。
3. ❌ 群重提核准後：舊條目維持 ❌ 並加一行「由 <新條目日期｜標題> 取代」，另開新條目。
4. 改的是版控中的檔：只改不 commit，回報裡列出檔案讓使用者決定。

## Task 6：歸檔

1. 已處理的群（核准、雜訊、交給 plugin）：`archive <id>... --disposition <處置>`，
   腳本會同時更新 last-review。
2. **延後**的群留在佇列，不歸檔；全部延後時跑 `stamp`。
3. 回報：本輪 Check 結果（✅／❌／⏳ 各幾條）、處理幾群、改了哪些檔與帳本、佇列剩幾筆。
