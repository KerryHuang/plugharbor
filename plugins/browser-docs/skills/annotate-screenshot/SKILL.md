---
name: annotate-screenshot
description: "在真實截圖上畫框、編號、圖例、遮罩，或用真實片段合成「調整後」示意圖；輸出 -annotated.png、保留乾淨原圖。可由 agent 以 spec 或標註意圖呼叫。觸發：「截圖加紅框」「標註這張圖」「示意圖」「遮罩個資」。"
argument-hint: "<截圖路徑> [標註意圖｜spec.json]"
---

# Annotate-Screenshot — 截圖標註與合成

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

輸入乾淨截圖與標註意圖 → 寫 spec.json → 跑 `annotate.py` → 輸出 `<原檔名>-annotated.png`。**乾淨原圖一律保留，不覆寫。**

| 類型 | 內容 | 何時用 |
|------|------|--------|
| **現行畫面標註** | 真實截圖＋編號框＋圖例帶 | 呈現問題點、要移除／搬移的區塊、手冊的操作位置 |
| **調整後合成示意** | 真實截圖區塊裁切重組 | 呈現「改完長這樣」，以真實畫面為底 |

> 分工：本 skill 只管「已有截圖 → 標註圖」。開瀏覽器、登入、截圖、量測座標由 `browser-surveyor`（`mode: measure`／`capture`）負責，環境安全規則見 `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/safety.md`。上傳、嵌入票面或文件不在本 skill 範圍。

## 輸入

```
$ARGUMENTS → <截圖路徑> [標註意圖 | spec.json 路徑]
```

呼叫端（含其他 skill、agent 以 Skill 工具叫用）至少給：

| 項目 | 說明 |
|------|------|
| 截圖路徑 | 乾淨底圖。合成示意圖另需被搬移區塊的來源截圖 |
| 標註意圖 | 要框什麼、標什麼、遮什麼，或「調整後」要長怎樣；已有現成 `spec.json` 就直接進步驟 3 |
| 座標 | 目標元素的 rect。沒有就先請 `browser-surveyor`（`mode: measure`）量，**不要肉眼猜**；影像 px 與 CSS px 的換算見 [annotate-spec.md](../../references/annotate-spec.md) §座標系 |
| 輸出位置 | 選填，預設與底圖同目錄；暫存性質的成品放 scratchpad，不要放 repo |

意圖不明確時，用 `AskUserQuestion` 一次問一題；agent 叫用且不能問人時，就照給定的意圖與座標做，缺的欄位在回報中列為「未標註」，不要自行腦補。

## 流程

### 1. 前置：個資

底圖若來自含真實資料的環境，**截圖前**先換假資料，不要事後遮罩：流程與工具見 [anonymize-before-capture.md](../../references/anonymize-before-capture.md)（`${CLAUDE_PLUGIN_ROOT}/scripts/anonymize-page.js`）。只有 canvas／圖片型內容、瀏覽器外框等 JS 改不到的地方，才用 `mask` op。

### 2. 確認底圖與座標

- 底圖是 clean 版：檔名沒有 `-annotated` 字尾，且尚未畫過任何東西。
- 批次套用前**先拿一張驗映射**：疊一個框、開圖看套準了再跑其餘的。
- chrome-devtools 的截圖座標要先換成影像 px 再寫進 spec：倍率＝影像寬 ÷ CSS 寬（`innerWidth`），DPR 2 才是 ×2，不要寫死。

### 3. 寫 spec 並執行

spec.json 放 scratchpad。`output` 設為 `<底圖檔名去副檔名>-annotated.png`，與底圖同目錄；若已有同名檔，確認那是上一輪產物再覆寫。

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/annotate.py" <spec.json>
```

- spec 格式、op 清單（`rect`／`cross`／`badge`／`mask`／`label`）、色彩慣例（紅=問題／移除、藍=參照不變、綠=調整後、橘虛線=被遮蔽）、composite 與完整範例見 [annotate-spec.md](../../references/annotate-spec.md)。
- 每張圖都要有編號圓點＋底部圖例帶；合成圖的圖例必須註明「本圖為真實畫面合成示意」。
- `mask` 的 `color` 省略時自動取樣，只適用「框周圍與框內同色」；跨分隔線、大範圍、整批底色不一致時明確指定 `color`。
- 需要 Pillow：`pip install pillow`。

### 4. 驗收

產出後 Read 檢視每張圖：框位準確、文字不壓內容、編號與圖例對得上。遮罩要放大看「該遮的不見了、該留的還在」，像素統計只能輔助。

### 5. 回報

- 列出每張圖的 `-annotated.png` 路徑，以及保留的 clean 原圖路徑。
- 標註內容一行摘要（框了什麼、遮了什麼）；有缺座標或沒做的項目明列。
- 使用 spec 的路徑，方便呼叫端微調重跑。

**完成判準**：`-annotated.png` 存在且已開圖驗收、clean 原圖未被改動、repo `git status` 沒有多出暫存檔。

## Red Flags

| 症狀 | 正解 |
|------|------|
| `output` 與 `base` 同名 | 會覆寫 clean 圖，無法重標。輸出一律 `-annotated.png` |
| 肉眼猜座標 | 用 `getBoundingClientRect()` 量；沒有就派 `browser-surveyor` `mode: measure` |
| 截圖用 CSS px 座標 | 影像 px = CSS px × 倍率（影像寬 ÷ `innerWidth`；DPR 2 為 2），先換好 |
| 用 CSS 疊遮罩再截圖 | 色會被色彩管理位移。遮罩一律畫進像素（`mask` op） |
| 整批遮罩沿用同一個色值 | 底色逐張不同，逐張取色 |
| 遮罩只看像素統計就放行 | 框偏到空白處統計也會乾淨。開圖放大看 |
| PIL 用 `PingFang.ttc` | `OSError: cannot open resource`。用腳本內建 fallback |
| 合成圖不註明是合成 | 讀者會當成已實作的畫面。圖例必註「合成示意」 |
| 標註圖或 spec 留在 repo | 放 scratchpad，收尾 `git status` 驗證 |

## References

- [annotate-spec.md](../../references/annotate-spec.md) — spec 格式、色彩慣例、composite、完整範例
- [anonymize-before-capture.md](../../references/anonymize-before-capture.md) — 截圖前換假資料（`scripts/anonymize-page.js`）
- `${CLAUDE_PLUGIN_ROOT}/agents/browser-surveyor.md` — 截圖與量測 agent
