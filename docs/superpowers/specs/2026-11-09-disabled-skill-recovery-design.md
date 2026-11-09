# 停用 skill 補救機制（第二版）設計

日期：2026-11-09 ｜ 影響：toolkit（hooks）、各 plugin 的 SKILL.md frontmatter、`scripts/ci/validate.py`

## 起因與意圖

/doctor 依使用次數建議停用少用的 plugin／skill，寫成 `enabledPlugins: false`（常寫在 user 層，所有專案一起失效）或 `skillOverrides: "off"`。
被停用的 skill 從清單消失，之後使用者開口要、或 agent 做到一半需要時，agent 不知道它存在，通常自己硬做完（做得較差但不失敗），沒有任何訊號。

toolkit 0.17.0 已上線第一版：SessionStart 列出所有明確停用的項目、附重開指令，agent 讀檔照做後再問要不要重開。它有兩個缺陷：

1. **分不出「少用被關」與「刻意不要」**：兩者都是 `false`，agent 會繞過使用者刻意的決定去用（例：blog 專案刻意停用 plugharbor 的 blog plugin，因為專案自帶 write-post）。
2. **永遠注入、無法消掉**：沒重開就每個 session、每個專案都注入，使用者回「不要」也沒用；清單越長越吃回 /doctor 省下的 context，也會被習慣性忽略。

「遇到情境再去找 skill」若交給 agent 自己判斷幾乎不會發生（看不到就不會想到），所以情境判斷交給程式做。

## 目標

- 使用者訊息對得上某個停用中 skill 時，當輪提示 agent 那個 skill 存在（主力）。
- agent 處理途中需要時，有一行名稱可對（保底）。
- 使用者回「不要」之後，同一項不再被任何一層提起。
- 沒有停用項目時零輸出；有停用時常駐成本壓到一行。

## 非目標

- 不處理從沒啟用的 plugin（專案層 plugin 刻意只裝在特定專案，如公司 workspace 自帶 sdlc；列出來會誘導重複）。這類照舊靠 user 層 `engineering.md`「能力缺口」段在缺能力時按需查 marketplace 目錄。
- 不比對 agent 自己的工具呼叫或中間產出（PreToolUse 層級的比對）。
- 不支援 Codex、pi、agy（只讀 Claude Code 的設定）。
- 不改 /doctor 本身（內建功能）。

## 反目標（做到也算失敗）

- 比對到就自動重開或自動執行 skill。
- skill description 變長（description 常駐在清單裡，repo 規則禁止變胖）。
- 使用者已回「不要」的項目又被提起。
- 誤觸頻繁到使用者開始無視提示。

## 已決定的部分

### 1. 觸發詞來源

- 新增 SKILL.md frontmatter 欄位 `triggers`：字串陣列，寫使用者會說的**片語**（如「開始錄音」，不寫「錄音」這類短詞）。
  2026-11-09 用 `claude -p --plugin-dir` 實測：自訂欄位不進 skill 清單（清單只顯示 description），不增加常駐成本。
- hook 的比對詞 = `triggers` ∪ description 中「」括起的片語。已有「」觸發詞的 skill 可以不寫 `triggers`；目前 23 個 model-invocable 的 skill description 抓不到「」，需要補 `triggers`。
- `disable-model-invocation: true` 的 skill 不參與比對（只能手動叫，提示也無法讓 agent 叫用）。

### 2. 情境比對（UserPromptSubmit，主力）

- 只比對「停用中且不在忽略清單」的 skill：plugin 明確 `false` 時它底下所有 skill；或 `skillOverrides: "off"` 的單一 skill。停用狀態依 user → project → local 設定算（同 0.17.0）。
- 比對到時注入，每個 skill 一行，最多 3 個：skill 名、SKILL.md 路徑（marketplace clone 內），以及處理方式：
  **先用 AskUserQuestion 問再用**（使用者已拍板）。選項：
  - 「用它並重開」：讀 SKILL.md 照做，並跑重開指令（plugin：`claude plugin enable <p>@plugharbor --scope <寫 false 的那一層>`；skill：刪掉對應 `skillOverrides` key）。
  - 「只這次用」：讀 SKILL.md 照做，不改設定。
  - 「不要」：寫進忽略清單，不用。
- 沒比對到就零輸出。

### 3. 開場一行（SessionStart，保底）

- 取代 0.17.0 的完整清單：只注入一行名稱，例：`[toolkit] plugharbor 停用中：browser-docs、workspace:agent-orchestration（用到前先問使用者；細節見 <狀態檔>）`。
- 細節（路徑、重開指令、每個 plugin 的 skill 清單）寫進狀態檔，agent 需要時才讀。
- 忽略清單內的項目不列；全部被忽略或沒有停用時零輸出。

### 4. 忽略清單

- **單位跟著停用的單位走**（使用者已拍板）：plugin 整個被停用 → 忽略整個 plugin（它底下的 skill 都不再提起，開場那行也不列它）；單一 skill 被 `skillOverrides` 關掉 → 只忽略那個 skill。
- **範圍一律只在當下專案**（使用者已拍板），以專案路徑為 key；即使停用寫在 user 層，其他專案遇到仍會問。
- 由 hook 腳本提供寫入指令（例：`disabled-skills.py ignore <項目>`），注入文字帶上完整指令，agent 不手改 JSON。
- 項目一旦重新啟用，hook 自動把它從忽略清單移除（之後若又被 /doctor 關掉，會重新提示）。

### 5. 同一 session 只問一次

- 同一個 session 裡，同一項（plugin 或 skill，單位同上）提示過就不再注入，不論使用者選了什麼。用 hook 輸入的 `session_id` 記狀態。
- 起因：選「只這次用」或「用它並重開」（重開要下個 session 才生效）後，項目仍是停用，不去重的話每則命中訊息都會再問一次。

## 我的判斷（未經使用者確認，可推翻）

- 同一 session 只問一次（見第 5 節），由 builder check 提出後自行決定。
- 狀態檔與忽略清單放 `~/.claude/disabled-skills/`（toolkit 的狀態一律放 `~/.claude/` 下，不寫進 plugin 目錄）。
- 比對時 ASCII 不分大小寫、全形半形不正規化；最多注入 3 個 skill。
- 兩個事件用同一支腳本、以子命令區分（`session`／`prompt`／`ignore`）。
- `validate.py` 新增檢查：`triggers` 若存在必須是字串陣列、每項至少 4 個字元。
- 版號：toolkit minor（0.18.0）；改到其他 plugin 的 SKILL.md（補 `triggers`）各自 patch bump。

## 約束

- hook 一律 fail-open（任何錯誤 exit 0、無輸出），`run-py.sh` 包裝，timeout 5 秒；UserPromptSubmit 每則訊息都會跑，要在 0.5 秒內完成。
- 公開 repo：注入文字可含使用者本機路徑（執行期產生），但 repo 內的文件、測試、範例不得出現個人絕對路徑。
- 每個 skill 改動照版號同步規則：CHANGELOG、plugin.json、marketplace.json、根 README 同一個 commit。
- `toolkit/README.md` hook 表與 `docs/agent-parity.md` 同步。

## 留給實作者

- 狀態檔格式、是否快取比對詞（每則訊息重掃 ~70 個 SKILL.md 若太慢再快取）。
- 23 個 skill 的 `triggers` 用詞（以各 skill 的 description 與實際使用語氣推得；寫完列給使用者過目）。
- 測試案例設計，至少涵蓋：比對命中與未命中、忽略清單生效與自動移除、忽略單位（plugin／skill）與只限當下專案、同 session 不重複注入、`disable-model-invocation` 不參與、fail-open。

## 驗收

- toolkit hook 測試全過（含新增案例），`validate.py` 通過。
- 實機：本機把一個 plugin 設 `false` 後，用 `claude -p --plugin-dir plugins/toolkit` 驗：開場只有一行；送出含其觸發詞的訊息時注入提示；寫入忽略清單後兩層都不再出現。
