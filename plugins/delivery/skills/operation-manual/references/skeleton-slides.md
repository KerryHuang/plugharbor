---
marp: true
theme: default
paginate: true
header: '操作手冊 － 採購單作業'
style: |
  section { font-size: 26px; }
  section.lead { text-align: center; }
  section.lead h1 { font-size: 52px; border-bottom: none; }
  h1 { color: #1a4d8f; border-bottom: 3px solid #1a4d8f; padding-bottom: 8px; }
  h2 { color: #1a4d8f; font-size: 32px; }
  table { font-size: 22px; }
  blockquote { background: #fff9e6; border-left: 6px solid #e0a800;
               padding: 12px 18px; font-size: 24px; }
  img { display: block; margin: 0 auto; }
---

<!--
本檔以虛構產品「Greenleaf 訂貨管家」示範。有品牌文字要放頁尾時，在 frontmatter 加 footer: '<品牌文字>'，沒有就不加。
不要用 raw HTML（<div> 之類）做色塊：Marp 預設不允許，標籤會原樣印在投影片上。要色塊用 blockquote，外觀靠上面的 style。
簡報依定版後的手冊產出，不從 inventory 另寫，避免兩份內容漂移。
產出：scripts/build-deck.sh <本檔路徑> <.tmp 下的輸出目錄>，同時出 PDF 與 PPTX，並自動跑溢出檢查。
-->

<!-- _class: lead -->
# 採購單作業　操作教學

Greenleaf 訂貨管家 · ORD100

教育訓練

---

# 課程大綱

| # | 章節 | 重點 |
|---|------|------|
| 0 | 開始之前 | 要先建好的主檔與權限 |
| 1 | 進入採購單作業 | 從主控台找到功能 |
| 2 | 新增採購單 | 表頭、明細、送出 |

---

<!-- _class: lead -->
# 0　開始之前

這一章的一句話重點

---

# 小節標題

一到兩句說明，不要整段文字，細節留給手冊。

`![h:420](images/a01-menu.png)`

<!-- 截圖一律用 h: 限高，不得小於 h:380（再小，圖上的標籤讀不到）。
     版面上限是實測的，不是估的（逐種排法用溢出檢查器量過）：

       h:420 → 圖以外最多 1 行文字，且不能再放說明框
       h:400 → 圖以外最多 2 行文字，且不能再放說明框
       h:380 → 1 行文字 ＋ 1 行說明框

     3 行以上文字、或 2 行以上的說明框，任何圖高都會溢出，縮圖救不了，要拆到下一張「小節標題（續）」。
     一張投影片同時放「圖 ＋ 說明框 ＋ 兩行以上說明」必定溢出。
     md 看不出版面，一定要產 PDF 跑 check-deck-overflow.py（build-deck.sh 會自動跑）。 -->

---

# 小節標題

`![h:380](images/a02-list.png)`

> ⚠ 這張圖要提醒的重點

---

# 重點回顧

**重點一**
一句話

**重點二**
一句話
