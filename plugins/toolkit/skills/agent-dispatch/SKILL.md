---
name: agent-dispatch
description: 把工作交給另一個 agent CLI（claude、codex、agy、pi）：依任務類型與難度查表挑 CLI＋模型＋思考等級，額度用盡自動改派；短問答以唯讀模式一次問完，長任務在 herdr pane、Ghostty 分割或背景 worktree 讓對方做完交回結果檔；需要時挑不同家族的模型審查。Use when 使用者說「丟給 codex 問」「問問 claude／agy 的看法」「要第二意見」「交給 agy／pi 做」「X 這週省著用」，或輸入 /agent-dispatch。
argument-hint: "[對象] <任務>"
---

# 跨 CLI 派工

你可以是 claude、codex、agy、pi 其中任何一個入口（主控）。四家對等，共用 `references/routing.json` 這份路由規則。

腳本都在本 SKILL.md 旁的 `scripts/`；在非 Claude 入口，`${CLAUDE_SKILL_DIR}` 換成本 SKILL.md 所在的目錄。

## 1. 選對象

- 使用者指定對象就照做（`--to`）。
- 沒指定時，判斷任務類型，交給腳本查表（`--type`），**直接派，不先徵詢**：

  | 等級 | 類型 |
  |---|---|
  | top | `plan`、`architecture`、`review-critical` |
  | standard | `implement`、`research`、`qa`、`debug` |
  | cheap | `docs`、`format`、`mechanical` |

- 查表會濾掉 agent-mesh-check 最近一次沒通過的 CLI，以及額度封鎖中的 CLI。派出去一律帶明確的模型與思考等級，不繼承你自己的模型。
- 回報時照抄腳本第一行「交給 <cli>（<模型>／<等級>），理由：…」，讓使用者知道花了哪一家的額度。
- 只想要另一家觀點、你本身是 pi、pi 也登入了那家：用 pi 自己的子代理換模型比較輕。需要 codex 或 agy 工具本身（沙箱、外掛、repo 設定）時才用本 skill。
- 使用者偏好與各家實測速度見 `references/preferences.md`。

## 2. 選模式

| 任務 | 模式 |
|---|---|
| 問意見、第二看法、小型唯讀調查，幾秒到幾分鐘 | 短問答 |
| 要改檔、預估十幾分鐘以上 | 長任務 |

## 3. 短問答（一律唯讀）

1. 把 prompt 寫成暫存檔。prompt 要能獨立讀懂，自帶背景、要回答什麼、回答的格式。
2. 執行：

   ```bash
   node "${CLAUDE_SKILL_DIR}/scripts/ask.mjs" (--to <cli> | --type <類型>) [--model <m>] [--effort <e>] [--timeout 600] [--cwd <目錄>] <prompt 檔>
   ```

3. 判讀：
   - 第一行是「交給誰、用哪級、理由」，之後是對方的輸出。
   - 輸出超過 16000 字元時，全文寫進 `<prompt 檔>.out.md`，畫面只有前 4000 字元和檔案位置。需要細節再讀檔，不要整份讀進 context。
   - exit code：124 逾時、127 沒安裝、2 用法錯誤、75 所有候選都不能用（stderr 有最早解封時間）。
   - 額度用盡時腳本會自己封鎖那一家並改派下一家，stderr 會印「改派 X」，回報時一併說明。
4. 轉述時寫明是哪個 CLI 說的，不要把它的結論包裝成你自己的；它說錯的地方要指出來。

短問答一律唯讀，因為無互動模式下沒人能按確認。`ask.mjs` 會在 prompt 前加唯讀指示；claude 與 pi 只開讀檔、搜尋類工具（能自己看 `--cwd` 底下的檔案），codex 是 read-only 沙箱；agy 沒有參數層的唯讀（見 cli-notes），只靠這行指示。需要改檔的工作改用長任務，不要為了方便放寬權限。

## 4. 審查

- 下列情況要**跨家族審查**（同家換型號不算獨立）：改動碰到安全、資料、DB 結構、公開介面（路徑樣式在 `routing.json` 的 `crossReview`），或變更超過 300 行。
- 其他小改只做同家審查。
- 挑審查者：用 `route.mjs` 的 `reviewer()` 規則——top 等級候選裡第一個跟作者不同家族的。家族：claude 與 pi 是 anthropic、codex 是 openai、agy 是 google。
- 湊不到別家（都沒裝、沒登入或封鎖中）就退回同家審查，回報寫「湊不到別家，退回同家審查」，不問使用者。
- 審查用短問答（`--to <審查者> --model … --effort high`），把 diff 寫進 prompt 檔。

## 5. 長任務：依環境選一層

依序偵測，取第一個可用的：

1. **herdr**（`HERDR_ENV` 是 `1`）：看得見的 pane，步驟見下方第 6 節。
2. **Ghostty 分割**（macOS、`TERM_PROGRAM` 是 `ghostty`）：看得見的分割，用 `bg.mjs ghostty-split`／`ghostty-close`。做法與限制見 `references/background-worker.md`。macOS 自動化權限被拒時退到第 3 層。
3. **背景 worker**：看不見，只在下列條件都成立時才用，不成立就由你在目前的 session 自己做，並說明原因：
   - 工作不需要中途問人（遇到要決策就停，寫進結果檔）。
   - 只在獨立 git worktree 裡改檔，不改主線、不 push。
   - 你合併前會先讓使用者審。

   這是**信任模型、不是沙箱**：worker 有 shell 與寫檔權限（claude acceptEdits＋Bash、codex danger-full-access、agy 跳過確認），「只改 worktree」主要靠 prompt。腳本另外做兩道防線：不傳推送用 token（`GH_TOKEN`、`GITHUB_TOKEN`、`GITLAB_TOKEN`、`GLAB_TOKEN` 等），並對 worker 程序關掉 git 的遠端傳輸（push 必失敗）。

   ```bash
   node "${CLAUDE_SKILL_DIR}/scripts/bg.mjs" start --repo <repo> --name <短名> --to <cli> --model <m> --effort <e> --ws <工作目錄> <prompt 檔>
   ```

   狀態、並行上限、收工步驟見 `references/background-worker.md`。

三層共用的規則：

- prompt 必須寫明結果檔的絕對路徑，以及「寫完結果檔才算完成，寫完就停」；還要寫明已經定案的決定和已排除的方向。
- 「不要刪暫存資料夾，把要清的路徑列在結果檔」。
- 並行多個 worker 時，各自的結果檔與工作區分開，並寫明「另一個 worker 正在寫 X，不要碰」。並行上限預設 4（背景 worker 以同一個 `--ws` 上層目錄計），遇到額度錯誤或逾時就降。
- **不輪詢**。Claude worker 用 SendMessage 回報；其他 CLI 用阻塞等待（herdr `--wait`）或完工通知。背景 worker 在 macOS 等通知、用 `bg.mjs status` 看一次；其他平台用 `bg.mjs wait` 阻塞等結束。
- **完成的唯一證據是結果檔存在**。

## 6. herdr pane 步驟

指令細節見 `references/herdr-long-task.md`。

0. 前置：
   - herdr 沒裝、或升級後指令回 `protocol_mismatch`：見 reference「安裝與升級」。
   - herdr 指令不加 `2>/dev/null`，錯誤全在 stderr。
   - 在 herdr pane 裡跑拋棄式 `claude -p` 時，先濾掉 `HERDR_*` 環境變數，否則會蓋掉真正主 session 的回報。
   - **不要在 Claude Code 內啟 herdr server**：`CLAUDE_CODE_CHILD_SESSION` 會被繼承，pane 內 transcript 不落檔（macOS 用 `brew services start herdr`）。
   - 對象是 claude 時，cwd 必須是 Claude Code 開過、通過信任對話框的目錄，否則 worker 卡在對話框沒人能答。檢查腳本見 reference；不通過就請使用者先在該目錄開一次 Claude Code。
1. 在專案的暫存區開一個工作目錄，把 prompt 寫成檔案（內容照第 5 節共用規則）。**你是 Claude Code、對象是 claude 時**，先用 `ListAgents` 取得自己的位址寫進 prompt，要它寫完結果檔**之後**用 `SendMessage` 回報一句話加結果檔路徑；要用 AskUserQuestion 問人之前，也先發一則「在問：{一句話}」。送不到就在工作區寫 `undelivered` 檔，不重試。
2. 在同一個 tab 切 pane、重排，再起對方的 CLI。`pane_id` 從回傳的 `result.pane.pane_id` 讀，不要自己推算：

   ```bash
   herdr pane split --current --direction right --cwd "<cwd>" --no-focus
   python3 "${CLAUDE_SKILL_DIR}/scripts/herdr_layout.py" --main "$HERDR_PANE_ID" --label <短名>
   herdr agent start <唯一名稱> --kind <claude|codex|agy|pi> --pane <pane_id>
   ```

   - 每開一個 pane 就跑一次 `herdr_layout.py`（主 session 最大並掛「★」標籤，同 tab 最多 6 個 worker）；不手動 `--direction down`、不 `pane resize`。`--label` 第一次給即可。
   - 第 7 個起改 `herdr tab create --cwd "<cwd>" --label <短名>`，取 `result.root_pane.pane_id`，該 tab 不重排。不用 `workspace create`（使用者看不到）。
   - 起好後 `herdr pane rename <pane_id> <名稱>`。
   - 指定 agent 定義（claude／codex）：`agent start` 尾端加 `-- --agent <plugin>:<agent>`，套用其工具白名單與 model。
   - `agent start` 失敗：先 `herdr pane read <pane_id>` 留畫面，再關掉這個 pane，連同畫面摘要回報；`agent_not_ready` 多半是 cwd 問題。
3. 送出 prompt，放在背景等待：

   ```bash
   herdr agent prompt <名稱> "$(cat <prompt 檔>)" --wait --timeout 540000
   ```

   - 一定要用 `$(cat 檔)` 送出，不要用 heredoc 或裸雙引號，因為反引號和 `$()` 會在你這邊的 shell 先被執行。
   - `--timeout` 一定要搭 `--wait`：單獨給 `--timeout` 整條會被拒，prompt 根本沒送出，而且錯誤只在 stderr。
   - 送出後先 `herdr pane read <pane_id>` 確認畫面開始工作，再去等。claude worker 的 `SendMessage` 是主訊號，背景等待只是備援。
4. 判讀結果。狀態燈只是參考：

   | 回傳 | 處置 |
   |---|---|
   | `done`／`idle`，結果檔在 | 讀它，進第 5 步 |
   | `done`／`idle`，結果檔不在 | 先不關 pane，`herdr pane read` 看最後一段：在提問 → 照 `blocked`；還沒開始動（codex 常見）→ 隔幾秒查一次結果檔；只用文字收尾忘了寫檔 → 送一句「把結果寫進 <結果檔>」 |
   | `blocked`，或畫面停在提問 | 不替它回答、不重送 prompt；告訴使用者「worker『{名稱}』在問：{一句話}，`herdr agent attach <pane_id>` 進去回答」。等人答完用 reference 的輪詢 |
   | 逾時 | 不代表失敗：查結果檔，再 `herdr agent list`；仍在跑就重掛等待，不重送 |
   | `protocol_mismatch` | 不重派，worker 多半還活著；請使用者在 worker 都 idle 時重啟 server（reference「安裝與升級」） |

   claude worker 回到 idle、結果還沒到、context 已超過 250K：由你發動中途交接，步驟見 reference 與第 8 節。正在 working 或 blocked 時不插話。
5. 收工：讀完結果檔，`herdr pane close <pane_id>`，再跑一次 `herdr_layout.py --main "$HERDR_PANE_ID"` 重排。只關自己在第 2 步開的 pane，不用「清單上沒別人」推論安全，也不要 `herdr workspace close`（會連使用者與你一起關）。最後把結果檔列出的暫存路徑確認都在本次工作區內，一次清掉。

## 7. 額度

- 自動：`ask.mjs` 與背景 worker 遇到額度錯誤會封鎖那一家到重置時間（抓不到時間就 1 小時），期間查表自動跳過它。
- 手動：使用者說「X 這週省著用」之類的話，換算成到期時間後執行：

  ```bash
  node "${CLAUDE_SKILL_DIR}/scripts/route.mjs" block <cli> <到期時間，ISO 格式> <理由>
  ```

  回報標記到什麼時候。要提前解除，就請使用者說一聲，再用同一指令把到期時間設成現在。
- 狀態檔位置：`$XDG_STATE_HOME/agent-dispatch/state.json`；Windows 是 `%LOCALAPPDATA%\agent-dispatch\state.json`；其他是 `~/.local/state/agent-dispatch/state.json`。

## 8. 交棒（context 快滿，交給新 session）

做法見 `references/handoff-protocol.md`：交接內容有上限，對方確認收到才算交出，沒確認之前所有權留在你這裡。

## 參考

- 各 CLI 的無互動參數、模型與思考等級參數、已知坑：`../agent-mesh-check/references/cli-notes.md`
- 要先確認對方叫得動：用 agent-mesh-check skill；它的最近一次結果也是查表的可用性依據。
