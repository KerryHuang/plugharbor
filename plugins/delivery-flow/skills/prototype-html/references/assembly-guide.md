# 組裝指引

把推導結論變成單一 HTML 檔。路徑慣例：`${CLAUDE_PLUGIN_ROOT}/skills/prototype-html/references/`。

## 一、檔案形態

- 單一 `.html`，CSS 全部 inline 放 `<style>`，JS 放檔尾 `<script>`（vanilla，無框架）。
- 禁止外部資源：不用 CDN、外部字型、外部圖片（`grep -c 'src="http'` 與 `href="http` 都應為 0；說明面板的出處連結除外時要放在文字裡，不放 `<link>`）。
- 圖示用文字或內嵌 SVG。
- 檔名：`<功能名>_prototype.html`（kebab-case 功能名）。

## 二、風格來源

| 情況 | 做法 |
|---|---|
| 使用者給了設計系統（URL 或檔案路徑） | 讀它的 token（色彩、間距、字級、圓角）與元件寫法，照它做。URL 用 WebFetch；讀不到就問使用者要檔案，不自己猜 |
| 沒給 | 整份 `neutral-style.css` 用 `cat` 進 `<style>`，不要 Read 進 context |
| 給了但只涵蓋一部分 | 涵蓋的照它，缺的元件用 `neutral-style.css` 對應 class，並把變數對到它的 token |

換設計系統的最小動作：覆寫 `neutral-style.css` 開頭 `:root` 的 CSS 變數。元件 class 不改。不要在原型內另寫覆蓋樣式改變風格（畫面切換規則除外）。

## 三、版型

```
頂欄（功能名＋模式切換）
側欄（畫面清單，data-target）｜內容（多個 .screen，一次顯示一個）
```

最小切換 JS：

```html
<script>
document.querySelectorAll('.sidebar a').forEach(a => a.addEventListener('click', () => {
  document.querySelectorAll('.sidebar a, .screen').forEach(e => e.classList.remove('active'));
  a.classList.add('active');
  document.getElementById(a.dataset.target).classList.add('active');
}));
</script>
```

彈窗用 `<dialog>` 與 `showModal()`。單一畫面的原型可省側欄。

## 四、要呈現的狀態

只靠靜態 HTML 呈現，不做真實驗證、不做分頁運算。至少要看得到：

- 正常列表／表單
- 空狀態（沒有資料時說什麼、下一步是什麼）
- 錯誤提示（欄位錯誤、整頁錯誤擇需要者）
- 關鍵狀態 chip（文字一定要有，不只靠顏色）
- 破壞性操作的確認彈窗

資料照 `mock-data.md`。

## 五、設計說明面板（必含）

放在內容區頂部的 `<details class="notes">`，預設收合，內容：

1. **誰在用、要解決什麼**：一兩句。
2. **推導結論**：查詢條件、欄位與顯示方式、操作動線、規則邊界。
3. **已定案**：每項附一句結論。
4. **待確認**：需求沒寫、原型暫以某假設呈現的項目，逐項寫「假設了什麼、若不是會怎樣」。
5. **資料說明**：資料為示意；使用者給樣本時註明依樣本的哪些組合。

## 六、改既有原型

同功能已有原型就改原檔，不新建、不改檔名、不另存 `_v2`：

1. 先整檔讀過，理解畫面清單、`id` 命名、切換 JS、說明面板。
2. 用 Edit 逐處改，不整檔覆寫重生；只動需變動的畫面或區塊。
3. 畫面增減要同步側欄 `data-target` 與 `.screen`；設計依據變了要更新說明面板，不留舊結論。

## 七、自我驗證

寫完回報前跑：

```bash
grep -c 'src="http' <檔>          # 0
grep -c 'href="http' <檔>         # 0（說明面板的出處用純文字）
grep -c 'class="screen' <檔>      # 多畫面時 ≥ 2
grep -c 'class="notes"' <檔>      # ≥ 1
```

有瀏覽器工具時，自己開檔截圖確認版面（亮色與深色各看一次）。沒有就在回報註明「視覺未驗證」。
