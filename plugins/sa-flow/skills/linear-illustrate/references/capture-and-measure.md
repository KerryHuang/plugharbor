# 截圖與量測

## 瀏覽器工具

優先用 **playwright MCP**（一次 ToolSearch 載齊）：

```
ToolSearch: select:mcp__playwright__browser_navigate,mcp__playwright__browser_snapshot,mcp__playwright__browser_take_screenshot,mcp__playwright__browser_click,mcp__playwright__browser_evaluate,mcp__playwright__browser_wait_for
```

playwright MCP 不可用時退回 chrome-devtools MCP（連線/登入細節見 `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/browser-bootstrapping.md`）。環境安全判定沿用 `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/safety.md`：**production 只允許導頁＋截圖（唯讀）**；開 dialog、填欄位等操作僅限 `-test` / staging。

## 導頁與操作

1. `browser_navigate` 到目標環境（登入態通常沿用既有 session；未登入見 live-drive bootstrapping）。
2. `browser_snapshot` 取元素 ref → `browser_click` 操作到目標狀態。snapshot 過大時存檔再 grep：`browser_snapshot {filename: "snap.md"}` → `grep -n "關鍵字" snap.md`。
3. 需要重現「被遮蔽」狀態時，先開 dialog 截圖，再關掉量測（見下方版面位移陷阱）。

## 截圖

```
browser_take_screenshot {type: "png", scale: "css", filename: "<票號>-<序號>-<描述>.png"}
```

- **必須 `scale: "css"`**：影像 px == CSS px == rect 量測值，免換算。
- 檔案落在 playwright 的工作目錄（通常是 repo 根目錄）——**收尾必須搬到 scratchpad**，不可留在 repo。

## 量測元素座標

**鐵律：不肉眼猜座標，一律 `browser_evaluate` 量 `getBoundingClientRect()`。**

```js
() => {
  const r = (el) => { const b = el.getBoundingClientRect();
    return {x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height)}; };
  // 例：找包含某文字的最小容器（避免抓到外層 wrapper）
  let best = null;
  document.querySelectorAll('div,section').forEach(el => {
    if (el.textContent.includes('其他資料') && el.textContent.includes('討論備註')) {
      const b = el.getBoundingClientRect();
      if (b.width > 600 && b.height > 100 && (!best || b.width * b.height < best.area))
        best = {rect: r(el), area: b.width * b.height};
    }
  });
  return best;
}
```

常用查法：

- **欄位**：用專案 UI 框架的欄位容器 selector（先 snapshot 看 DOM 結構），過濾 `textContent.includes('欄位名')`。
- **欄位框（首選）**：用文字比對挑「最小容器」很不穩——同一 label 在捲動前後會 match 到不同層（有時只抓到 label 文字、有時抓到整排 wrapper），寬度忽大忽小。穩定做法：先找 `textContent` **完全等於**欄位名的**葉節點**，再往上走到第一個 `getComputedStyle(el).backgroundColor` 非透明的祖先——那就是視覺上的灰底欄位框：

  ```js
  const fieldBox = (label) => {
    let leaf = null;
    document.querySelectorAll('div,span,label').forEach(el => {
      if (!el.children.length && el.textContent.trim() === label) leaf = el;
    });
    for (let el = leaf; el; el = el.parentElement) {
      const bg = getComputedStyle(el).backgroundColor;
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent')
        return el.getBoundingClientRect();
    }
    return null;
  };
  ```

- **按鈕**：過濾 `textContent.replace(/\s+/g,'')`（許多 UI 框架的按鈕文字會含 icon 名，如 `add新增`）。
- **dialog 卡片**：用卡片 selector 過濾寬度區間，不要抓到全螢幕 backdrop（`[role="dialog"]` 常是 backdrop）。
- **被遮蔽元素照樣可量**：`getBoundingClientRect()` 不受覆蓋影響。

## 版面位移陷阱（必讀）

dialog 開啟時多數 UI 框架會鎖 body scroll、移除卷軸，**整頁版面可能平移 10–20px**。因此：

1. 量測值只對「量測當下的版面狀態」有效。
2. 截圖與量測**必須在同一版面狀態下做**——量完座標後若開/關過 dialog，要重拍截圖再用。
3. 保險做法：先操作到目標狀態 → 量測 → 立刻截圖，中間不做任何會改版面的動作。

## 頁面捲動

要讓目標區塊入鏡：`browser_evaluate` 裡 `el.scrollIntoView({block: 'center'})`，捲動後重新量測（rect 是 viewport 相對座標）。

**scrollIntoView 可能是非同步的**：頁面若設了 `scroll-behavior: smooth`，`scrollIntoView` 後在**同一次 evaluate 內**立刻 `getBoundingClientRect()` 會拿到捲動前的舊值。捲動與量測要分成兩次 evaluate；第二次量測時比對 rect 是否真的變了（沒變 = 捲動沒生效，可能抓錯捲動容器——很多框架是內層容器在捲，不是 body）。
