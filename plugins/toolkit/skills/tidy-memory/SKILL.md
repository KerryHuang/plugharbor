---
name: tidy-memory
description: 整理 auto-memory 目錄——修復結構問題（孤兒檔、斷連結、索引不符）、控制索引體積（200 行／25,000 字元硬上限）、查證並淘汰過時記憶、合併重複記憶；亦可用 --sessions／--session 依建立 session 查詢或限縮範圍。結構與體積問題自動修，過時與重複逐項列證據後由使用者定奪。Use when 使用者說「整理記憶」「記憶太亂」「記憶重複了」「memory 過時」「索引太長」「那次 session 記了什麼」，或輸入 /tidy-memory。
---

# 整理 memory 目錄

記憶會腐化：票號結案了、欄位改名了、當時的「未 commit」早就 push 了。
本 skill 把腐化找出來，但**判定過時必須有外部證據**——這是它唯一的價值來源。

## 參數

| 形式 | 意圖 |
|---|---|
| `/tidy-memory` | 全目錄整理，跑完 Task 1~6 |
| `/tidy-memory --sessions` | **只列出** session 清單（id、檔數、建了哪些檔），不整理 |
| `/tidy-memory --session <id>` | 把 Task 4／5（過時、重複）的範圍限縮到該 session 建立的檔 |

### `--session` 的能與不能

`scan.py` 的 `sessions` 欄位來自各檔 frontmatter 的 `originSessionId`。

**能**：回答「那一輪工作記了什麼」「這幾則是不是同一次做的」。
不確定 id 就先跑 `--sessions` 看清單再挑。

**不能**：
- **不縮小索引衝突風險**。`MEMORY.md` 沒有 session 歸屬，是全域共用檔；限縮範圍不會讓
  索引的並行寫入變安全，那要靠上面的寫入紀律。
- **Task 2／3（結構、體積）不受此參數影響**，它們本質上是全域的。
- `originSessionId` 記的是**建立者**不是最後修改者，一則被後續 session 改寫過的記憶，
  歸屬仍是原始 session——過濾出的集合不等於「這輪碰過的記憶」。
- 該欄位**官方文件查無規範**，屬觀察到的實作行為；缺值的檔歸入 `(unknown)`，
  不要因為缺值就判定該檔有問題。

> 實測（2026-08-13）：140 檔散在 **96 個 session**，最大一個 25 檔，其餘多為 1~4 檔。
> 這個分布代表 `--session` 對**整理**幫助有限（一次只會處理一兩則），
> 主要價值在**查詢**。要整理就跑全目錄。

## 兩類問題，兩種處置

| 類別 | 例子 | 處置 |
|---|---|---|
| 結構 | 孤兒檔、索引斷連結、索引重複、frontmatter 缺 description／type | **直接修**，修完回報 |
| 語意 | 過時、重複、該合併、該刪 | **列證據後逐項問**，使用者說了才動 |

## 任務初始化

建立 6 個 todo（每項一個），依序執行：

1. 定位目錄並掃描
2. 修結構問題
3. 控制索引體積
4. 查證過時候選
5. 比對重複候選
6. 逐項確認並收斂

## 寫入紀律（貫穿全部任務）

**改 `MEMORY.md` 一律用 `Edit` 精確替換單行或單區塊，禁止用 `Write` 覆蓋整檔。**

這個 workspace 常態多 session 並行，其他 session 隨時會往索引 append 新行。整檔重寫
會把它們剛寫的內容靜默吃掉，而 `~/.claude` 沒有版控，吃掉就沒了。用 `Edit` 時，
字串比對失敗反而是好事——那代表有人動過，停下來重讀，不要改用 Write 硬蓋。

同理，**收尾前重讀一次 `MEMORY.md`**，比對你處理期間有沒有新增的行；有就保留它們。

## Task 1：定位目錄並掃描

memory 目錄依序解析：settings 的 `autoMemoryDirectory` → 預設
`~/.claude/projects/<專案路徑轉換後>/memory/`。當前專案的目錄名可從已載入的
MEMORY.md 路徑直接取得，不必猜。

```bash
"$(command -v python3 || command -v python)" "${CLAUDE_SKILL_DIR}/scripts/scan.py" <memory_dir>
```

輸出 JSON：`counts`、`index_missing_file`、`orphan_files`、
`duplicate_index_entries`、`dangling_wikilinks`、`sessions`（session → 檔名清單）、
每檔的 `issues`、`signals`、`depends_on` 與 `origin_session`。

**腳本只陳述事實，不下判斷。** `signals`（ticket／pending／version／date）是
「需要查證的線索」，不是「已過時的結論」。把 signals 當結論用，就是本 skill 最容易犯的錯。

**驗收：** 拿到可解析的 JSON，且 `counts.files` 與目錄實際檔數相符。

## Task 2：修結構問題

逐項修，不必問：

- `orphan_files` → 讀該檔的 description，在 MEMORY.md 對應分類加一行 `- [標題](檔名.md) — hook`
- `index_missing_file` → 索引指向不存在的檔：確認不是剛被改名（比對相近檔名），
  是改名就修連結，真的沒了就刪該行
- `duplicate_index_entries` → 保留資訊較全的一行
- `dangling_wikilinks` → 目標不存在。**先確認拼字**（wikilink 指向的是**檔名**，不是
  frontmatter 的 `name`）；若確實還沒寫，保持原樣——`[[未來要寫的記憶]]` 是合法用法
- frontmatter 缺 `description` 或 `metadata.type` → 依內容補

**不要碰的**（harness 自己維護，動它等於製造永遠修不完的假工單）：
`name`（會被正規化成 `""`）、`node_type`、`originSessionId`、`modified`。

**驗收：** 重跑 scan.py，`orphan_files`／`index_missing_file`／
`duplicate_index_entries` 皆為 0。

## Task 3：控制索引體積

`MEMORY.md` 有**硬上限：前 200 行或前 25,000 字元，先到者止**。超出的部分在下次
載入時**直接丟棄且不報錯**——你不會知道自己漏讀了什麼
（[官方文件](https://code.claude.com/docs/en/memory)）。

### 量測（口徑錯了會誤判）

```bash
wc -l < MEMORY.md                                    # 行數，對 200 比
node -e "console.log(require('fs').readFileSync(process.argv[1],'utf8').length)" MEMORY.md   # 字元數，對 25000 比
```

**必須量字元數，不是 bytes。** 繁體中文 UTF-8 一字 3 bytes，`wc -c`／`du -b` 會高估
約 1.76 倍，把還有餘裕的檔案誤判成已超標。（實測 2026-08-13：bytes 36,034＝35.2 KiB
看似爆表，實際字元數 20,489＝82%，未超限。）

harness 的提醒訊息以 1024 進位顯示上限（24.4 KiB ≈ 25,000 字元），與官方文件的
「25KB」是同一條限制，不是兩套標準。

### 超過 80% 就處理

處置順序，先做便宜的：

1. **索引行瘦身**——官方要求「one line per entry」。長成三行摘要的條目，把細節搬進
   該則自己的 topic 檔（topic 檔**不計入**這個上限），索引只留一句 hook
2. **狀態描述移出**——「殘留＝docs 未 commit」「下一棒＝X」這類是狀態不是記憶，
   該在 issue tracker 的票或 docs 裡，索引不該重複記
3. **分層**——主索引只留「必須主動注入才有用」的兩類：**進行中**（有下一棒的）與
   **工作通則與教訓**（行為約束，不主動載入就不會遵守）。其餘查詢型分類
   （Domain／DB 真相、已定案規格、工具環境、客戶環境）移到
   `INDEX-reference.md`，該檔不自動載入，需要時用 Grep 或直接讀

分層是最後手段——它讓查詢多一跳。前兩項通常就夠。

**驗收：** 行數 < 160 且字元數 < 20,000（留 20% 餘裕給並行 session 寫入），
且移出的內容確實存在於 topic 檔或 `INDEX-reference.md`，沒有淨損失。

## Task 4：查證過時候選

只處理帶 `ticket` 或 `pending` 訊號的檔。**每一則都要拿到外部證據才能提議**：

| 訊號 | 查什麼 | 用什麼查 |
|---|---|---|
| 票號（如 ABC-123） | 票現在的狀態；Done／Canceled 代表記憶可能該收斂 | 對應 issue tracker 的 MCP 讀票 |
| 「未 commit」「未 push」「尚未」「待做」 | 那件事現在做完沒 | `git log`／`git status`／查該檔案或分支 |
| 欄位名、檔案路徑、flag、API | 現在還在不在、有沒有改名 | Grep／Read／DB 查詢工具 |
| 版本號、日期 | 是否已被更新的事實取代 | git log／該檔現況 |

**硬性規則：查不到證據就不提議。** 不允許用「看起來過時」「應該已經完成了」
之類的措辭下結論——沒有證據的提議會誘導使用者刪掉還有效的記憶。

**過時 ≠ 該刪。** 三種收斂方式，提議時要指明是哪一種：

- **改寫**：結論仍有效但細節變了（票號、欄位名、狀態）→ 更新內容，保留教訓
- **降級**：從「進行中」移到「已定案」分類，內容大多不動
- **刪除**：整則的前提已不存在，且沒有可留的教訓

### 順手補 `depends_on`（把下次的猜測變成查證）

處理到的每一則，若它的有效性繫於某個**外部可查的東西**，在 frontmatter 補一行：

```yaml
metadata:
  depends_on: ["ABC-123", "docs/某模組/某功能/", "ORDERS.STATUS"]
```

`scan.py` 會把它解析進每檔的 `depends_on`，下次執行 Task 4 時直接查這些依賴物的現況，
不必再靠 signals 猜哪則可能過時（有 `depends_on` 的檔優先查，signals 退為次要線索）。

為什麼值得做：記憶不是隨時間線性衰減，是**隨外部狀態改變離散失效**——「這張票還沒開」
在票開的那刻失效、「docs 未 commit」在 commit 那刻失效。用 TTL 或日期猜完全對不上這個
失效模式；查依賴物才對得上。

不必回頭補 140 個檔，**只補這次處理到的**，漸進累積即可。

> ⚠ `depends_on` 是本 skill 自定欄位，**不是官方 schema**（`originSessionId`、`type`
> 同樣未見於官方文件，屬觀察到的實作行為）。harness 若正規化 frontmatter 時把它清掉，
> 不要跟它對抗，改記進該則正文。

**驗收：** 每個候選都附一行證據（票狀態／commit hash／grep 結果），
沒有證據的候選已被剔除而非帶著猜測往下走。

## Task 5：比對重複候選

判準是**可執行結論**，不是標題相似度。兩則講同一個主題但推出不同行動 → 不是重複。

比對方式：把 signals 有交集（同票號、同欄位、同表名）或 description 語意接近的檔配對，
讀完兩邊內文再判斷。

**同一個 `origin_session` 建立的檔要優先配對。** 它們出自同一段思路，重複或該合併的
機率比隨機兩檔高得多——例如同一次 session 同時產出「某功能的分析結論」與「該次分析
學到的通則」，兩者常有大段重疊。`scan.py` 的 `sessions` 欄位直接給出這些群組。

⚠ 但這只是**配對優先序**，不是判準。同 session 的兩則講不同事情是常態
（一則記功能結論、一則記工具教訓），判準永遠是「可執行結論是否同一條」。

合併時：

- 保留**兩邊的證據行**，不是只留一則的——證據是記憶的價值所在
- 保留較具體的 description
- 兩邊的 `[[連結]]` 併集
- 被併掉的檔刪除後，**掃全目錄**把指向它的 wikilink 改指到保留的那則

**驗收：** 每個合併提議都說清楚「哪一條可執行結論重複了」，而非「這兩則很像」。

## Task 6：逐項確認並收斂

用 `AskUserQuestion`，**一次一題**。不要把 20 個提議塞進一則訊息要使用者一次回答。

每題含：檔名、提議動作（改寫／降級／刪除／合併）、**證據**、不做的後果。
選項給「照建議做／保持原樣／我來決定內容」。

依使用者答覆逐一套用。**刪除永遠是使用者說了才做**——`~/.claude` 底下沒有版控，
誤刪不可回復。

最後重跑 scan.py，回報前後對照：檔數、索引數、修了什麼、收斂了什麼。

**驗收（二元）：** `counts.files == counts.index_entries`，且
`orphan_files`／`index_missing_file`／`duplicate_index_entries` 全為 0。

`dangling_wikilinks` **不列入歸零條件**——`[[未來要寫的記憶]]` 是合法的前向連結
（見 Task 2）。只需確認每一條都已逐項看過：是拼錯就修，是前向連結就留著。
把它當成必須歸零的缺陷，會逼人刪掉合法連結。

索引體積（Task 3）也要一併回報：行數與字元數的前後對照。

## Red Flags — 停下來

想到這些代表正在合理化：

| 念頭 | 現實 |
|---|---|
| 「這則看起來過時了」 | 「看起來」不是證據。查票／查 git／查檔案，否則不提。 |
| 「signals 有命中，應該是過時的」 | signals 是線索不是結論。52 個檔有票號訊號，不代表 52 則過時。 |
| 「標題很像，應該重複」 | 相似 ≠ 重複。判準是可執行結論是否同一條。 |
| 「過時了就刪掉吧」 | 過時的記憶常只需改寫。教訓的價值不隨票號結案而消失。 |
| 「一次問完比較快」 | 一次 20 題等於沒問。逐題問。 |
| 「frontmatter 格式不統一，順手修一下」 | `name: ""` 是 harness 產物。修它會變成永遠修不完的假工單。 |
| 「這些檔我剛掃過，不用重跑驗收」 | memory 目錄有其他寫入者（harness 正規化、auto-dream 合併）。收尾一定重跑。 |
| 「整份索引重寫比較快」 | 並行 session 剛 append 的行會被靜默吃掉，且沒有版控可回。一律 Edit 逐條。 |
| 「Edit 字串比對失敗，改用 Write 蓋過去」 | 比對失敗＝有人動過檔案。那是警報，不是障礙。重讀再改。 |
| 「`du -b` 顯示 35KB，超過 25KB 上限了」 | 口徑錯。上限算**字元數**，中文 bytes 會高估 1.76 倍。量錯會做出不必要的大手術。 |
| 「索引太長，把舊的刪掉就好」 | 刪除是最後手段。先瘦身索引行、移出狀態描述，內容搬進 topic 檔不算損失。 |

## 附帶事實

- **檔名是權威識別**：`[[連結]]` 指向檔名，不是 frontmatter 的 `name`。
- **目錄不是你獨佔的**：harness 會在寫入後正規化 frontmatter；`autoDreamEnabled`
  開啟時還有背景合併程序。掃描結果可能在你處理期間變動。
- 記憶分類（`type`）：`user`／`feedback`／`project`／`reference`。
  `feedback` 與 `project` 內文要有 **Why:** 與 **How to apply:** 兩行。
- **索引硬上限**：前 200 行或前 25,000 字元，先到者止，超出**靜默丟棄**、無錯誤訊息、
  無設定可調（[官方](https://code.claude.com/docs/en/memory)）。topic 檔不受此限。
- **官方未文件化的欄位**：`originSessionId`、`node_type`、`type` 在官方文件查無規範。
  它們是觀察到的實作行為，可讀不可依賴——用它們做邏輯判斷時要有 fallback。
- **狀態不屬於 memory**：哪一棒、等誰、殘留什麼是 issue tracker 的票與 docs 的事。
  memory 只留「當時的判斷與教訓」。索引裡看到狀態描述，就是該搬走的東西。
- **不要裝 `claude-mem`**：它曾靜默寫入 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 到
  settings.json，把原生 auto-memory 關掉且零警告（該專案 Issue #2836），
  既有記憶會對使用者「消失」。
