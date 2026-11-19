# agent 暫存生命週期（toolkit）設計

日期：2026-11-19。狀態：設計。
起因：2026-11-19 某 workspace 盤點出 AI agent 留在各專案的暫存約 9.3 GB（規格鏈 worktree 1.9 GB、978 MB 測試 log、含 cookies 的拋棄式 Chrome profile、成品只在 `.tmp` 的工作區），沒有任何機制提醒，只能事後人工清。
討論 checkpoint：`.tmp/20261119-agent-scratch-lifecycle/checkpoint.md`（本機，不進版控）。

## 意圖

agent 開的暫存不再無聲累積：建立時就記下是誰、為什麼開、能留多久；session 結束時記帳；下次開場把過期的提議給使用者刪；定期全區掃描兜住沒標記、沒正常結束的。**刪除的最後把關一律是使用者**，hook 與腳本本身不刪任何東西。

## 目標／非目標／反目標

- 目標：專案 `.tmp/<單位>/`、`.superpowers/<單位>/` 從建立到刪除有帳可查；過期的會被問到；worktree、成品檔、並行 session 在用的不會被誤刪。
- 非目標：build 產物（另案評估 kondo）、`docs/會議/**/*.assets/` 這類不在暫存區的檔（由各 skill 收尾時問，sdlc 2.115.0 已加）、session scratchpad（harness 自己清）。
- 反目標：結束時自動刪（已排除，理由見 checkpoint）；同一天被反覆打斷；把交接檔在接手前提議刪掉；刪掉 git worktree 的資料夾弄壞中繼資料。

## 已拍板（使用者）

四段組合（checkpoint，2026-11-19）：建立時標記 → 結束時只記帳 → 下次開場提議 → 兜底全區掃描。`/clear` 留下的交接檔開場不列。

本次 AskUserQuestion 裁決（2026-11-19，皆選推薦）：

| 題目 | 裁決 |
|---|---|
| agent 沒補期限時的預設 | 7 天，從最後一次有 session 用它起算 |
| 開場提議的呈現 | 一題 AskUserQuestion 複選，依大小列前 4 個（路徑、大小、用途、閒置天數、警示），勾的刪、沒勾的留；其餘下次再問 |
| 提醒頻率 | 每專案每天最多一次；沒勾（保留）的 7 天內不再列 |
| 全區掃描觸發 | 距上次掃描滿 7 天，或家目錄所在磁碟可用空間不到 20 GB，開場提議「要不要掃」，同意才跑；沒標記的只列 14 天以上沒動的 |
| `/clear` 交接檔 | 開場永不列；全區掃描時 14 天沒動才標「交接檔」列入複選 |

## 做法比較

1. **單一 hook 腳本＋中央帳本（採用）**：`hooks/scratch-ledger.py` 一支腳本處理 PostToolUse（標記）、SessionEnd（記帳）、SessionStart（提議），同檔帶 CLI 子命令（`mark`、`keep`、`sweep`）。帳本是 `~/.claude/scratch-ledger/ledger.jsonl` 只追加。暫存資料夾本身不寫任何檔。
2. 每個暫存資料夾內放標記檔（`.scratch.json`）：人看得到、跟著資料夾走；但 worktree 裡多一個未追蹤檔、skill 工作區被打包時會帶進去，SessionEnd 還得掃全專案找標記，超出 1.5 秒預算的風險高。不採用。
3. 只靠規則叫 agent 自己寫標記：規則常被忽略（本 repo 多次改成機制的起因，如 toolkit 0.29.0），不採用；hook 自動標記 session，只把「用途、期限」交給 agent 補。

## 設計

### 單位與範圍

路徑中第一個名為 `.tmp` 或 `.superpowers` 的目錄，往下一層就是一個「暫存單位」（`<專案>/.tmp/20261119-foo/`、`<專案>/.superpowers/brainstorm/`）。`.tmp` 下的裸檔不算單位（tmp-scratch 規則禁止裸檔）。

### 帳本（技術決策）

`~/.claude/scratch-ledger/ledger.jsonl`，一行一事件，讀取時依 `dir` 摺疊：

```json
{"ts":"2026-11-19T10:00:00+08:00","ev":"mark","dir":"/abs/.tmp/20261119-foo","session":"<sid>","created":"…"}
{"ts":"…","ev":"meta","dir":"…","session":"<sid>","purpose":"規格鏈 worktree","ttl":"7d"}
{"ts":"…","ev":"touch","dir":"…","session":"<sid2>"}
{"ts":"…","ev":"end","dir":"…","session":"<sid>","reason":"other","size":123456,"partial":false}
{"ts":"…","ev":"keep","dir":"…","until":"2026-11-26"}
```

- 只追加（`O_APPEND` 單行寫入），並行 session 不用鎖；摺疊時最後一筆為準。
- `ttl` 只收 `1d`、`7d`、`handoff`；沒有 meta 視為 `7d`。
- 其他狀態：`~/.claude/scratch-ledger/state.json`（`asked`: {專案根: 日期}、`swept`: 上次掃描或婉拒時間）；`sessions/<sid>.seen`（本 session 已處理過的單位，PostToolUse 節流用，SessionEnd 刪掉）。
- 理由：中央帳本讓 SessionStart 不必掃目錄、SessionEnd 只處理自己的單位；放 `~/.claude` 下同 `feedback-loop/`、`context-reminder/` 慣例，不進專案版控。帳本瘦身（丟掉資料夾已不存在的紀錄）只在 `sweep` 做。

### 1. 建立時標記（PostToolUse `Write|Edit|MultiEdit|NotebookEdit|Bash`）

- Write 類取 `tool_input.file_path`；Bash 以正規式從指令抓含 `.tmp/<名>`、`.superpowers/<名>` 的字樣，相對路徑以 `cwd` 解開。只處理工具跑完後確實存在的資料夾。
- 單位已在 `sessions/<sid>.seen` → 直接結束（每個 session 每個單位只處理一次）。
- 帳本沒有這個單位 → 寫 `mark`（`created` 取資料夾建立時間，取不到用現在），並以 `additionalContext` 注入一次：「新暫存 `<單位>` 已記到本 session，期限預設 7 天（從最後使用起算）；用一行補上用途與期限：`python3 <腳本> mark <單位> --purpose '<一句話>' --ttl 1d|7d|handoff`，交接檔用 handoff」。
- 帳本已有（別的 session 開的，或本 session 之前開的）→ 靜默寫 `touch`。
- 抓不到的（腳本裡建的資料夾、`cd .tmp && mkdir x`）不補救，交給全區掃描。

### 2. 結束時記帳（SessionEnd）

- 從帳本找本 session 有 `mark`／`touch` 的單位，對仍存在的寫 `end`（帶 `reason` 與大小）。
- 大小用 `os.scandir` 遞迴加總，全部單位共用 0.5 秒期限（含 python 啟動兩次的開銷仍留餘裕），超時記已算到的數並標 `partial`。理由：Claude Code 的 SessionEnd 全部 hook 共用 1.5 秒，plugin 設的 timeout 不會放寬預算；Codex SessionEnd 預設 1 秒、上限 3 秒。
- 不刪任何東西。刪掉 `sessions/<sid>.seen`。

### 3. 下次開場提議（SessionStart `startup`）

只在 `source=startup`；`resume`、`clear`、`compact` 是同一件工作的延續，不提。`AGENT_DISPATCH_UNATTENDED=1`（無人值守 worker）不提。

候選＝專案根（`CLAUDE_PROJECT_DIR` 或 `cwd`）以下、仍存在、且同時符合：

1. 所有碰過它的 session 都已 `end`（還有 session 在用的不列，涵蓋並行 session 共用 `.tmp/plans/` 的情況）。
2. 不是交接檔：`ttl` 不是 `handoff`、最後一筆 `end` 的 `reason` 不是 `clear`、資料夾頂層沒有 `handoff.md`。
3. 已過期：最後活動時間＋期限 < 現在。最後活動＝帳本最後一筆 mark／touch／end 與資料夾本身及頂層項目 mtime 中最晚者（防 hook 沒抓到的使用）。
4. 沒有未到期的 `keep`。
5. 這個專案今天還沒問過（`state.asked[專案根] != 今天`）。

有候選時依帳本大小排序取前 4 個，各自檢查警示：

- **worktree**：單位內有 `.git` 檔（`gitdir:` 開頭）→ 刪法改 `git -C <主 repo> worktree remove <路徑>`，有未提交改動就停下報告。
- **成品檔**：單位內（深度 3、最多掃 2000 項）有 `.pptx .docx .xlsx .pdf .key .mp4 .mov .wav .flac .m4a` → 標「含成品檔，先確認已搬走」。

注入的指示：先處理使用者第一個請求，回合收尾前用**一題** AskUserQuestion（`multiSelect: true`）：label 是資料夾名，description 寫大小、閒置天數、用途、警示；勾的刪（一般資料夾用單獨一條 `rm -rf <絕對路徑>`，toolkit 的 `rm-scratch-allow` 會自動核准；worktree 用上面的指令），沒勾的與使用者略過的跑 `python3 <腳本> keep --root <專案根> <路徑…>`（7 天內不再列；不帶路徑也要跑一次，記下今天已問過）。超過 4 個時提一句「其餘 N 個（共 X）下次再問」。

理由：今天是否已問過由 agent 跑 `keep` 時才記，hook 注入時不記——`claude -p` 這類沒人在場的 session 不會問、也就不會吃掉當天的額度。

### 4. 兜底全區掃描（SessionStart 提議，`sweep` 子命令執行）

- 觸發：同一個 SessionStart，`state.swept` 距今滿 7 天（或從沒掃過）或 `shutil.disk_usage(家目錄)` 可用不到 20 GB → 注入「提議跑全區掃描（約數十秒）」；同意就跑 `python3 <腳本> sweep`，婉拒跑 `sweep --skip`（兩者都記 `swept`，7 天後再提；磁碟吃緊時每天最多提一次）。若同時有開場候選，掃描提議排在其後、一樣用一題問。
- 掃描範圍：`~/.claude/scratch-ledger/config.json` 的 `roots`（可選）∪ 帳本出現過的專案的上一層 ∪ 目前專案的上一層；每個根掃 `*/.tmp/*`、`*/.superpowers/*`。理由：不寫死任何個人路徑，裝好就能從帳本學到專案在哪。
- 列出：
  - 開場候選條件 1–4 成立者（跨所有專案，不看今天問過沒）。
  - **沒標記**（帳本沒有）且 14 天以上沒動。
  - **session 沒正常結束**（有 mark／touch 沒 end）且閒置超過期限。
  - **交接檔** 14 天以上沒動。
- 輸出：依大小排序的 Markdown 表（路徑、大小、閒置天數、類別、用途、警示），`--json` 給機器讀。agent 照開場同樣的複選題問前 4 個，沒勾的 `keep`。
- 同時瘦身帳本：資料夾已不存在的紀錄丟掉（寫暫存檔再 `os.replace`）。

### 失敗處理

hook 一律 fail-open（例外寫 stderr、exit 0），照 toolkit 既有 hook。帳本行解析失敗就跳過該行。

### 各 CLI 對等

- Claude Code：hooks.json 註冊 PostToolUse、SessionEnd、SessionStart `startup`。
- Codex：會載入 plugin `hooks/hooks.json`（經 `/hooks` 信任後）；Codex 有 SessionEnd（主 thread、1 秒預設）、PostToolUse 的 shell 工具名也是 `Bash`、支援 `additionalContext`。腳本對沒有 `reason` 的 payload 照樣運作。**未驗證**（同 tower 系列），在 `docs/agent-parity.md` 標明。
- agy、pi：沒有對應 hook；`sweep` 是純 CLI，可手動跑。

### 與既有規則的關係

- `workspace:tmp-scratch` 管命名、裸檔、當輪清與「worker 不自刪」；本設計不改它的規則，只把「忘了清」的兜住。tmp-scratch 是否要加一句「hook 會提示補用途與期限」列為主控待確認（不在本次授權範圍）。
- `rm-scratch-allow.py` 照舊：刪除指令寫成單獨一條 `rm -rf` 就自動核准。
- `retro-due-reminder.py` 的「SessionStart 注入提議、使用者婉拒就不再提」寫法沿用。

## 驗收

- 單元測試 `hooks/tests/test_scratch_ledger.py`（pytest，照 toolkit 慣例）：標記／節流／touch、Bash 路徑抽取、SessionEnd 記帳與部分大小、開場候選五條件與排序、worktree 與成品檔警示、交接檔排除、keep 與每日一次、掃描分類與帳本瘦身、fail-open。
- 實觸發：在拋棄式目錄起 `claude -p`（濾掉 `HERDR_*`、`HC_*`），確認 PostToolUse 寫 mark 並注入、SessionEnd 寫 end；改帳本時間讓它過期後再起一次，確認 SessionStart 注入提議。
- 掃描對其他專案唯讀：`sweep` 不刪檔；實跑時只讀。

## 實作者的決定（builder check 後補）

- 注入文字裡的 `<腳本>` 由 hook 以 `__file__` 解出絕對路徑；plugin 升級後舊快取路徑可能失效，屬既有 hook 共同限制，不另處理。
- Bash 指令中提到、且工具跑完仍存在的單位都算使用（`ls`、`cat` 也寫 touch）；被 `rm` 刪掉的自然因不存在而略過。
- `mark`／`keep` 的路徑可給絕對或相對（以呼叫時 cwd 解開），一律正規化成單位路徑；不是單位就報錯 exit 2，不寫帳本。
- payload 缺 `session_id` 就整支靜默結束，不寫帳本（Codex 欄位差異的退路）。
- session 被 kill、當機沒觸發 SessionEnd 的單位刻意不進開場候選，只由全區掃描以「session 沒正常結束」處理。
- 多個 SessionStart hook 的 `additionalContext` 由 Claude Code 串接；實觸發驗收用已安裝的完整 toolkit 跑，順便確認並存。
- 版號、CHANGELOG、README、`docs/agent-parity.md`、`docs/feature.md` 一併更新。

## 留給實作者

- Bash 路徑抽取的正規式細節、事件欄位命名、輸出文案。
- 期限、門檻寫成腳本常數（7 天、14 天、20 GB、4 個、0.5 秒、2000 項），不開設定。
