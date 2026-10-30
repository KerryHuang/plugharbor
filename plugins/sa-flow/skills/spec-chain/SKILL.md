---
name: spec-chain
description: "跨 session 協調多棒 SA 規格鏈：每棒決定就地做、派 subagent 或開 herdr worker，並獨立驗收產出。需要 herdr。觸發：「跑規格鏈」「spec-chain」。"
argument-hint: "[票號或功能描述]"
---

# PM — SA 規格鏈的協調者

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

PM **不實作**：不寫 FRD／SAD／BFS／FFS、不改程式碼、不碰程式碼 submodule／大型 repo 檔案（進去會載入大量 repo 規則，需要時派 subagent 取摘要）、不代 worker 答使用者、不跨機派工。只做：判規模與路由 → 派工 → 盯狀態 → 驗收。交棒點（硬性停點 vs 可自動接棒）以 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 為準。
herdr 通用操作一律依 `sa-flow:dispatch-worker`；機制細節（`_pm-run.json`、prompt 模板、驗收指令）見 [references/worker-protocol.md](references/worker-protocol.md)。
`$ARGUMENTS` = `[票號或功能描述]`，未給時從對話推斷並確認。

## Task 0：前置

任務清單：判現況、定路由、派工、盯狀態、驗收、回報。

- `test "${HERDR_ENV:-}" = 1` 不成立 → 停下告訴使用者，改照 handoff-protocol.md 單 session 接棒（不套 dispatch-worker「留在本 session 做」的退路，PM 不實作）。
- 成立再 `herdr status`：exit 127 → 停下請使用者依 `${CLAUDE_PLUGIN_ROOT}/skills/dispatch-worker/references/commands.md` 安裝，或改單 session 跑，不自己繞；`server_not_running` → 依同檔「安裝與起 server」起 server（不要在 Claude Code 內起）。
- 🔴 接著跑 `scripts/pm_resume.py` 對帳 `{功能目錄}/analysis/_pm-run.json`，不憑記憶重建進度（PM 會被壓縮、中斷）。檔案不存在 = 第一輪。指令見 worker-protocol.md「執行狀態與續跑」。

## Task 1：判現況（PM 自己做）

先把 `$ARGUMENTS` 解析成 `{功能目錄}`：票號 → 查票務系統取功能名，到 `{docs-root}` 找 `{模組}/{功能}`（或 `grep -rl "{票號}" {docs-root}`）；功能描述 → 以關鍵詞搜目錄。定不出唯一目錄 → 停下問，不猜。

只讀三處，不整檔載入規格：`ls` 功能目錄（鏈跑到哪）、規格檔檔頭 SPEC-INDEX、`decisions.md`（指令見 worker-protocol.md）。沒有 `decisions.md` 是舊功能常態，由該棒 worker 依 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md` 建檔。

## Task 2：定路由

兩個軸：需不需要人即時裁決 × 要不要進 submodule。

| 需人裁決 | 進 submodule | 派給 |
|---|---|---|
| 否 | 否 | PM 自己，限小動作（讀 `decisions.md`、路由、檢查腳本） |
| 否 | 是 | subagent（便宜的隔離；PM 嚴守不碰 submodule，這格主要由 worker 內部使用，派工 prompt 明寫） |
| 是 | 否／是 | session（subagent 觸及不到人，只有此項值得升級成 session） |

鏈上各棒：`linear-triage` PM 自己；`explore`、`requirement`、`system-analysis`、`specify-backend`、`specify-frontend`、`dev-readiness`、`verifying-specs`、`linear-create` 全派 session。`dev-readiness`、`verifying-specs`、`linear-create` 不准 PM 就地跑（實測 context 暴漲到 926k）；`linear-create` 由 worker 讓使用者確認票樹，PM 只收票號。`verifying-specs` 棒的 claude worker 以 `herdr agent start ... -- --model sonnet` 起（照清單驗證、最機械，不必用最貴的模型）；其餘棒繼承預設模型。

**不可並行**：`specify-backend → specify-frontend`（FFS 硬相依 BFS）；`dev-readiness` 獨佔；同一功能目錄的任意兩棒（共用 `analysis/_context.yml`、`db-analysis.yml` 會互蓋）。不同票可並行。驗收發現上游要修而下游已在跑時：後派的限定窄任務、prompt 點名「不要碰這兩個共用檔」；做不到就等下游跑完。

路由結果以文字列給使用者（哪一棒、派給誰、為什麼），該回合不接工具呼叫，逐棒列到下一個硬性停點、一次確認。使用者經另一個 session 轉達「由你跑完這條鏈」時，路由與接棒的確認門算過；push、開票、改 DB、關別人的 pane 與規格內容裁決仍回使用者本人。

## Task 3：派工

- **派 session**：依 dispatch-worker Step 0～4。cwd 一律專案根（不要拿 submodule 目錄）。prompt 模板見 worker-protocol.md，必含：貼上 `decisions.md`「決策／選定」兩欄並標「已拍板、不要重問」（無 `decisions.md` 則寫明本棒建檔從 D-001 起）、讀哪幾份文件哪幾章（走 `sa-flow:spec-docs`）、「本棒跑完就停，不接下一棒」（可接棒時 PM 驗收後另開新 worker，每棒從乾淨 context 起跑）、回報走落檔 ＋ `SendMessage`（驗收只看檔案）。
- 🔴 派工後立刻寫 `_pm-run.json` 一列 `dispatched` 並更新 `watch`，不只記在 context。只寫此檔，不寫 `_context.yml`。
- **派 subagent**（`Agent`）：prompt 必含回報格式（只回摘要與結論，不貼原始碼全文）與邊界（只讀不改，發現該改處回報位置理由）。

## Task 4：盯狀態

依 dispatch-worker Step 5。產出檔存在 → Task 5；不存在 → 照 Step 5「done／idle」那列判讀，不關 pane。停點提醒一行附棒名與 `pane_id`，提醒後不再介入、不代答（需人裁決才升級成 session）。量 worker context 用 `scripts/ctx.py`（用法見 worker-protocol.md）；PM 自己的數字是移動標的，報數字標明量測時點。

## Task 5：驗收（必要職責）

先過閘：產出檔存在嗎？`idle` 不代表完成，沒產出就不是驗收失敗，是還沒到時候。依序逐項複驗，不照單全收，共五項（指令見 worker-protocol.md「驗收」）：

1. 產出檔存在且非空殼：體積 ≥ 範本、編號章數 ≥ 範本、無殘留範本佔位符，三條缺一不可，不自訂判準。
2. `decisions.md` 有本棒新列、「否決的選項與原因」非空，且產出檔 `§D` 列了同一批編號。
3. SPEC-INDEX 與章節一一對應：照 `${CLAUDE_PLUGIN_ROOT}/skills/spec-docs/references/spec-index-format.md`「Full index」規則 6 的指令跑，看 `diff` 空不空。
4. 跑機械閘 `python3 ${CLAUDE_PLUGIN_ROOT}/skills/verifying-specs/scripts/check-decision-propagation.py {功能目錄}`：exit 非 0 照輸出先回派修，通過才進第 5 項。它擋 R1～R4 決策傳播、R5 暫定標記（`狀態`＝暫定的 D，正文要寫「（暫定，D-xxx 待確認）」）、R6 文件資訊版本＝CHANGELOG 最高版本，這三類靠讀正文抓不完（實測驗收後窄修回派 86 則，暫定漏標 31、版本不同步 29）。
5. worker 宣稱依循的上游決策確實存在：派 subagent 比對，只收「宣稱｜D 編號｜有無」表。

驗收完把 `_pm-run.json` 該棒改 `verified` 或 `rejected`。`verified` 就依 dispatch-worker Step 6 關該 pane 並重排；可自動接棒且續行條件全滿足 → 回 Task 3 派下一棒新 worker，否則停下回報。
有問題 → 回派同一個 worker 修（`herdr agent prompt`），派窄任務（明說改哪幾處），不重跑整支 skill、不自己改；回派後不等回報，直接重驗檔案。
🔴 最後一步是重新掛上等待並更新 `watch`（背景等待返回即結束，曾漏掉 27 分鐘無人看守）；要不要掛只看 `herdr agent list` 該 worker 的 pane 還在不在。

## Task 6：回報與收工

三段：跑了哪幾棒、產出什麼、下一棒建議。逐個 `herdr pane close` 收掉未關的 worker，`herdr agent list` 確認無殘留。🔴 只關 `_pm-run.json` 記得的 pane，殘留列給使用者決定。各棒列出的暫存路徑在整條鏈收工時由 PM 一次清掉。

**票務收工**：規格鏈驗收通過、QA／Dev 票開好的同一輪，把規格票改完成狀態，不等後續附帶 MR 合併（待合併事項寫在規格票留言追蹤）；父需求票依子票狀態調整（已開 Dev 票 → 進行中，沒開 → 維持需求整理中）。收工時查一次票況複核。
> 單一票的特例裁決（如「等某個 MR 合併再關」）不要套到整批。

**docs 收工**：關完 pane 後 `git -C <docs repo> status --short`。有本鏈產出但未 commit 的檔 → 環境有 `commit` skill 就交給它（逐檔 add，不用 `git add -A`），沒有就逐檔 add 後 commit；接著問使用者要不要 push、要不要 bump 上層 repo 的 submodule pointer，兩者都對外，不自動做。
還有 `狀態`＝暫定的 D 時，先派一次 `sa-flow:domain-advisor`（`mode: triage`，subagent，不必開 session）分流，再問使用者；不分流就問，會把顧問查得出答案的 domain 題全丟給 PO（曾一次丟 19 題）。PM 先把需要的 DB 實查結果放進 `evidence_bundle`，顧問讀舊系統原始碼與證據，逐題判「撤題」「顧問裁定」或「交 PO」：舊系統移植以舊系統為最終驗收基準，顧問只能往對齊舊系統裁定；偏離舊系統（通用預設以外）、與 SA 意見相左、證據不足、命名或範圍取捨一律交 PO。顧問裁定的題照 worker-protocol.md「使用者裁決回寫」樣板回派（`狀態`＝定案、`拍板`＝`顧問`、依據補證據），問之前先列成一張清單讓使用者可點名推翻；交 PO 的題才一次一題問（`shared-preludes-details.md`「規格鏈中途裁決」第 3～4 點）。

## 暫停／恢復／狀態

使用者說「先停」「下班了」「回來繼續」「現在到哪」時用，不另寫腳本：

- **暫停**：對 `_pm-run.json` 記載的每個還活著的 worker pane 送（`herdr agent prompt <pane>`）：「暫停：把目前進度寫進 {功能目錄}/analysis/_handoff-{棒名}.md，未完成的步驟列在最後，然後停下等 PM 通知，不要再改檔。」送完把 `paused_at` 與已通知的 pane 清單寫回 `_pm-run.json`；不關 pane、不刪暫存。
- **恢復**：先跑 `pm_resume.py`（Task 0）對帳，再對 `_pm-run.json` 已通知清單裡仍活著的 pane 送：「恢復：重讀你的交棒檔，從列在最後的未完成步驟接著做。」pane 已不見的那一棒依 `pm_resume.py` 的建議重派。恢復後清掉 `paused_at`，重新掛上等待（Task 5 最後一步）。
- **狀態**：直接跑 `pm_resume.py`，照輸出回報，不另外組裝。
