# annotate.py Spec 格式

`${CLAUDE_PLUGIN_ROOT}/scripts/annotate.py <spec.json>` 讀取 JSON spec，輸出標註/合成後的 PNG。

**plugin 共用**，使用者：`linear-illustrate`（票面示意圖）、`operation-manual` ／
`manual-explorer`（手冊截圖的遮罩與紅框）。要加新的繪圖能力就改這一支，
**不要在各自的 skill 裡另寫一份**。

## 頂層欄位

| 欄位 | 必填 | 說明 |
|------|------|------|
| `base` | ✅ | 底圖路徑（playwright 截圖，scale=css） |
| `output` | ✅ | 輸出 PNG 路徑（放 scratchpad，不要放 repo 內） |
| `composite` | 否 | 合成設定（先於 ops 執行），見下 |
| `ops` | 否 | 繪圖操作陣列，依序執行 |
| `legend` | 否 | 底部圖例帶（白底、灰分隔線、編號圓點＋文字） |
| `font_size` | 否 | 標籤／圖例字級，預設 22（CSS-px 截圖用）；chrome-devtools DPR 2 的截圖可給 44，否則縮到頁寬後標籤讀不到。標籤塞不下時改回 22；**同一批圖用同一字級**，不要單獨改一批 |

## 座標系

一律 **影像 px**。

- playwright `browser_take_screenshot` 用 `scale: "css"` 時影像 px == CSS px ==
  `getBoundingClientRect()` 回傳值，三者直接對得上，不需換算。
- **chrome-devtools 的 `take_screenshot` 不是**——DPR 2 的機器截出來是 CSS px × 2
  （實測 1680×1000 的 viewport 截出 3360×1672）。`getBoundingClientRect()` 給的是 CSS px，
  **呼叫端要自己先乘好再寫進 spec**。
- 批次套用前**先拿一個元素驗映射**：疊一個框、截下來看有沒有套準，再跑其餘的。
  一分鐘的成本，省掉整批重做。

## ops

```json
{"op": "rect",  "box": [x0, y0, x1, y1], "color": "red",    "width": 4, "dashed": false}
{"op": "rect",  "box": [x0, y0, x1, y1], "color": "orange", "dashed": true}
{"op": "cross", "box": [x0, y0, x1, y1], "color": "red",    "width": 5}
{"op": "badge", "at": [x, y], "num": 1, "color": "red"}
{"op": "mask",  "box": [x0, y0, x1, y1]}
{"op": "mask",  "box": [x0, y0, x1, y1], "color": [52, 103, 169]}
{"op": "label", "box": [x0, y0, x1, y1], "text": "說明文字", "side": "right"}
```

- `rect`：實線/虛線框。框要比元素 rect 外擴 4px 左右才不會壓到內容。
- `cross`：整框打紅 X（表示「移除」）。
- `badge`：編號圓點（半徑 16px），放在對應框的左上角 `(x0-2, y0-2)`。
- `mask`：**實心遮罩**。`color` 省略時自動取樣框上下各 6px 的底色中位數——
  遮出來會跟背景同色，看不出被塗過。**但自動取樣有適用邊界，見下節。**
- `label`：標籤貼在框旁邊，`side` 取 `right`｜`left`｜`above`｜`below`，預設 `right`。

### 🔴 遮罩必須畫進像素，不能用 CSS 疊

用 HTML 疊一層半透明或實心 div 再截圖，**顏色會被色彩管理位移**——
實測輸入 `#3467A9`、輸出像素 `(65,102,164)`，遮罩跟底色差一截，一眼看得出來。
`mask` op 直接改像素，沒有這個問題。

驗收看**輸出像素**不看輸入色號：遮罩框內取一點、框外取一點，兩者 RGB 必須相等。
取樣點要落在**同一個元件內**——落到元件外的背景本來就是別的顏色，那不算失敗。

### `sample_color` 只適用於「框周圍與框內同色」

省略 `color` 走自動取樣，前提是**框上下各 6px 的顏色就等於框內要蓋掉的底色**。
純色背景（導覽列、表頭、單一卡片內部）成立；下面三種情況一律**明確指定 `color`**：

| 情況 | 會發生什麼 |
|---|---|
| 框緣跨到分隔線、邊框、圓角 | 取樣取到線的顏色。實測塗成 `(238,238,238)` 而底色是純白 `(255,255,255)`，差 17 階、肉眼一塊灰斑 |
| 大範圍／跨多個元件的遮罩 | 取樣點與框內中央根本不是同一塊區域，塗出突兀色塊 |
| 同一批圖底色不只一種 | 實測六張導覽列有三種底色（半透明 scrim 疊上去會整條調暗）。**單一色套整批必露色差，要逐張取色** |

取色的方法：用 PIL 在**該張圖**上讀一個確定是空白的點，不要沿用別張圖的數值。

### 🔴 遮罩驗收要開圖看，像素統計只能輔助

「框內深色像素 0」這類統計**在框沒對準目標時必定通過**——因為那裡本來就是空白。
曾實際踩到：遮罩框偏了 7px 落在文字上方的空白區，
統計回報乾淨，而真正要遮的編號一個字都沒動，**同時還把該保留的欄位標題蓋掉了**。

所以：裁切該區域**放大看一眼**，確認「該遮的不見了、該留的還在」。
統計拿來定位可疑處很好用，但不能當結論。通則見
[verify-against-source.md](verify-against-source.md)。

## 色彩慣例

| 顏色 | 語意 |
|------|------|
| `red` | 問題點／待移除元素 |
| `blue` | 參照元素（位置不變、僅供對照） |
| `green` | 調整後的新位置／新增區塊 |
| `orange`（虛線） | 被遮蔽或隱藏的元素實際位置 |

## composite（「調整後」合成示意）

把另一張截圖的區塊接到底圖的某個 y 之下（底圖該線以下裁掉、畫布向下延伸）：

```json
"composite": {
  "cut_y": 693,
  "gap": 10,
  "insert": {"src": "remarks-tab.png", "crop": [352, 247, 1541, 468]},
  "x": 352,
  "bottom_margin": 30
}
```

- `cut_y`：底圖保留 0..cut_y（通常 = 目標區塊 rect 的 `y + h`）。
- `insert.crop`：來源圖上要搬移區塊的 `[x0, y0, x1, y1]`（用量測到的 rect）。
- `x`：貼上時的左緣，預設沿用 crop 的 x0（同頁面同容器時左緣通常一致）。
- 合成後的插入區域為 `(x, cut_y+gap)` 起、寬高同 crop——ops 的框可據此計算。

## legend

```json
"legend": [
  {"num": 1, "color": "red",  "text": "「備註欄」tab 移除"},
  {"num": 2, "color": "blue", "text": "價格資料區塊（現有位置不變）"}
]
```

每行 34px 高；文字用完整句子說明該編號的語意。

## 完整範例 1：現行畫面標註

```json
{
  "base": "02-add-item-overlay.png",
  "output": "02-annotated.png",
  "ops": [
    {"op": "rect", "box": [333, 186, 1241, 545], "color": "red", "width": 4},
    {"op": "badge", "at": [331, 184], "num": 1, "color": "red"},
    {"op": "rect", "box": [752, 448, 943, 512], "color": "orange", "dashed": true},
    {"op": "badge", "at": [750, 446], "num": 2, "color": "orange"}
  ],
  "legend": [
    {"num": 1, "color": "red", "text": "「新增品項」pop-up：只有品項欄位，沒有訂單主要內容"},
    {"num": 2, "color": "orange", "text": "訂單「主要內容」欄位實際位置——被 pop-up 完全蓋住"}
  ]
}
```

## 完整範例 2：調整後合成

```json
{
  "base": "02-order-tab-price.png",
  "output": "02-target-composite.png",
  "composite": {
    "cut_y": 693,
    "gap": 10,
    "insert": {"src": "01-remarks-tab.png", "crop": [352, 247, 1541, 468]},
    "x": 352
  },
  "ops": [
    {"op": "rect", "box": [348, 699, 1545, 928], "color": "green", "width": 4},
    {"op": "badge", "at": [346, 697], "num": 1, "color": "green"},
    {"op": "rect", "box": [352, 476, 1526, 522], "color": "blue", "width": 3},
    {"op": "badge", "at": [350, 474], "num": 2, "color": "blue"}
  ],
  "legend": [
    {"num": 1, "color": "green", "text": "調整後：原「備註欄」的區塊整段移到「價格資料」之下（本圖為真實畫面合成示意）"},
    {"num": 2, "color": "blue", "text": "價格資料區塊（現有位置不變）"}
  ]
}
```

## 字型

腳本內建 macOS/linux CJK 字型 fallback（STHeiti → Hiragino → PingFang → Arial Unicode → Noto）。`PingFang.ttc` 在部分 PIL/freetype 版本無法開啟（`OSError: cannot open resource`），所以不是首選——不要改回去。
