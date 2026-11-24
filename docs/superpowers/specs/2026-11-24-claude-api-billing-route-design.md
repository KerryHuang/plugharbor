# claude-api：派工先扣 API 額度、用完退回訂閱

日期：2026-11-24　狀態：設計待核准

## 起因與目的

- 訂閱方案（例如 Ultra／Max）每月附一筆 Claude API 額度，月底作廢、不累積。這筆額度只付「用 API key 跑的 `claude -p`／Agent SDK」，不付互動式 Claude Code。
- 2026-11-24 使用者週用量快見底，同時手上有當月 API 額度沒動。手動跑 `claude-api` 包裝指令可行，但自動駕駛、無人值守派出去的工作仍全扣訂閱。
- 目的：非互動的派工**先扣 API 額度，用完或過期自動退回訂閱**，不需要人記得切換。

## 目標

- `toolkit:agent-dispatch` 多一個派工對象 `claude-api`：同一支 `claude` 執行檔，以 API key 計費。
- 依用途決定計費優先序：top 等級（規劃、架構、關鍵審查）訂閱優先，`claude-api` 排在 `claude` 正後方；standard 與 cheap 等級（實作、研究、QA、除錯、文件、格式、機械性工作）API 優先，`claude-api` 排在 `claude` 正前方。其他家順序不動。
- API 額度不足時沿用現有封鎖機制，封鎖 `claude-api` 並改派下一個候選（通常就是 `claude`）。
- 回報行照現有格式寫「交給 claude-api（…）」，使用者看得出扣哪筆錢。
- 使用者沒設定 key 來源時，`claude-api` 等同「沒安裝」，行為與現在完全相同。

## 非目標

- 不改 `workspace:unattended`、自動駕駛的流程文字；它們經 agent-dispatch 派工，自動受益。
- 不讓互動式 pane worker（herdr、Ghostty 分割裡的 claude）改走 API：額度不付互動用法。
- 不做用量預估、預算分配、月初節流。
- 不管雲端排程（claude.ai routine）：官方規定它扣訂閱、且要 claude.ai 登入。

## 反目標（做了也算失敗）

- key 出現在 repo、log、prompt 檔、結果檔、`ps` 可見的命令列參數，或任何會進 git 的地方。
- 沒設定 key 的使用者行為改變，或 mesh-check 多出失敗項。
- API 額度用完時派工整批失敗，而不是改派。
- repo 內出現個人化值（鑰匙圈服務名、email、路徑）：plugharbor 是公開 repo。

## 限制

- 額度只付 `-p`：`ask.mjs`（短問答）與 `bg.mjs`（背景 worker）可用；`mux.py spawn` 開的互動 pane 不可用。
- `ANTHROPIC_API_KEY` 存在時 claude.ai 的 connectors 應不載入（實測 2026-11-24：用假 key 跑 `claude -p` 時印出 connectors disabled 警告）。需要 claude.ai connector 的派工要明確 `--to claude`。
- 本機 MCP（專案 `.mcp.json`、user 設定）在 API key 下照常載入（實測 2026-11-24：`claude -p` 自述可用的 server 含專案與 user 設定裡的本機 server）。所以 claude-api 可以進背景 worker 路徑，不另加「需要 MCP」旗標。
- 實測：設了 `ANTHROPIC_API_KEY` 的 `claude -p` 一定用 key、不會退回 claude.ai 登入（假 key 回 `Invalid API key`、exit 1）。
- 額度不足時 claude 的錯誤字樣未實測；預期類似「credit balance is too low」，現有 `NEEDS_TOPUP` 正規式不含 `too low`。

## 做法比較

| 做法 | 取捨 | 結果 |
|---|---|---|
| A. 路由加新對象 `claude-api` | 重用以 CLI 為單位的封鎖與改派；回報分得出扣哪筆；要改 clis.mjs、routing.json、mesh-check 與測試 | **使用者選定** |
| B. `claude` 底下加「先用 key」開關 | 不加新對象；但 API 額度的封鎖要另記，回報分不出扣哪筆 | 不採用 |
| C. 獨立 skill＋包裝指令 | 不會自動接上自動駕駛；常駐 description 變長 | 不採用 |

使用者另定：
- 「平常就先用 API，用完再回訂閱」（不是只在訂閱用完才轉 API）。
- 依用途分：設計、思考類以訂閱優先，範圍限 top 等級（規劃、架構、關鍵審查）；研究、除錯不算，走 API 優先。

## 設計

### key 來源（使用者本機設定）

- 環境變數 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD`：一段 shell 指令，stdout 印出 API key。例：macOS 鑰匙圈 `security find-generic-password -s <服務名> -w`。（我的決定：用「取 key 的指令」而不是 key 本身，key 才不必常駐環境變數。）
- 沒設、指令失敗或印出空字串 → `claude-api` 視為不可用（同未安裝），派工照常略過。
- 取到的 key 只放進子程序的 `ANTHROPIC_API_KEY`，不寫檔、不進命令列參數、不印出。

### clis.mjs

- `CLIS` 加 `claude-api`。
- `resolveBin('claude-api')`：沒設定 key 來源時回 null；有設定就回 `claude` 的路徑。
- `buildArgs('claude-api', …)`：與 `claude` 相同。
- 新增一個取得子程序環境的步驟（建議放在 `scrubEnv` 之後由呼叫端套用，或新函式 `cliEnv(name, env)`）：`claude-api` 時執行 key 指令、設 `ANTHROPIC_API_KEY`；`claude` 時，**只有在設了 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD` 的情況下**才刪掉 `ANTHROPIC_API_KEY`／`ANTHROPIC_AUTH_TOKEN`，確保退回訂閱真的走訂閱。沒設的使用者（可能本來就靠 API key 或 gateway 跑 claude）環境原樣傳遞。（我的決定，依反目標「沒設定者行為不變」。）
- `NEEDS_TOPUP` 加入 `credit balance is too low`（或等義字樣），讓額度用完封鎖 24 小時而不是 1 小時。
- 認證失敗（`Invalid API key`、401、key 被撤銷）：**只對 claude-api** 視同額度錯誤，封鎖 24 小時並改派。其他四家維持現狀。（我的決定：key 失效時無人值守不應整批失敗。）

### routing.json

- standard、cheap 在 `claude` 正前方插入 `claude-api`；top 在 `claude` 正後方插入（訂閱優先，claude 被封鎖時才用 API）。模型與 effort 同該級 `claude` 那列。
- `family` 加 `"claude-api": "anthropic"`：跨家族審查時 claude-api 與 claude 同家。

### ask.mjs／bg.mjs

- 取得子程序環境改用上面的步驟。其餘（封鎖、改派、回報行）不動。
- bg.mjs 維持現有行為：只接受 `--to`、不在執行中改派；監督程序遇到額度或（claude-api 的）認證錯誤時寫 `state: quota` 並封鎖。主控下次查表就會跳過 claude-api、改派 claude。（我的決定：不做「worker 中途自動重啟」，改一半的 worktree 處理太複雜；無人值守的主控本來就會依結果檔重派。）

### mux.py（互動 pane）

- 路由挑到 `claude-api` 時，pane 一律以 `claude` 開（訂閱計費），並在回報寫一句「pane 為互動模式，改用訂閱」。（我的決定：不讓 pane 失敗。）
- 有設定 key 來源時，開 claude pane 一併刪掉繼承來的 `ANTHROPIC_API_KEY`／`ANTHROPIC_AUTH_TOKEN`，避免主 session 帶著 key 時 pane 互動改成按量付費。

### agent-mesh-check

- 有設定 key 來源時，把 `claude-api` 納入檢查（用 key 跑一句簡單 `-p`）；沒設定就列為「未設定」，不算失敗。

### 文件

- agent-dispatch SKILL.md：在「選對象」加兩行——`claude-api` 是什麼、怎麼設定 key 來源、需要 claude.ai connector 時用 `--to claude`。description 不變長。
- 設定說明寫明：key 要用**沒綁卡或沒開自動儲值**的 org，否則額度用完會繼續扣錢，永遠不會退回訂閱。不另做程式煞車。（我的決定：用量預估已列非目標。）
- `references/cli-notes.md`（mesh-check）補 claude-api 一節；`references/preferences.md` 視需要補一句。
- toolkit CHANGELOG 起因寫本檔「起因」；版號 minor。

## 驗收

1. 沒設 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD`：`route.mjs pick implement` 結果與改動前相同；既有測試全過。
2. 有設定：`route.mjs pick implement` 在 `claude` 前出現 `claude-api`，`pick plan` 則在 `claude` 後；`ask.mjs --type docs` 實際由 claude-api 回答，Console 用量（數小時後）出現該筆。
3. 單元測試：key 指令失敗 → 不可用；`claude` 子程序環境不含 `ANTHROPIC_API_KEY`；`claude-api` 子程序有；key 不出現在 args。
4. 單元測試：`quotaInfo` 對「credit balance is too low」類輸出回傳 24 小時封鎖。
5. 模擬額度用完（錯誤輸出 fixture）與 key 失效（假 key）：ask.mjs 封鎖 claude-api 並改派 claude，stderr 有「改派 claude」。
5a. 沒設 key 來源、但環境本來有 `ANTHROPIC_API_KEY`：`claude` 子程序照樣拿到它（不被刪）。
6. `python3 scripts/ci/validate.py` 通過（含外洩掃描）。

## 留給實作者

- `cliEnv` 的確切形狀與放哪個檔。
- key 指令的逾時（建議數秒）與快取（同一次 ask.mjs 執行內取一次即可）。
- Windows 上 key 指令的執行方式（沿用既有 run 的 shell 處理）。
- 額度不足錯誤字樣的實測：若可取得真實輸出，以實測為準調正規式。
