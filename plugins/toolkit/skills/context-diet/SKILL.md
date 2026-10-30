---
name: context-diet
description: 量測並壓縮每個 session 無條件進 context 的設定量——CLAUDE.md、全域／scoped rules、MEMORY.md 索引、skill／agent description、plugin 與 MCP——先用 transcript 找出沒在用的，再把重複、程序、事故史搬到按需讀取的 refs。量測自動、砍什麼逐項列證據由使用者定奪。Use when 使用者說「context 太肥」「每次 session 花太多 token」「瘦身」「壓縮 rules」「哪些 skill 沒在用」，或輸入 /context-diet。
---

# Context 減重

**與內建 `/doctor` 分工**：量測、找沒在用的擴充、CLAUDE.md 可推導內容修剪、改延遲載入這四件事
`/doctor` 已經做——**先跑 `/doctor`，再跑本 skill**，Task 1 的量測與 Task 2 的「0 次呼叫」判定可直接引用它的報告。
本 skill 獨有的是搬遷規則（程序／對照表／事故史搬 `refs/`、紅線不得只留在 refs、同 `paths:` rule 合併、
MEMORY.md 索引壓行、agent description 壓字）與 Task 3-4 的提案／套用紀律（grep 所有指路處、Codex 鏡射同步、plugin bump）。

每個 session 開場就吃掉的 token 有五個來源：CLAUDE.md、無 `paths:` 的 rules、MEMORY.md 索引、
所有 enabled skill 的 description、所有 agent 的 description＋tools。這些**每次都付**，
而且大多是慢慢長出來的重複與程序敘述。本 skill 先量、再用使用證據決定砍什麼。

## 參數

| 形式 | 意圖 |
|---|---|
| `/context-diet` | 量測 → 提案 → 使用者勾選 → 套用 → 重量 |
| `/context-diet --measure` | 只出量測表，不提案 |
| `/context-diet --days 60` | 使用證據的統計視窗（預設 28 天） |

## Task 1：量測

```bash
"$(command -v python3 || command -v python)" "${CLAUDE_SKILL_DIR}/scripts/measure.py" --project <專案根> --days 28
```

輸出兩張表：**載入量**（每項的字元與估 tokens，scoped rules 附 `paths:`）與**使用證據**
（近 N 天 transcript 內 Skill 呼叫、subagent 派發、MCP server 呼叫、使用者 slash 次數）。
把「每 session 無條件 ≈ N tokens」那行當基線抄下來，最後要對照。

**證據只涵蓋本機 transcript**——多台機器工作的人，另一台的使用看不到，
「0 次」只代表下限，砍之前要問。預設只掃 `--project` 的 transcript；判 user 層 skill 或 plugin 去留時加 `--all-projects`。

## Task 2：找候選（依「省下 tokens ÷ 工」排序）

逐項對照，每條列出**證據**（字元數、呼叫次數、重複的對方檔案）：

| 形狀 | 判準 | 處置 |
|---|---|---|
| CLAUDE.md 有段落是某條 rule 的複本 | 兩邊講同一件事 | CLAUDE.md 留一行指路，rule 保留 |
| 全域 rule 寫了程序／對照表／事故史 | 超過「不讀就出事」的紅線 | 搬到 `.claude/refs/<同名>.md`，rule 留紅線＋一行指路；**紅線不得只留在 refs** |
| 只在某目錄才成立的全域 rule | 內容提到特定路徑 | 加 `paths:` frontmatter 變 scoped |
| 兩條 scoped rule 同 `paths:` 且主題相鄰 | 例：docs 慣例＋docs 圖譜 | 合併成一檔一節 |
| MEMORY.md 索引過長或結構有問題 | 索引只決定「要不要開 topic 檔」 | 交給 `/tidy-memory`（門檻與連結檢查以它為準），本 skill 不另訂 |
| plugin 整組 N 天 0 呼叫（skill 與 agent 都 0） | 使用證據 | 提議在專案層 `enabledPlugins` 設 false，要用時 `/plugin` 臨時開 |
| agent description 超過 ~120 字 | 職責清單是給 agent 本體讀的 | 壓成「做什麼、誰派發、不做什麼」 |
| MCP server N 天 0 呼叫 | 使用證據 | 提議停用（claude.ai 連接器要到網頁端關） |
| 只靠 slash 手動叫、且模型不需辨識的 skill | 使用證據＋性質 | 加 `disable-model-invocation: true`（description 不進 system prompt） |

**不要動的**：plugin 自帶的 SessionStart 注入（fork 才能改）、內建工具 schema、
MCP deferred 工具名（只能靠停 server）。

## Task 3：提案並等使用者勾選

用一張表列候選：`# | 動作 | 省約 tokens | 證據 | 風險`，再問要做哪些。
砍 plugin／MCP／skill 一律由使用者定奪；純重複（CLAUDE.md 對 rule 的複本）可標「建議直接做」。

## Task 4：套用

- 改 rule 或 CLAUDE.md 時，先 `grep -rn` 該檔名／段落標題找**所有指路處**（其他 rule、skill、
  refs README、平行檔如 `AGENTS.md`），一起改；刪檔前必查引用。
- 搬進 refs 的內容要**先確認 refs 沒有現成的**（常常已經有一份，rule 那份才是複本）。
- 有 Codex 鏡射（`.agents/`、`.codex/`）的專案，改完跑該專案的同步腳本，不手改副本。
- 改 plugin 內的 agent description 要 bump 版本＋CHANGELOG；改完驗 frontmatter 仍可解析。

## Task 5：重量並回報

再跑一次 measure，回報 `前 → 後（−N%）` 逐項與合計；達不到目標時說明剩下的大頭是什麼、
為什麼不建議再砍（例如 skill 清單本身，只能靠減 skill 數量）。

## 判準速記

- **每次載入的只放紅線**：短句、祈使句、不讀就出事。程序與對照表是 refs 的事。
- **索引不是內容**：MEMORY.md 一行只需要讓人決定開不開檔。
- **description 是觸發條件不是說明書**：做什麼、誰派發、不做什麼，三句夠了。
- **0 次是下限不是證明**：砍之前看另一台、問使用者。
