---
name: linear-illustrate
description: "用實機真實截圖為 Linear 票補示意圖：瀏覽器擷取、標註框／編號／圖例，或以真實片段合成調整後畫面，上傳並嵌入票描述。觸發：「補真實截圖」「附示意圖到票」。"
argument-hint: "<票號> [目標畫面／調整描述]"
model: sonnet
---

# Linear-Illustrate — 用真實截圖幫票做示意圖

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

讀 Linear 票 → 實機操作到目標畫面 → 精確量測 → 標註或合成 → 上傳附件並內嵌回票描述。產出兩類圖：

| 類型 | 內容 | 何時用 |
|------|------|--------|
| **現行畫面標註** | 真實截圖＋編號框＋圖例帶 | 呈現問題點、要移除/搬移的區塊 |
| **調整後合成示意** | 真實截圖區塊裁切重組 | 呈現「改完長這樣」，以真實畫面為底，比手繪原型更接近成品 |

> 分工：**live-drive** 管連線/登入/安全判定（本 skill 引用其 references）。本 skill 專職「真實截圖 → 票內示意圖」。

## 輸入參數

```
$ARGUMENTS → <ticket-id> [目標畫面/調整描述]
```

未給票號時以文字詢問票號（自由文字輸入）。目標畫面不明確時，從票的需求內容推斷要呈現哪些畫面與狀態，用 `AskUserQuestion`（multiSelect）列推斷出的畫面清單供勾選——最關鍵的畫面放第一位標「（推薦）」，推斷依據一行寫進 description。
其餘互動詢問依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範。

## 流程

### 1. 讀票定畫面

1. 用 Linear MCP 的 `get_issue` 讀票，理解業務背景與功能目標。
2. 決定要截哪些畫面、每張圖要標什麼、是否需要合成「調整後」圖。
3. 決定環境 URL：優先讀專案 `CLAUDE.md` 的環境設定；沒有就問使用者（格式如 `https://<your-app>`，限測試／staging 環境）。

### 2. 派 `browser-surveyor` 取截圖與座標

**主 session 不開瀏覽器。** 截圖與 DOM snapshot 對「畫示意圖」這件事毫無用處，
卻會擠爆 context——這一棒一律派 `sa-flow:browser-surveyor`（`mode: measure`）：

> 同 session 可平行派多個瀏覽器 agent，各給不同 `isolated_context`。

```
subagent_type: "sa-flow:browser-surveyor"
prompt: |
  mode: measure
  url: {步驟 1 決定的環境 URL}
  credentials: {登入設定檔絕對路徑——依 workspace CLAUDE.md 指定,未指定則試 repo 根 `CLAUDE.local.md`;派工前先 `ls` 驗存在}
  targets:
    - {畫面/狀態 1：怎麼到達、要量哪些元素}
    - {畫面/狀態 2：...}
  out_file: {scratchpad 絕對路徑}/measure.yml
  shot_dir: {scratchpad 絕對路徑}/shots
  focus: 要框的元素、要裁切的區塊、插入點的精確 rect
  isolated_context: linear-illustrate-{票號或序號}   # 同 session 派多個時各自不同，例 survey-01／survey-02
```

回傳的是**證據檔路徑與一行摘要**，不是截圖原文。主 session 讀 `measure.yml`
取檔名與座標即可，**不要 Read 截圖進 context**——步驟 4 產出後才需要看圖驗收。

<law>
**環境安全由主 session 先判、agent 再判一次**（agent 拿不到本檔的 `<law>`）：
`-test` / staging 才允許點擊、開 dialog 等操作；production 或判不準時一律唯讀
（只導頁＋截圖），除非使用者顯式授權。任何情況都不送出/儲存資料——截圖流程不需要真的寫入。
派工 prompt 必須明寫本次環境的判定結果。
</law>

> 「版面位移鐵律」（dialog 開關會鎖/放 body scroll 造成整頁平移，量測與截圖必須在同一
> 版面狀態下完成）已寫進 `browser-surveyor` 定義，此處不重述。
> 截圖參數與陷阱見 [capture-and-measure.md](references/capture-and-measure.md)。

### 3. 標註 / 合成

寫 JSON spec，跑本 skill 的標註器：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/annotate.py" <spec.json>
```

- spec 格式、色彩慣例（紅=問題/移除、藍=參照不變、綠=調整後、橘虛線=被遮蔽）、composite 用法與完整範例見 [annotate-spec.md](../../references/annotate-spec.md)。
- 每張圖都要有編號圓點＋底部圖例帶；合成圖的圖例必須註明「本圖為真實畫面合成示意」。
- 需要 PIL（Pillow）。優先用專案 venv 的 python；沒有 PIL 時 `pip install pillow`。
- spec 與輸出圖放 **scratchpad**，不要放 repo。
- 產出後 Read 檢視每張圖，確認框位精準、文字不壓內容，再進下一步。

### 4. 上傳與回票

每檔依序 prepare → curl PUT → finalize（60 秒簽名、URL 逐字元複製），再 `save_issue` 把圖以 assetUrl 內嵌進描述的「現行畫面（實機截圖）」／「調整後示意圖（真實畫面合成）」章節。完整 recipe 與描述結構慣例見 [linear-upload.md](references/linear-upload.md)。

### 5. 收尾（必做）

1. 把截圖/snapshot 等落在 repo 的暫存檔搬到 scratchpad（`git status` 確認 working tree 乾淨）。
2. 回報：附了哪幾張圖、描述改了哪些章節、票連結；操作過程若只開關 dialog 未寫入資料，一併說明環境無異動。

**完成判準**（全部成立才算完成）：附件出現在票上、描述內嵌圖可見、repo working tree 乾淨。

## Red Flags — 全部來自實戰

| 症狀 | 正解 |
|------|------|
| 主 session 自己開瀏覽器截圖 | 派 `browser-surveyor`。截圖進主 context ＝ 隔離失效。 |
| 把 agent 回傳的截圖 Read 進來「先看一眼」 | 步驟 3 產出後才看。此時只需要 `measure.yml` 的檔名與座標。 |
| 派工 prompt 沒寫環境判定結果 | agent 判不準會降唯讀，該操作的畫面拍不到。主 session 先判並明寫。 |
| 一次 prepare 多個檔案再慢慢 PUT | 60 秒過期。一檔一輪。 |
| 手抄 signed URL / 改動 headers | 逐字元複製；400/403 就重新 prepare。 |
| PIL 用 PingFang.ttc | `OSError: cannot open resource`。用腳本內建 fallback。 |
| 截圖留在 repo 根目錄就結束 | 收尾搬 scratchpad，`git status` 驗證。 |
| 合成圖不註明是合成 | dev 會當成已實作的畫面。圖例必註「合成示意」。 |
| 只送 description 片段給 save_issue | 整份覆寫。先 get_issue 拿全文再插入。 |
| 在 production 開 dialog / 填欄位 | 唯讀。要操作去 `-test`。 |

## References

- `${CLAUDE_PLUGIN_ROOT}/agents/browser-surveyor.md` — 截圖／量測 agent（步驟 2 派它；環境安全與版面位移鐵律在其定義內）
- [capture-and-measure.md](references/capture-and-measure.md) — 截圖參數、量測、版面位移陷阱
- [annotate-spec.md](../../references/annotate-spec.md) — annotate.py spec 格式、色彩慣例、實例（**plugin 共用**，`operation-manual` 也用它）
- [linear-upload.md](references/linear-upload.md) — Linear 附件上傳 recipe、描述內嵌結構
- `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/browser-bootstrapping.md` / `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/safety.md` — 連線、登入、環境安全（live-drive 所有）
