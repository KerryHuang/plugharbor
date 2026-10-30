---
name: dispatch-worker
description: "用 herdr 開 pane 跑另一個完整 CLI session（claude／codex）並派工：長任務外包、多 worker 並行匯流、跨 CLI。疊在官方 `herdr --skill` 之上，補 Claude Code 專屬坑與檔案交接。觸發：「派給另一個 session」「丟給 codex 做」「開 N 個 worker 並行」「這個長任務丟出去跑」。"
argument-hint: "[任務說明] [--kind claude|codex] [--n <worker 數>]"
---

# Dispatch Worker — herdr 派工

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

通用操作以官方 `herdr --skill` 為準；本檔只補 Claude Code 的坑與「結果一律從檔案拿」。
用在：預估 15 分鐘以上、可能中途問人、要完整 session 或換 CLI。範圍明確、不需問人 → Agent subagent；小又需要目前 context → 自己做。
並行匯流 = 多開幾個 worker，全部結果檔到齊才整合。指令全文與 cwd 檢查見 [references/commands.md](references/commands.md)。

## Step 0：前置

- `test "${HERDR_ENV:-}" = 1` 不成立 → 不呼叫任何 herdr 控制指令（會抓到別人的 pane）；短任務改派 subagent，長任務留在本 session 做並告知使用者。
- 成立 → 第一次用先讀 `herdr --skill`；衝突時以本檔為準。
- 🔴 開 pane 前先 `herdr agent list` 數活著的 worker：**已有 3 個以上 → 先停下問使用者**（AskUserQuestion：照派／排隊等一個收工／改派 subagent），題目附活著的 worker 清單。每個 claude worker 開場約 74K tokens、每一輪都重讀，並行數直接乘上用量（曾有一天高峰同時二十多個 session，一天吃掉過半週用量）。使用者在本 session 對同一批派工答過「照派」就不再重問。
- cwd 必須是 Claude Code 開過的目錄，否則 worker 卡在信任對話框、沒人能回答（檢查見 commands.md）。
- herdr 指令不加 `2>/dev/null`（錯誤全在 stderr）。不要從 Claude Code 內啟 herdr server：`CLAUDE_CODE_CHILD_SESSION` 會被繼承，pane 內 transcript 不落檔（macOS 用 `brew services start herdr`）。

## Step 1：prompt 與結果檔

- prompt 一律寫成檔，Step 4 用 `"$(cat <絕對路徑>)"` 送出；不用 heredoc、不裸雙引號（反引號與 `$()` 會在呼叫端被執行，不報錯）。
- prompt 必寫結果檔絕對路徑，並寫明「結果寫進該檔才算完成，寫完就停」。`agent wait` 只回狀態、`agent read` 讀的是折行的渲染畫面。
  例外：以 `--agent` 起、沒有寫檔工具的 worker（如 sdlc 顧問）改由主 session 從 transcript 取回應。
- **claude worker 要主動回報**（不然只能靠主 session 輪詢，等人一久輪詢斷掉，就變成使用者回頭通知主 session）：先用 `ListAgents` 取得主 session 的位址（第一行 `This session is <名稱> [ref]`），寫進 prompt，並寫明兩件事——**寫完結果檔之後**，用 `SendMessage`（to 寫成 `<名稱> [ref]`）回報一句話加上結果檔路徑；**要用 AskUserQuestion 問人之前**，也先發一則「在問：{一句話}」。先寫檔再發訊息，否則主 session 被喚醒時會讀不到檔。閒置中的主 session 收到訊息會自己醒來（實測）。codex worker 不能發訊息給 Claude session，維持 Step 4 的輪詢。
- 並行時每個 worker 各自的輸出檔與工作區，並明講「另一個 worker 正在寫 X，不要碰」。
- 暫存放專案規定處（沒有規定就用 `.tmp/<YYYYMMDD>-<slug>/`）。
- prompt 必寫「不要刪暫存資料夾，在結果檔列出要清的路徑」：worker 的 `rm -rf` 會撞使用者的 ask 規則而停在確認畫面（曾一天卡三次）。

## Step 2：開 pane

```bash
herdr pane split --current --direction right --cwd "<cwd>" --no-focus
python3 ${CLAUDE_PLUGIN_ROOT}/skills/dispatch-worker/scripts/herdr_layout.py --main "$HERDR_PANE_ID" --label <票號或任務短名>
```

- 取回傳的 `result.pane.pane_id`，不要推算編號。開完一律跑 `herdr_layout.py` 重排（主 session 最大並掛「★」標籤）；不手動 `--direction down`、不 `pane resize`。`--label` 第一次給即可。
- 同 tab 已有 6 個 worker → 第 7 個起 `herdr tab create --cwd "<cwd>" --label <名稱>`，取 `result.root_pane.pane_id`，該 tab 不重排。
- 不用 `workspace create`（使用者看不到）。

## Step 3：起 worker

```bash
herdr agent start <唯一名稱> --kind <claude|codex> --pane <pane_id>
```

- 名稱唯一好認（`w1-schema-scan`），起好後 `herdr pane rename <pane_id> <名稱>`。
- `agent start` 失敗（非 0）→ 先 `herdr agent read <名稱>`（讀不到用 `pane read`）留畫面，再 `herdr pane close <pane_id>`，連同畫面摘要回報；`agent_not_ready` 多半是 cwd 問題。
- 指定 agent 定義：`-- --agent <plugin>:<agent>`，套用其工具白名單與 model。

## Step 4：派工並等待

```bash
herdr agent prompt <名稱> "$(cat <prompt 檔絕對路徑>)" --wait --timeout 540000
```

- 不加 `--until`（`--wait` 預設停在 idle／done／blocked）。`--timeout` 須小於 Bash 上限 600000 ms，而且**一定要搭 `--wait`**：只寫 `--timeout` 會整條被拒、prompt 根本沒送出（曾因輸出被導進 /dev/null 沒人發現，worker 空轉到使用者來問）。預估超過幾分鐘一律 `run_in_background: true`。送出後先 `herdr agent read` 確認畫面開始工作，再去等。
- **主訊號是 worker 的 `SendMessage`**（Step 1）；背景等待只是備援。背景等待只會返回一次：只有狀態仍是 `working` 才重掛 `herdr agent wait <名稱> --timeout 540000`（對 idle／done 的 worker 會立刻返回，空轉）。要等人回答的長時間等待改用 `Monitor` 跑輪詢（commands.md），上限 30 分鐘、到期重掛；不要自己停掉不掛。
- 並行：多個 `agent prompt` 在同一則訊息送出（各自背景）。

## Step 5：判讀

完成的唯一硬證據是結果檔存在；狀態燈只是提示（`idle` 可能是答完等人、沒收到 prompt、做完結束）。收到 worker 的「完成」訊息 → 照 `done` 處理；收到「在問」訊息 → 照 `blocked` 提醒使用者。

| 回傳 | 處置 |
|---|---|
| `done`／`idle` | 結果檔在 → 讀它、進 Step 6。不在 → `herdr agent read` 看最後一段，**先不關 pane**：在提問 → 照 `blocked`；畫面底部有「N shell」＝工作丟背景後結束這一輪，關 pane 會一起砍掉 → 再查結果檔，仍不在就 `herdr agent wait <名稱> --until working` 等被喚醒、再 `agent wait` 等結束；只用文字收尾、忘了寫檔 → 送一句「把結果寫進 <結果檔>」或回報使用者 |
| `blocked`／`agent_blocked` | `agent read` 看問什麼，提醒使用者一行：「worker『{名稱}』在問：{一句話}。要回答：`herdr agent attach <pane_id>`」。**不代答、不重送 prompt**。attach 後不要再介入（畫面混著人的輸入）；等人答完用輪詢（見 commands.md），不用 `--until working`（worker 的 subagent 回報會誤喚醒） |
| `timeout`＋exit 1 | 不是失敗。查結果檔，再 `herdr agent list`：仍 `working` → 重掛；否則依該狀態處理。不重送、不關 pane |
| `agent_prompt_stalled` | `agent read` 看畫面，多半 prompt 沒進輸入框 |
| `protocol_mismatch` | herdr 升級後 CLI 與跑中的 server 協定不合，worker 多半還活著。**不重派**；請使用者在 worker idle 時重啟 server（見 commands.md「升級 herdr」） |

並行匯流：有人卡住就先處理其他人的結果，不空等。懷疑狀態判錯 → `herdr agent explain <名稱>`。

### 中途交接（worker context 過大）

worker 每一輪都整份重送 context。曾有一天八成 worker 超過 200K，這段佔當日用量約四分之一。worker 沒人盯，所以由派工端發動：

- **時機**：worker 回到 `idle`／`done`、結果檔還沒到齊，且 `ctx.py`（用法見 commands.md）量到 **> 250K**。`working` 中不插話；`blocked` 不動，以免打斷它問人。
- **三步，各自 `--wait`**：①請它依交接格式寫 `<工作區>/_handoff-<名稱>.md`，寫完就停；②檔案存在才送 `/clear`；③送「讀 <交接檔>，從『下一步』接著做」，並重貼原 prompt 裡的結果檔路徑與回報方式。三段 prompt 文字見 commands.md「中途交接」。
- `/clear` 後 session id 會換新，名稱不變（實測）。要再量 context，先從 `herdr agent list` 重抓 `agent_session.value`。
- 交接檔由派工端收工時清（同 Step 6 暫存）；worker 不刪。

## Step 6：收工

```bash
herdr pane close <pane_id>      # 逐個，只關自己在 Step 2 開的
herdr agent list                # 確認無殘留
python3 ${CLAUDE_PLUGIN_ROOT}/skills/dispatch-worker/scripts/herdr_layout.py --main "$HERDR_PANE_ID"
```

- 結果檔驗過就關，不等全部做完。關之前 `agent read` 確認沒人在跟它對話；`pane close` 不可逆。
- 只關自己開的 pane，不用「清單上沒別人」推論安全（`herdr agent list`、`claude agents`、`ps` 各有漏）。不 `herdr workspace close`（會連使用者與主 session 一起關）。
- 暫存由主 session 統一清：收齊各結果檔列出的路徑，確認都在本次工作區內，一條指令刪除（一次核准）；有疑義就留著回報。
- 在 herdr pane 裡跑的拋棄式 `claude -p` 要濾掉 `HERDR_*`，否則會蓋掉真正主 session 的回報。
