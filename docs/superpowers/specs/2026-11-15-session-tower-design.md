# Session 塔台：多 session 協調設計

日期：2026-11-15　狀態：設計待核准　規劃圖：使用者私人 artifact（Session 塔台規劃）

## 意圖

同一個專案常同時開好幾個 session（同機多 worktree、自動駕駛的平行線、日後跨機器跨人），彼此不知道對方在做什麼，造成：

- **重工**：兩個 session 做了同一件或很像的事。
- **合併衝突**：改到同一批檔，或在 main 上互相蓋掉。

比喻是機場塔台：起飛前申報、飛行中追蹤、落地時核對「人數」（實際改動是否與申報相符）、下機後釋放跑道。

**起因**：使用者實際遇過多 session 重工與衝突，未留文字紀錄（使用者 2026-11-15 裁決整套一次做完，不先做量測版）。已有紀錄的相關事件只有產品化 session 三條線重測試撞期（已由 `test-lock.sh` 解決）。

## 目標

1. 每個 session 開工時登記一班「航班」，其他 session 看得到。
2. 起飛時發現重疊就提醒；進入 main 前發現不符或撞車就硬擋。
3. 跟現有的 roadmap／feature.md／todo.md／票、自動駕駛／無人值守接起來，不另起一套。
4. 登記格式第一版就能直接搬去跨機器共用。

## 非目標

- 第一版不做跨機器同步（只預留格式與欄位），也不做 git hook 硬擋。
- 不做 symbol 級（函式、類別）預約；只到檔案路徑／glob。
- 不做語意相似度比對；沒有工作項目時，重工由 agent 讀其他航班目標自己判讀。
- 不改無人值守／自動駕駛的模式劃分（使用者 2026-11-15 裁決維持現狀）。
- 不替失聯航班自動清理。

## 反目標（做出來但算失敗）

- 開工常被擋、使用者只好一直放行。
- agent 隨便寫一行理由就把真的撞車帶過去。
- 自動駕駛因為等使用者確認而停擺。
- feature.md、CHANGELOG 這類人人都改的檔天天觸發提醒，提醒變噪音。
- 自動駕駛換新 session 後，自己的舊航班變失聯、新航班又跟它撞。

## 限制

- 放在 toolkit plugin（使用者裁決）。toolkit 已有 hook 框架與 `guards/*.md` 分層 guard。
- 每個 plugin 必須能單獨安裝：workspace 的 unattended 呼叫塔台是可選的，沒裝 toolkit 時維持現在的共用檔判準。
- 跨 CLI：hook 只有 Claude Code 完整支援（`docs/agent-parity.md`）；Codex 部分、agy 只有 Stop、pi 沒有 hook。核心邏輯必須是一支可直接執行的腳本，hook 只是 Claude Code 上的自動觸發。
- 常駐 context 不變胖：新增 hook 的 SessionStart 輸出要短；skill description 要精簡。
- 公開 repo：登記檔不進版控，不得寫入個人絕對路徑以外的外洩內容（登記檔本身在 `.git/` 下，不會被提交）。

## 做法比較

| 做法 | 取捨 | 結果 |
|---|---|---|
| A. 本機登記表＋hook＋guard（toolkit），格式預留跨機 | 輕、立刻有感；跨機器要第二階段 | **採用** |
| B. 一開始就用 GitHub draft PR／共享 git ref 當塔台 | 涵蓋最完整；要先處理同步延遲、權限，單機也變慢 | 不採用，留給第二階段 |
| C. 只做落地核對（合併前比 diff） | 最輕；擋不住重工 | 不採用 |
| 外部：Contrail、MCP Agent Mail、Claude Code Agent Teams | Contrail 綁 Cloudflare、symbol 級；Agent Mail 要架 server、原 repo 可能停維護；Agent Teams 只限同一 lead | 借概念（起飛前預測、TTL、落地再驗），不引入 |

## 已拍板（使用者 2026-11-15）

1. 第一版只做單機，格式預留跨機器。
2. 起飛時只提醒、落地時硬擋。
3. 飛行計畫＝開工時申報意圖（一行目標＋預估路徑）＋hook 自動追蹤實際改動。
4. 落地＝進入 main：在 main 上 commit、merge／rebase 進 main、push 到 main。分支上的中途 commit 不擋。
5. 航班有對應的 roadmap 段號、feature.md 功能名或票號就連上；沒有也能飛。
6. 硬擋放行：只是超出申報範圍 → 補一行理由（記進航班）就放行；改到另一班活航班持有的檔 → 要使用者確認，無人值守時改排隊、等對方落地後 rebase 再試。
7. 放 toolkit；unattended 有裝就接上。
8. 提醒與硬擋整套一次做完。
9. 自動駕駛與無人值守維持現狀，塔台兩者一視同仁。

## 設計

### 1. 登記表（塔台）

- 位置：`$(git rev-parse --git-common-dir)/tower/flights/<flight-id>.json`。git 共用目錄讓同一 repo 的所有 worktree 看到同一份；在 `.git/` 下，不進版控。
- 一班一檔，寫入用「寫暫存檔再 rename」確保原子性；不需要全域鎖。
- 欄位：

```json
{
  "id": "20261115-1432-a1b2",
  "schema": 1,
  "goal": "herdr 開 pane 規則與 guard",
  "work": {"segment": "a7", "feature": "功能名", "ticket": "#123"},
  "paths": ["plugins/toolkit/guards/**"],
  "touched": ["plugins/toolkit/guards/herdr-tab-create.md"],
  "branch": "feat/x", "worktree": "../plugharbor-x",
  "session": "<CLI session id>", "cli": "claude", "host": "<主機名雜湊>",
  "started": "...", "beat": "...",
  "overrides": [{"at": "...", "kind": "scope", "reason": "..."}],
  "state": "flying"
}
```

- `host` 存主機名的短雜湊，不存原名（公開 repo、跨機器時不洩漏）。
- `state`：`flying`、`landed`（已進 main，等下機）、`lost`（心跳逾時，僅標記）。下機＝刪檔，歷史事件另記 `tower/log.jsonl`（一行一事件，給回來報告與日後統計用）。

### 2. 共用跑道

人人收工都會改的檔，重疊不提醒、不擋，但落地前一定 rebase 最新 main、數字類由腳本重算：

- toolkit 預設只放通用檔：`docs/feature.md`、`docs/roadmap.md`、`docs/todo.md`（及根目錄大寫版）、`**/CHANGELOG.md`。
- 專案在 `.plugharbor/tower.yml` 的 `shared:` 追加；plugharbor 自己加 `.claude-plugin/marketplace.json`、根 `README.md`、`plugins/*/.claude-plugin/plugin.json`。
- **我的決定**：`land-check` 驗「HEAD 已包含本機預設分支最新 commit」（有遠端時先比 `origin/<預設分支>`），不包含就退出碼 12（要先 rebase），硬擋但放行方式就是 rebase 後重試，不問人。版號、總計等數字的重算不由塔台做，仍由各專案既有腳本（如 plugharbor 的 `release-plugin`、`feature_checklist.py`）負責。

### 3. 核心腳本 `plugins/toolkit/scripts/tower.py`

所有 CLI 都透過它操作；hook 只是在 Claude Code 上自動呼叫它。子命令：

| 子命令 | 作用 |
|---|---|
| `takeoff --goal --paths [--segment --feature --ticket]` | 登記，回傳航班 ID 與重疊報告 |
| `amend <id> --paths/--goal` | 範圍變了就更新 |
| `beat <id> [--touched <檔>…]` | 心跳＋記錄實際改動 |
| `radar [--json]` | 列出所有航班與重疊 |
| `land-check <id>` | 落地核對，退出碼：0 放行、10 超出申報、11 撞活航班、12 落後預設分支 |
| `override <id> --kind scope --reason` | 超出申報補理由 |
| `landed <id>`／`release <id>` | 標記已落地／下機刪檔 |

重疊判斷：

- **同工作項目**：另一班活航班的 `work` 任一欄相同 → 重工（最強提醒）。
- **路徑重疊（起飛、飛行中提醒）**：申報 `paths`／實際 `touched` 與其他活航班的交集，扣掉共用跑道。
- **撞活航班（落地硬擋，退出碼 11）**：只算雙方**實際改過的檔**（本班 `git diff` 與對方 worktree 的 `git diff`）有交集，扣掉共用跑道；申報範圍不參與硬擋（使用者 2026-11-15 裁決）。
- 失聯：心跳超過逾時就當 `lost`。**我的決定**：心跳由任何工具呼叫與使用者送訊息續命（見第 4 節），只有 session 真的關掉或卡死才會失聯；`lost` 不參與起飛提醒與落地硬擋，但落地時若改到 `lost` 航班碰過的檔，印一行提醒並寫進 log（避免死航班永遠擋人，又不完全沉默）。

### 4. Claude Code 的 hook 與 guard（toolkit）

| 時機 | 掛法 | 行為 |
|---|---|---|
| SessionStart | `tower-context.py` | 有航班時印一行摘要（幾班在飛、與本 worktree 相關的重疊）；沒有就不輸出 |
| 開工 | skill 指示 agent 呼叫 `takeoff` | 回報重疊只提醒，讓使用者決定等、協作或照飛 |
| PostToolUse Edit／Write | `tower-track.py` | 記 `touched`、撞到別班的檔時即時提醒；只是即時提醒用，落地核對不依賴它 |
| PreToolUse（任何工具）、UserPromptSubmit | `tower-track.py` | 續心跳（只更新時間戳，不開 git 子程序） |
| PreToolUse Bash | `tower-landing.py`（獨立 hook，不走 `guards/*.md`） | 判斷指令是否進 main（含「目前分支是 main 時的 `git commit`」），是就跑 `land-check`，依退出碼放行、`ask` 或 `deny` |
| 本 session 沒有航班 | — | hook 只追蹤、不擋（不強迫每個 session 都申報） |

**我的決定（技術類）**：

- 落地硬擋另寫 hook：現有 `guard.py` 只做字串 regex、結果固定，無法執行腳本、也看不出目前分支，做不到「在 main 上 commit 才擋」。
- 落地核對一律以 `git diff <main>...HEAD`（含工作區未提交）為準；Bash 改的檔（sed、腳本產生、`git mv`）也算得到。hook 的 `touched` 只供即時提醒。
- 航班對應：以 **worktree 路徑＋分支** 找航班，不以 session id。主控派多個 subagent 時 session id 都一樣、派 pane worker 時起飛當下也不知道 worker 的 session id；worktree 才是一個工作單元的真實邊界。同一 worktree 一次只有一班活航班；換新 session 自然沿用，帳本只需記航班 ID 備查。
- 無人值守訊號：unattended 起飛時寫 `"mode": "unattended"` 進航班；hook 也認既有環境變數 `AGENT_DISPATCH_UNATTENDED=1`。有這個訊號時，退出碼 11 回 `deny` 並附「排隊等航班 X 落地」說明，不回 `ask`。
- 效能：PostToolUse 與心跳 hook 先量一次實際延遲（`run-py.sh` 會啟動兩次 interpreter），超過 100ms 再優化（例如心跳改純 shell `touch`）。

### 5. 跟現有文件與票

- 起飛時讀 `docs/feature.md`：申報的功能已是 🚧 但沒有活航班 → 提示「可能別台機器或舊 session 在做」。
- 落地核對多一項（只提醒、不擋）：連了功能名的航班，該項是否已改成 `[x]`。**我的決定**：toolkit 拿不到其他 plugin 的路徑，且 lifecycle 正在拆分，所以 `tower.py` 自帶最小解析（找含功能名的那一行、看開頭是否 `- [x]`），不引用 lifecycle／tickets 的腳本。票階段不由腳本查；skill 寫明「有裝 tickets 時用 `ticket-ops` 更新票」，沒裝就略過。
- todo.md 不加認領欄；認領靠航班的 `goal` 表達。

### 6. 跟無人值守／自動駕駛（workspace，可選）

- 排線：塔台存在時，被其他活航班持有段號或路徑（扣共用跑道）的段不列入可開工。
- 每個工作單元登記一班；worker 由 hook 自動回報。
- 起飛撞到別人時：同工作項目有活航班 → 跳過該段做下一段；只是路徑重疊 → 當共用檔照順序。都記成主控裁決。
- 合併（第 6 步）＝落地：退出碼 10 補理由放行；11 排隊，帳本記 `空檔：等航班 <id> 落地`，先做別的。
- 換新 session：航班 ID 寫進帳本，接回時沿用，不重新起飛。
- 回來報告多一節「塔台紀錄」：提醒、排隊、補理由放行，各一筆。
- 沒裝 toolkit：照現在的共用檔判準，不變。

### 7. 其他 CLI

- Codex、agy、pi：沒有完整 hook，靠 skill 指示手動呼叫 `takeoff`、`land-check`、`release`；`touched` 改由 `land-check` 時直接從 `git diff` 推算。
- 回報時標明「此 CLI 沒有自動追蹤、沒有硬擋」。
- 第一版硬擋只在 Claude Code（使用者 2026-11-15 裁決）；git pre-commit／pre-push hook（讓所有 CLI 與手動指令都擋得住，含與既有 `core.hooksPath` 共存）留到第二階段，與跨機器一起做。

### 8. 規則與文件同步

- AGENTS.md「並行」段：人工 `git worktree list` 的做法改成「有裝 toolkit 時看 `tower.py radar`，沒有時照舊」。
- 新增 skill（暫名 `toolkit:tower`）：說明何時 takeoff／land／release、怎麼讀 radar；SKILL.md 300 行內，邏輯在腳本。
- feature.md 新增一節，CHANGELOG 起因照本文件「起因」段。

## 留給實作者的事

- 心跳逾時（提案：30 分鐘；自動駕駛長閘門期間由閘門腳本定期 beat）。
- 進 main 的 git 指令比對樣式（在 main 上 commit、`merge`、`rebase`、`push` 到預設分支）的正規式與測試案例。
- `paths` 的 glob 語法（提案：與 `.gitignore` 相同的 `**` 語意，用 Python `pathlib`／`fnmatch` 實作）。
- 航班 ID 格式、`log.jsonl` 欄位。
- PostToolUse hook 的效能（每次 Edit 都跑，要在 100ms 內）。

## 驗收方式

- `tower.py` 單元測試：重疊判斷（同工作項目、路徑、共用跑道排除、失聯排除）、退出碼、原子寫入。
- hook 測試照 toolkit 既有 pytest 慣例。
- 端到端：用 `claude --plugin-dir plugins/toolkit` 開兩個 worktree session，重現「同段重工提醒」「改到對方的檔被擋」「超出申報補理由放行」三個情境。
- `python3 scripts/ci/validate.py` 通過；版號同步照 AGENTS.md。
