# 派工：走 API 還是訂閱

SKILL.md 第 2～4 步與第 6 節的細則。起因：Agent subagent 跑在主 session 的 process 裡、永遠扣主 session 的訂閱；pane worker 依 `toolkit:agent-dispatch` 一律走訂閱。要讓 `claude-api`（API key 計費）接得到工作，只能經 agent-dispatch 的背景 worker（`bg.mjs`）。

## 誰經背景 worker

| 工作 | 派法 |
|---|---|
| 實作（`implement`）、QA／走查（`qa`）、文件（`docs`）、機械類（`mechanical`） | 背景 worker，`--type` 依路由表派 |
| 規劃、架構、設計、關鍵審查、`lifecycle:domain-advisor` 分流 | 維持訂閱：主控自己做或 Agent subagent；審查照 SKILL.md 第 3 步 |

路由表決定第一家（standard 是 claude-api、cheap 可能是 agy）；額度用完或 key 失效時腳本封鎖那一家、在同一個 worktree 改派下一個候選，主控不用自己重派。

下列情況不走背景 worker，改用 Agent subagent（現行做法），帳本與回報寫 `退回訂閱：<原因>`：

- 沒裝 `toolkit`（叫用不到 `toolkit:agent-dispatch`）→「沒裝 toolkit」。
- 環境沒有 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD` →「沒設 API key 來源」。
- `start` exit 75（候選全被濾掉）→「候選全被濾掉」。
- 工作要用 MCP（瀏覽器、DB）、要再開 subagent、要中途問人或 `git fetch` →「需要 <哪一項>」。背景 worker 只放行 Bash 與編輯，git 遠端傳輸被關掉。

`start` 報「並行已達上限」不是退回的理由：去做空檔工作，等一個 worker 結束再派。`start` 其他報錯（用法、找不到腳本、worktree 問題）是**工具故障**：退回 Agent subagent，回來報告最前面標 🔴 附錯誤訊息。

## 怎麼派

先叫用 `toolkit:agent-dispatch` 拿它的 Base directory，`BG=<該目錄>/scripts/bg.mjs` 記進帳本（context 壓縮後照用，不 glob 外掛快取）。工作目錄一律放帳本資料夾的 `bg/` 底下：同一層算並行上限。

1. 第一輪：在第 1 步開好的單元 worktree 跑，不另開分支：

   ```bash
   node "$BG" start --worktree <單元 worktree> --name <段>-r1 --type implement --timeout <秒> --ws <帳本資料夾>/bg/<段>-r1 <prompt 檔>
   ```

   - 原本派 Agent 定義的純 Bash／編輯類（如 `lifecycle:developer`）加 `--agent <plugin>:<agent>`；要 MCP 的定義（如 `lifecycle:qa-runner-ui`）照上表不走背景 worker。`--model`／`--effort` 以 `start` 帶的為準（`--type` 一律是路由表等級）。機制與狀態欄位見 agent-dispatch 的背景 worker 文件（該 skill 目錄下的 background-worker）。
   - 套不上時（非 claude 系、plugin 在 worktree 沒啟用）腳本退成 prompt 叫 worker 讀定義檔，`status.json` 記 `agentApplied: false`。所以 prompt 一律寫明「先讀 <定義檔絕對路徑> 照它做」。
   - prompt 照第 2 步：自足、含第 0 節授權範圍、重測試用 `test-lock.sh` 包。結果檔路徑與「寫完就停」腳本會自己加。
   - `--timeout` 預設 3600 秒；整段實作估得比這長就加大。
   - worker 跑的期間主控不改這個 worktree。
2. 等結束：用 Bash 的背景執行跑 `node "$BG" wait --ws <ws> --timeout <同上加 300>`，結束時會收到通知；期間做空檔工作，不輪詢 `status`。
3. 判讀 `status.json`（`wait` 印出的 JSON）：
   - `done`：讀 `result.md`。寫的是「待決」或「未完成」（worker 遇到決策就停）時不送審：照 SKILL.md 第 4 節判斷是停下條件還是主控裁決（記成待確認），補上決定後用 `--continue` 續派。真的完成才進審查；worker 的 commit 已在單元分支上，沒有東西要另外合併回來。
   - `quota`：候選都用完了；照 `退回訂閱：額度用完` 改派 Agent subagent。worktree 可能有半成品，prompt 加一句「worktree 可能留有前一位沒做完的改動，先看 git status 與 git log」，並附上一輪 `result.md` 路徑與目前 SHA。
   - `failed`：看 `tail`；同一段失敗兩次就換人診斷。
4. 修正輪（第 4 步「交回原實作者」）：

   ```bash
   node "$BG" start --continue <帳本資料夾>/bg/<段>-r1 --name <段>-r2 --ws <帳本資料夾>/bg/<段>-r2 <修正 prompt 檔>
   ```

   上一輪是 claude 系就接續同一個 session（`status.json` 的 `resumed: true`）；改派到別家或 session 不見時是新 session，所以修正 prompt 照第 4 步自足：審查發現、通過條件、目前 SHA、上一輪 `result.md` 路徑。

帳本每個 worker 記一行：ws 路徑、單元 worktree、輪次。context 壓縮或換 session 接回時，先對帳本裡還沒收尾的每個 ws 跑 `node "$BG" status --ws <ws>`：`running` 就重掛第 2 步的 `wait`、不重派、不動那個 worktree；其他照第 3 步判讀。還有 running 的背景 worker 時不 self-rotate（`references/autopilot.md`「換新」的前提）。

審查的作者 CLI：取最後一輪 `status.json` 的 `cli`；任一輪的 `attempts` 顯示有改派（前一家可能也動過檔），`route.mjs reviewer` 挑出的審查者不能和動過檔的任何一家同家族，同家族就退回同家審查並照實寫。`bg/` 底下的工作目錄收工時列進回來報告的暫存清單，不在無人值守中途刪。

## 回報與計數

- 每次派工，帳本那行照抄 `start` 的第一行 `[bg] 交給 <cli>（<模型>／<等級>），理由：<類型>`；結束時 `status.json` 的 `line` 不同（有改派）就改抄 `line`。退回訂閱的寫 `退回訂閱：<原因>，交給 Agent subagent（<agent 類型>／<模型>）`。審查照抄 `ask.mjs` 的第一行。
- 計數看實際跑完的那一家：`claude-api` 算 API；`claude`、Agent subagent 算訂閱；codex、agy、pi 算其他家。審查也算，主控自己做的不算。每次 `start`（含 `--continue` 的修正輪）、每次 subagent、每次審查各算一次。
- 回來報告「驗證結果」那節加一行：`本輪派工：API <n>／訂閱 <m>（其中退回訂閱 <k>：<原因與次數>）／其他家 <x>`；`k` 含在 `m` 裡。
