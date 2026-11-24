---
name: agent-dispatch
description: 把工作交給另一個 agent CLI（claude、codex、agy、pi）：查表挑 CLI＋模型＋思考等級，額度用盡自動改派；短問答唯讀一次問完，長任務開 pane 或背景 worktree。Use when「丟給 codex 問」「要第二意見」「交給 agy／pi 做」，或輸入 /agent-dispatch。
argument-hint: "[對象] <任務>"
---

# 跨 CLI 派工

你可以是 claude、codex、agy、pi 其中任何一個入口（主控）。四家對等，共用 `references/routing.json` 這份路由規則。

腳本都在本 SKILL.md 旁的 `scripts/`；在非 Claude 入口，`${CLAUDE_SKILL_DIR}` 換成本 SKILL.md 所在的目錄。context 壓縮後也照用 skill 開頭的 Base directory，不要 ls 或 glob 外掛快取找腳本：快取留著幾十個舊版，挑錯版本會缺子命令。

## 1. 選對象

- 使用者指定對象就照做（`--to`）。
- `claude-api` 是同一支 claude、以 API key 計費；設了 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD`（印 key 的指令，如 `security find-generic-password -s <服務名> -w`）才啟用。key 要用沒綁卡、沒開自動儲值的 org；規劃類訂閱優先，其餘 API 優先。要用 claude.ai connector 指定 `--to claude`；pane 一律走訂閱。
- 沒指定時，判斷任務類型，交給腳本查表（`--type`），**直接派，不先徵詢**：

  | 等級 | 類型 |
  |---|---|
  | top | `plan`、`architecture`、`review-critical` |
  | standard | `implement`、`research`、`qa`、`debug` |
  | cheap | `docs`、`format`、`mechanical` |

- 查表會濾掉 agent-mesh-check 最近一次沒通過的 CLI，以及額度封鎖中的 CLI。派出去一律帶明確的模型與思考等級，不繼承你自己的模型。
- 依風險升一級：改動碰到 `crossReview` 的路徑樣式或超過 `maxLines` 行，可以用高一級；偏離查表結果（升或降）時，回報那行加「升級理由：…」。
- 只查不派（例如工作要交給同家 subagent，只需要知道該用哪一家、哪個模型）：`node "${CLAUDE_SKILL_DIR}/scripts/route.mjs" pick <類型>` 印出有序候選 JSON（全被濾掉時是 `[]`）；挑審查者用 `reviewer <作者 CLI>`，套下面的跨家族規則。回報那行由呼叫端自己組。
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
   node "${CLAUDE_SKILL_DIR}/scripts/ask.mjs" (--to <cli> | --type <類型>) [--model <m>] [--effort <e>] [--timeout 600] [--idle-timeout 480] [--cwd <目錄>] <prompt 檔>
   ```

3. 判讀：
   - 第一行是「交給誰、用哪級、理由」，之後是對方的輸出。
   - 輸出超過 16000 字元時，全文寫進 `<prompt 檔>.out.md`，畫面只有前 4000 字元和檔案位置。需要細節再讀檔，不要整份讀進 context。
   - 對象是 codex 時，畫面只印最終答案，另存 `<prompt 檔>.answer.md`；`.out.md` 是整段執行紀錄（prompt 回顯、hook 行，可達數百 KB），只在查過程時用 grep 讀。要重讀結論讀 `.answer.md`。
   - exit code：124 逾時（含連續 `--idle-timeout` 秒無輸出判定卡住，預設 480，0 關閉；推理很久的任務可調大）、127 沒安裝、2 用法錯誤、75 所有候選都不能用（stderr 有最早解封時間）。
   - 額度用盡時腳本會自己封鎖那一家並改派下一家，stderr 會印「改派 X」，回報時一併說明。
4. 轉述時寫明是哪個 CLI 說的，不要把它的結論包裝成你自己的；它說錯的地方要指出來。

短問答一律唯讀，因為無互動模式下沒人能按確認。`ask.mjs` 會在 prompt 前加唯讀指示；claude 與 pi 只開讀檔、搜尋類工具（能自己看 `--cwd` 底下的檔案），codex 是 read-only 沙箱；agy 沒有參數層的唯讀（見 cli-notes），只靠這行指示。需要改檔的工作改用長任務，不要為了方便放寬權限。

## 4. 審查

- 下列情況要**跨家族審查**（同家換型號不算獨立）：改動碰到安全、資料、DB 結構、公開介面（路徑樣式在 `routing.json` 的 `crossReview`），或變更超過 300 行。
- 其他小改只做同家審查。
- 挑審查者：用 `route.mjs` 的 `reviewer()` 規則——top 等級候選裡第一個跟作者不同家族的。家族：claude、claude-api 與 pi 是 anthropic、codex 是 openai、agy 是 google。
- 每次派審查前都先跑 `node "${CLAUDE_SKILL_DIR}/scripts/route.mjs" reviewer <作者 CLI>`，不沿用上一次的審查者。回傳的 `crossFamily` 是 `false` 就直接走同家審查，不要先送別家再等失敗。
- 湊不到別家（都沒裝、沒登入或封鎖中）就退回同家審查，回報寫「湊不到別家，退回同家審查」，不問使用者。同家審查用新的 context：同家 CLI 的短問答，或 Agent subagent。
- 只有 `reviewer` 正常回傳 JSON 且 `crossFamily` 是 `false` 才算湊不到別家。腳本報錯、印出用法或輸出不是 JSON 是**工具故障**：用 Base directory 的腳本重試一次；仍失敗才同家審查，回報寫「工具故障，退回同家審查」並附錯誤訊息，不能寫成湊不到別家。
- 審查用短問答（`--to <查到的審查者> --model … --effort high`），把 diff 寫進 prompt 檔。prompt 從 `references/review-prompt.md` 的範本開始寫。
- 審查 prompt 要給明確範圍（要讀的檔）與時限。逾時（124）不要原樣重送：先縮範圍或降一級 effort 再試一次，卡住（無輸出逾時）同樣適用；仍逾時就退回同家審查，回報寫「codex 逾時，退回同家審查」（codex 以外照實寫 CLI 名）。
- 封鎖到期後同一家又因沒額度失敗：用 `route.mjs block <cli> <到期時間>` 手動延長封鎖，並在回報裡寫明。

## 5. 長任務：依環境選一層

依序偵測，取第一個可用的：

1. **herdr 或 Herdr.app**（`mux.py env` 的 `backend` 不是 `none`）：看得見的 pane，步驟見下方第 6 節。
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
- 授權範圍：寫明可以改哪個 repo、哪些路徑，其他 repo 一律不動；prompt 沒寫明可以 push、發版的，就不 push、不發版。
- 並行多個 worker 時，各自的結果檔與工作區分開，並寫明「另一個 worker 正在寫 X，不要碰」。並行上限預設 4（背景 worker 以同一個 `--ws` 上層目錄計），遇到額度錯誤或逾時就降。
- **不輪詢**。Claude worker 用 SendMessage 回報；其他 CLI 用阻塞等待（`mux.py send --wait`）或完工通知。背景 worker 在 macOS 等通知、用 `bg.mjs status` 看一次；其他平台用 `bg.mjs wait` 阻塞等結束。
- **完成的唯一證據是結果檔存在**。

## 6. herdr／Herdr.app 步驟

動作與回傳欄位見 `references/herdr-long-task.md`。以下 `mux.py` 指 `python3 "${CLAUDE_SKILL_DIR}/scripts/mux.py"`；stdout 是 JSON（`read` 例外，輸出純文字），失敗時是 `{"error":kind,"hint":…}`，exit code 2 用法、3 `core_not_running`、4 `no_backend`、1 其他。

0. 前置：
   - `mux.py env` 回 `{"backend":"hc|herdr|none","self":…,"window":bool}`。`none` 就不走這節；`hc` 是 Herdr.app、`herdr` 是 TUI，後面的步驟兩者相同。
   - `core_not_running`：core 沒跑，請使用者從 Dock 開 Herdr.app；不要自己 stop／restart core，也不要直接跑 `hc` 去試（hc 會用你的環境把 core 自動啟動）。
   - `window:false`（hc）：視窗沒開，worker 照跑但 `spawn` 回 `visible:false`；告訴使用者開 app 視窗後把該 worker 叫出來。`window_error` 照 hint 回報。
   - `window_on:<機器>`（hc）：本機沒開 app，但使用者從另一台的 Herdr.app 遠端看這台 core（如 Mac 看 Windows）；`spawn` 會經 `hc exec --on` 擺進那邊的主 tab，照常使用。
   - mux.py 不加 `2>/dev/null`，錯誤與 hint 都要看。
   - 在 herdr 或 Herdr.app 的終端裡跑拋棄式 `claude -p` 時，先濾掉 `HERDR_*`、`HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`HC_SCOPE`，否則會蓋掉真正主 session 的回報（`ask.mjs` 已自動濾）。
   - TUI 專屬：**不要在 Claude Code 內啟 herdr server**，`CLAUDE_CODE_CHILD_SESSION` 會被繼承，pane 內 transcript 不落檔（macOS 用 `brew services start herdr`）。
   - 對象是 claude 時，cwd 必須已受信任（本身或任一上層通過信任對話框），否則 worker 卡在對話框沒人能答。檢查腳本見 reference；不通過就請使用者先在該目錄開一次 Claude Code。
1. 在專案的暫存區開一個工作目錄，把 prompt 寫成檔案（內容照第 5 節共用規則）。**你是 Claude Code、對象是 claude 時**，先用 `ListAgents` 取得自己的位址寫進 prompt，要它寫完結果檔**之後**用 `SendMessage` 回報一句話加結果檔路徑；要用 AskUserQuestion 問人之前，也先發一則「在問：{一句話}」。送不到就用 ListAgents 找同一個 ref 的目前名稱重送一次，仍失敗才在工作區寫 `undelivered` 檔。
2. 開 worker 並起對方的 CLI（版面由 `spawn` 處理）。回傳的 `id` 就是之後所有動作的 `<id>`，不要自己推算：

   ```bash
   mux.py spawn --name <唯一名稱> --kind <claude|codex|agy|pi> --cwd "<cwd>" --env AGENT_DISPATCH_RESULT="<結果檔>" --env AGENT_DISPATCH_INTERACTIVE=1 -- <模型參數>
   ```

   - hc 的終端名稱（`--name`）只能 1-32 字、`a-z 0-9 - _`。
   - `<模型參數>` 一定要帶（查表或使用者指定的模型與等級），寫法見 `../agent-mesh-check/references/cli-notes.md`：claude `--model <m> --effort <e>`、codex `-m <m> -c model_reasoning_effort=<e>`、agy `--model <id>`、pi `--model <provider>/<id>:<thinking>`。
   - `spawn` 負責開 pane、放進主 session 旁（主 session 最大、同 tab 最多 6 個 worker；主 tab 已有 6 個時第 7 個起 `spawn` 自己開新 tab，TUI 不再切主 session、不跑版面腳本）、起 CLI、命名；不手動切 pane、不 `pane resize`、不跑 `herdr_layout.py`。回 `visible:false` 見上面前置。
   - 兩個 `--env` 讓 Stop hook 在 worker 沒寫結果檔就停時攔一次，提醒它寫檔回報；還沒做完就直接再停一次。沒有寫檔工具的 worker 不要帶。
   - 主控在無人值守時再加 `--env AGENT_DISPATCH_UNATTENDED=1`：worker 要用 AskUserQuestion 時會被擋下，改照「（推薦）」做，並把題目與選擇寫進結果檔的「主控裁決待確認」。
   - 指定 agent 定義（claude／codex）：`--` 後面再加 `--agent <plugin>:<agent>`，套用其工具白名單與 model。
   - 任何情況都不用 `hc run` 或 `pane run` 起 CLI（guard 會擋），一律走 `spawn`。
   - 替別的專案開不回報的長駐獨立 session：`mux.py` 沒有開新 tab 的動作；TUI 做法見 reference「TUI 專屬」，Herdr.app 內請使用者自己開。
   - `spawn` 失敗：herdr 後端會先留畫面再關掉 pane（`spawn_failed`，hint 帶畫面摘要），連同 hint 回報，多半是 cwd 問題；`cli_not_found` 是呼叫者 PATH 找不到該 CLI。
   - Herdr.app 內各 CLI 啟動時可能先跳對話框（信任資料夾、外部檔案 import、hook 審核），此時 `status` 是 null（不是 `blocked`），`send` 的 Enter 會選到預設項。所以剛起的 worker（turn 0）`mux.py send` 會先等就緒（至多 60 秒）再自動加 `--if idle`：status 仍不是 idle 就不送，回 `{"status":"blocked","hint":…}`，不重試。收到時先 `mux.py read <id> --lines 30` 看畫面；有對話框就不替使用者按信任，告訴使用者用 `mux.py attach-hint <id>` 的 hint 進去處理，處理完再送；畫面已是就緒輸入框、沒有對話框時，隔幾秒再送同一則。
3. 送出 prompt，放在背景等待：

   ```bash
   mux.py send <id> --file <prompt 檔> --wait --timeout 540
   ```

   - `--file` 由 mux.py 直接讀檔，不經 shell，反引號與 `$()` 不會被展開；要送短句用 `--text`。
   - `--timeout` 單位是秒，要搭 `--wait` 才有效（不搭不會等）。回傳 `{"status":S,"raw":…}`，`S` 是 `done|idle|working|blocked|error|timeout|gone`。
   - 送出後先 `mux.py read <id> --lines 30` 確認畫面開始工作，再去等。claude worker 的 `SendMessage` 是主訊號，背景等待只是備援。
4. 判讀結果。狀態只是參考：

   | `status` | 處置 |
   |---|---|
   | `done`／`idle`，結果檔在 | 讀它，進第 5 步 |
   | `done`／`idle`，結果檔不在 | 先不關 worker，`mux.py read <id>` 看最後一段：在提問 → 照 `blocked`；還沒開始動（codex 常見）→ 隔幾秒查一次結果檔；只用文字收尾忘了寫檔 → 送一句「把結果寫進 <結果檔>」 |
   | `blocked`，或畫面停在提問 | 不替它回答、不重送 prompt；告訴使用者「worker『{名稱}』在問：{一句話}，`mux.py attach-hint <id>` 給的指令進去回答」。等人答完用 reference 的輪詢 |
   | `timeout` | 不代表失敗：查結果檔，再 `mux.py alive <id>`；仍在跑就重掛等待，不重送 |
   | `gone` | worker 已結束：查結果檔，沒有就回報並重派一次 |
   | `error` | 看 `raw`：TUI 含 `protocol_mismatch` 時不重派，worker 多半還活著，請使用者在 worker 都 idle 時重啟 server（reference「TUI 專屬：安裝與升級」）；其他照 `raw` 回報 |

   claude worker 回到 idle、結果還沒到、context 已超過 250K：由你發動中途交接，步驟見 reference 與第 8 節。正在 working 或 blocked 時不插話。
5. 收工：讀完結果檔就 `mux.py close <id>`，不留著待命（留著的 worker 會自己找事做）。例外：無人值守或自動駕駛的實作者要等審查與修正（續派原實作者），保留到該段修正完成才關，並在帳本記 worker id／session。只關自己在第 2 步開的 worker，不用「清單上沒別人」推論安全，也不要關整個 workspace／space（會連使用者與你一起關）。TUI 專屬：關完再跑一次 `python3 "${CLAUDE_SKILL_DIR}/scripts/herdr_layout.py" --main "$HERDR_PANE_ID"` 重排（Herdr.app 的格子 close 後自動消失，不需重排）。最後把結果檔列出的暫存路徑確認都在本次工作區內，一次清掉。

## 7. 額度

- 自動：`ask.mjs` 與背景 worker 遇到額度錯誤會封鎖那一家到重置時間（抓不到時間就 1 小時；「沒額度、要儲值」類的訊息封鎖 24 小時），期間查表自動跳過它。
- 手動：使用者說「X 這週省著用」之類的話，換算成到期時間後執行：

  ```bash
  node "${CLAUDE_SKILL_DIR}/scripts/route.mjs" block <cli> <到期時間，ISO 格式> <理由>
  ```

  回報標記到什麼時候。要提前解除，就請使用者說一聲，再用同一指令把到期時間設成現在。
- 狀態檔位置：`$XDG_STATE_HOME/agent-dispatch/state.json`；Windows 是 `%LOCALAPPDATA%\agent-dispatch\state.json`；其他是 `~/.local/state/agent-dispatch/state.json`。

## 8. 主將換模與交棒

- **只有一段卡住**：主將照第 1 節把該段派給更合適的模型，繼續負責整案和驗收。
- **整案需要重拆，或目前 session 無法繼續**：同 CLI 若支援，由操作者在安全點切換目前 session 的模型。需要換 session 或 CLI 時，依 `references/handoff-protocol.md` 交棒。派工的模型參數只影響新 worker。
- **長任務**：每個階段完成時更新交接紀錄。原 CLI 因額度封鎖且已無法回應時，由操作者依同一份協議用最近的紀錄交棒。CLI 封鎖期間，同一家換模型不會解除派工封鎖。

## 參考

- 審查 prompt 範本（第一輪整份審查、第三輪起定點核對）：`references/review-prompt.md`
- 各 CLI 的無互動參數、模型與思考等級參數、已知坑：`../agent-mesh-check/references/cli-notes.md`
- 要先確認對方叫得動：用 agent-mesh-check skill；它的最近一次結果也是查表的可用性依據。
