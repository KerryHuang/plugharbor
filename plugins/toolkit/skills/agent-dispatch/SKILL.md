---
name: agent-dispatch
description: 把工作交給另一個 agent CLI（claude、codex、agy、pi）：短問答以唯讀模式一次問完拿回答案，長任務在 herdr 開看得見的 pane 讓對方做完、交回結果檔；沒指定對象時自己挑。Use when 使用者說「丟給 codex 問」「問問 claude／agy 的看法」「要第二意見」「交給 agy／pi 做」，或輸入 /agent-dispatch。專案若提供派工 skill（如 `<plugin>:dispatch-worker`），claude／codex 長任務改用它。
argument-hint: "[對象] <任務>"
---

# 跨 CLI 派工

你可以是 claude、codex、agy、pi 其中任何一個入口。本 skill 負責把工作交給另外一個 CLI 去做。

## 1. 選對象

- 使用者有指定對象就照做。
- 沒指定時，先讀 `references/preferences.md`，依任務性質自己挑一個，**直接派，不先徵詢**。回報時寫一句「交給了誰、為什麼」，讓使用者事後知道花了哪一家的額度。
- 只想要另一家模型的觀點，而且你本身是 pi，pi 也已登入那家 provider 時，用 pi 自己的子代理（pi-herdr-agents）換模型就好，比較輕。需要用到 codex 或 agy 這個工具本身（它的沙箱、外掛、repo 設定）時，才用本 skill。

## 2. 選模式

| 任務 | 模式 |
|---|---|
| 問意見、第二看法、小型唯讀調查，幾秒到幾分鐘 | 短問答 |
| 要改檔、預估十幾分鐘以上、中途可能要問人 | 長任務 |

## 3. 短問答（一律唯讀）

1. 把 prompt 寫成暫存檔。prompt 要能獨立讀懂，自帶背景、要回答什麼、回答的格式。
2. 執行下面這條指令。腳本和本 SKILL.md 放在同一個目錄的 `scripts/` 下；在非 Claude 入口，`${CLAUDE_SKILL_DIR}` 換成本 SKILL.md 所在的目錄。

   ```bash
   node "${CLAUDE_SKILL_DIR}/scripts/ask.mjs" --to <claude|codex|agy|pi> [--timeout 600] [--cwd <目錄>] <prompt 檔>
   ```

3. 對方的輸出會原樣印出。exit code 的意思：124 是逾時，127 是沒安裝，2 是用法錯誤。
4. 轉述時寫明是哪個 CLI 說的，不要把它的結論包裝成你自己的；它說錯的地方要指出來。

短問答一律唯讀，因為無互動模式下沒人能按確認。`ask.mjs` 會在 prompt 前加唯讀指示；agy 沒有參數層的唯讀（見 cli-notes），交給 agy 的短問答只靠這行指示。需要改檔的工作改用長任務，不要為了方便放寬權限。

## 4. 長任務（herdr pane）

**先看有沒有專案派工 skill**：Skill 清單有 `<plugin>:dispatch-worker` 這類專案提供的派工 skill、且對象是 claude／codex 時，本節不執行，改用它。本節只在沒有專案派工 skill，或對象是 agy／pi 時使用。

先檢查 `HERDR_ENV` 是不是 `1`。**不是 1** 就告訴使用者「不在 herdr 裡，沒辦法開一個看得見的 pane」，改由你自己在目前的 session 做。不要偷偷用背景的無互動程序跑長任務。

在 herdr 裡的步驟（指令細節見 `references/herdr-long-task.md`）：

> **未實測（2026-10-29 改版）**：收工回報時加一段實測結果——claude worker 有沒有寫完結果檔才 `SendMessage`、`--timeout` 搭 `--wait` 有沒有正常送出、有沒有用到中途交接。哪項不如預期就修本節；全部驗過就刪掉這段引言。

0. 前置：
   - `herdr agent list` 數活著的 worker；已有 3 個以上，用 AskUserQuestion 問使用者要照派、排隊，還是改派 subagent。
   - 對象是 claude 時，cwd 必須是 Claude Code 開過、通過信任對話框的目錄，否則 worker 卡在對話框沒人能答。檢查腳本見 reference；不通過就請使用者先在該目錄開一次 Claude Code。
1. 在專案的暫存區開一個工作目錄，把 prompt 寫成檔案。prompt 必須寫明：
   - 結果檔的絕對路徑，以及「寫完結果檔才算完成，寫完就停」。
   - 「不要刪暫存資料夾，把要清的路徑列在結果檔」。
   - 已經定案的決定和已排除的方向，避免對方重問或重走。
   - **你是 Claude Code、對象是 claude 時，要它主動回報**：先用 `ListAgents` 取得自己的位址（`This session is <名稱> [ref]`）寫進 prompt，要求它寫完結果檔**之後**用 `SendMessage` 回報一句話加結果檔路徑；要用 AskUserQuestion 問人之前，也先發一則「在問：{一句話}」。先寫檔再發訊息，你被喚醒時才讀得到檔。codex／agy／pi 不能發訊息給 Claude session，靠第 3 步等待。
   - 並行多個 worker 時，各自的結果檔與工作區分開，並寫明「另一個 worker 正在寫 X，不要碰」。
2. 開 tab 並起對方的 CLI。`pane_id` 從回傳的 JSON 讀，不要自己推算：

   ```bash
   herdr tab create --cwd "<cwd>" --label <短名>
   herdr agent start <唯一名稱> --kind <claude|codex|agy|pi> --pane <pane_id>
   ```

   `agent start` 失敗：先 `herdr pane read <pane_id>` 留畫面，再關掉這個 pane，連同畫面摘要回報；`agent_not_ready` 多半是 cwd 問題。
3. 送出 prompt，放在背景等待：

   ```bash
   herdr agent prompt <名稱> "$(cat <prompt 檔>)" --wait --timeout 540000
   ```

   - 一定要用 `$(cat 檔)` 送出，不要用 heredoc 或裸雙引號，因為反引號和 `$()` 會在你這邊的 shell 先被執行。
   - `--timeout` 一定要搭 `--wait`：單獨給 `--timeout` 整條會被拒，prompt 根本沒送出，而且錯誤只在 stderr——herdr 指令不要加 `2>/dev/null`。
   - 送出後先 `herdr pane read <pane_id>` 確認畫面開始工作，再去等。claude worker 的 `SendMessage` 是主訊號，背景等待只是備援。
4. 判讀結果。**完成的唯一證據是結果檔存在**，狀態燈只是參考：

   | 回傳 | 處置 |
   |---|---|
   | `done`／`idle`，結果檔在 | 讀它，進第 5 步 |
   | `done`／`idle`，結果檔不在 | 先不關 pane，`herdr pane read` 看最後一段：在提問 → 照 `blocked`；還沒開始動（codex 常見）→ 隔幾秒查一次結果檔；只用文字收尾忘了寫檔 → 送一句「把結果寫進 <結果檔>」 |
   | `blocked`，或畫面停在提問 | 不替它回答、不重送 prompt；告訴使用者「worker『{名稱}』在問：{一句話}，`herdr agent attach <pane_id>` 進去回答」。等人答完用 reference 的輪詢 |
   | 逾時 | 不代表失敗：查結果檔，再 `herdr agent list`；仍在跑就重掛等待，不重送 |
   | `protocol_mismatch` | herdr 升級後 CLI 與跑中的 server 協定不合，worker 多半還活著：不重派，請使用者在 worker 都 idle 時重啟 herdr server |

   claude worker 回到 idle、結果還沒到、context 已超過 250K：由你發動中途交接（寫交接檔 → `/clear` → 接續），步驟與 prompt 見 reference。正在 working 或 blocked 時不插話。
5. 收工：讀完結果檔，`herdr pane close <pane_id>`。只關自己在第 2 步開的 pane，不用「清單上沒別人」推論安全，也不要 `herdr workspace close`（會連使用者與你一起關）。最後把結果檔列出的暫存路徑確認都在本次工作區內，一次清掉。

## 參考

- 各 CLI 的無互動參數與已知坑：`../agent-mesh-check/references/cli-notes.md`
- 要先確認對方叫得動：用 agent-mesh-check skill
