---
name: live-drive
description: "透過 debug-port Chrome＋chrome-devtools MCP 操作執行中的系統：重現問題、寫操作手冊、跑 e2e、探索現況；正式環境禁止異動操作。觸發：「重現這個 bug」「用實機操作」「跑一次 e2e」。"
argument-hint: "<investigate|manual|e2e|explore> [目標/URL]"
---

# Live-Drive — 實機驅動(瀏覽器操作運行中系統)

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

透過 `chrome-devtools` MCP（`--isolated`）連到一個正在跑的 web 系統,登入、導頁、操作、截圖、看 console/network,依**模式**產出對應成品。

> 與既有 skill 的分工:需要**實機驅動/蒐證**時用本 skill;純文件分析仍走 `sa-flow:system-analysis`(現況分析)、`sa-flow:linear-triage`(票根因分析)。本 skill 不取代它們,只在結尾**交棒**。

## 輸入參數

```
$ARGUMENTS → <mode> [目標/URL]
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `mode` | 否 | `investigate` / `manual` / `e2e` / `explore`;未給時先 `AskUserQuestion` 問模式——依任務脈絡把最合適的模式放第一位標「(推薦)」,一行理由寫進 description |
| `目標/URL` | 否 | 目標系統 URL、票號、模組或流程名;URL 未給時先讀**登入設定檔**的 `live-drive-url`,仍無才詢問使用者 |

互動詢問一律依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範(AskUserQuestion＋建議置首;路徑/憑證等自由文字輸入除外)。

## Task 0: 前置(每次必做)

1. **定位登入設定檔**(**派工前必做**):依序試——① workspace `CLAUDE.md` 明文指定的路徑
   (如「先讀 `.claude/live-drive.local.md`」) → ② repo 根的 `CLAUDE.local.md`。
   **兩者都要實際 `ls` 驗存在**,不要憑慣例假設檔名。
2. **確認模式與目標**:模式缺 → `AskUserQuestion`(附推薦,見輸入參數表);目標/URL 缺 →
   讀 Step 1 定位到的設定檔,仍無以文字詢問(自由文字輸入)。
3. 若 TodoWrite 可用,建任務清單:1. 安全判定 2. 派工 3. 判讀與交棒。

> **主 session 不載入瀏覽器工具、不開瀏覽器。** 連線、登入、操作、截圖全部由
> `sa-flow:browser-surveyor` 執行——畫面快照與 network 封包對「判讀與交棒」毫無用處,
> 卻會把主 context 擠爆,那正是這支 agent 存在的理由。

## 流程

### 1. 安全判定(派工前必做,**主 session 的責任**)

先跑 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py`,非 `OK` 就停,照它印的標準寫法請使用者改註冊後重啟 session。

由 URL 判環境,依 `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/safety.md`:

- `-test` / `-staging` / `localhost` / `127.0.0.1` → 允許完整操作
- 命中 **production / 正式客戶網域** 或**判不準** → **降唯讀**(只導頁＋截圖)

<law>
**正式環境唯讀**:命中 production 或無法確認環境時,一律降為唯讀,禁止任何變更動作,
除非使用者於該次顯式授權。
**破壞性操作確認**:刪除/批次/不可逆送出,即使在 test/staging 也先 `AskUserQuestion` 確認。
**判定結果必須明寫進派工 prompt**——agent 拿不到本檔的 `<law>`,它會自己再判一次,
但主 session 的判定是第一道閘,不可省略。
</law>

這一步**不派工**:環境該不該動是政策決定,是主 session 的職責。

### 2. 派 `browser-surveyor` 執行

> 同 session 可平行派多個瀏覽器 agent，各給不同 `isolated_context`。

依模式對應 agent 的 `mode`,一次派工跑完連線、登入、操作與蒐證:

| 本 skill 模式 | agent `mode` | 派工重點 |
|------|------|------|
| `investigate` | `investigate` | 給重現步驟;要求逐步記 console/network 原文與前後截圖 |
| `manual` | `survey` | 給要走的畫面清單;要求記欄位、預設值、驗證訊息原文、各狀態截圖 |
| `e2e` | `investigate` | **給斷言清單**;要求逐項記「預期 X / 實際 Y」,**判定 pass/fail 留給主 session** |
| `explore` | `survey` | 給要探的流程;要求記邊界、隱含規則、非預期行為 |

```
subagent_type: "sa-flow:browser-surveyor"
prompt: |
  mode: {對照上表}
  url: {目標 URL}
  env_class: {Step 1 的判定結果}
  readonly: {true/false —— Step 1 判定,判不準一律 true}
  credentials: {Task 0 定位到的登入設定檔絕對路徑}
  targets:
    - {逐項:怎麼到達、要看什麼}
  out_file: {workspace 根}/.tmp/live-drive/{session}/evidence.yml
  shot_dir: {workspace 根}/.tmp/live-drive/{session}/shots
  focus: {本次關心什麼}
  isolated_context: live-drive-{session}   # 見下
```

**`isolated_context` 是預設帶的,不是選用。** 同 session 派多個 agent 時它們共用同一個 Chrome,
`new_page` 帶 `isolatedContext: "<名字>"` 才各有自己的 cookie jar(同帳號也互不踢)。
⚠ 代價是**不沿用既有登入,要自己登一次**;它不擋分頁互見,每次呼叫帶自己的 `pageId` 那條照舊,
開頁後第一件事 `emulate 1680x1000x2`。細節見 `${CLAUDE_PLUGIN_ROOT}/references/browser-tooling.md`。

**截圖落地**:`chrome-devtools` 截圖只能寫 workspace roots 內 → 一律先落
`.tmp/live-drive/<session>/`,交付 repo 可能在 workspace 外,由主 session 於 Step 3 複製。

> 連不上先跑 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py`，照它印的標準寫法改註冊後重啟 session。
> 細節見 `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/browser-bootstrapping.md`。

### 3. 判讀、產出與交棒

讀 agent 產出的 `evidence.yml`(**不要 Read 截圖進 context**,除非要放進交付物),
依 `${CLAUDE_PLUGIN_ROOT}/skills/live-drive/references/modes.md` 對應模式的產出模板收斂:

| 模式 | 主 session 做什麼 | 產出 | 交棒 |
|------|------|------|------|
| `investigate` | 從證據推根因 | bug 重現報告 | → `sa-flow:linear-triage` 或 `sa-flow:linear-reply` |
| `manual` | 依 inventory 收斂 | markdown 操作手冊 | 獨立成品(**成套手冊改用 `sa-flow:operation-manual`**) |
| `e2e` | **逐項判 pass/fail** | 執行報告 | → 建議落成 Cypress spec(使用者決定,不自動寫) |
| `explore` | 歸納邊界與隱含規則 | 現況行為分析 md | → `sa-flow:explore` / `sa-flow:system-analysis` / `sa-flow:requirement` |

**收尾條件**(全部成立才算完成):證據檔存在且 `_meta.targets_failed` 已處理、
產出檔已寫到指定路徑、`.tmp/live-drive/<session>/` 的暫存已依需要複製或清理、
交棒對象已明確告知使用者。

**瀏覽器收尾**:agent 只關自己的分頁;主 session 若為本次手動起過任何 Chrome(含 9222 附掛),在回報完成的同一輪關掉並驗證(`curl -s -m 2 http://127.0.0.1:9222/json/version` 無回應、無 `puppeteer_dev_chrome_profile`／`claude-shared-chrome` 行程)。

## Red Flags

**禁止捷徑**:主 session 自己開瀏覽器(一律派 `browser-surveyor`)、改派 `general-purpose` 頂替(它繼承主 session 的模型,瀏覽器操作量大,成本遠高於專用 agent)、單次派工塞超過 8 個 targets(agent 有 150 次工具呼叫的 context 預算,超過會停下要你拆批)、把 agent 回傳的截圖與
network 原文 Read 進主 context(隔離失效)、**跳過 Step 1 安全判定直接派工**(agent 會降唯讀,
該操作的畫面拍不到,且主 session 放棄了自己的把關責任)、在 production 做變更動作、
把截圖直接寫到 workspace 外(工具會拒絕,必先落 `.tmp/` 再複製)、把帳密寫進產出文件。

## References

- `${CLAUDE_PLUGIN_ROOT}/agents/browser-surveyor.md` — 實機勘察 agent(Step 2 派它;環境安全在其定義內獨立再判一次)
- [browser-bootstrapping.md](references/browser-bootstrapping.md) — MCP 連線、連線排錯、登入、截圖落地
- [modes.md](references/modes.md) — 四模式觀察重點與產出模板
- [safety.md](references/safety.md) — 環境判定與唯讀降級
