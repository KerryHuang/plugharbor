# 功能清單

總計：完成 20／共 29（另有 1 項決定不做）；進行中 1、已規劃 2、構想 6；待確認 0 項。更新於 2026-11-16。

## workspace：unattended（自動駕駛） #8

完成 5／共 7。

- [x] 空檔判準：長工作丟背景時依序挑計畫文件、無共用檔的另一個 worktree、同批檔案照順序，帳本記「空檔：」；實作只跑相關測試，完整套件只在閘門跑一次（workspace 1.11.0；只做過 `claude -p` 情境測試，未在真實自動駕駛驗證） #9
- [x] 自動排線：lifecycle `--open` 的可開工分「主線」（第一個未完成段）與「可平行」（往後幾段內有 spec、沒被 ⛔ 擋的段），並抓出列序與 ⛔ 矛盾；roadmap 列序只是偏好、硬依賴寫 ⛔；autopilot 每段收尾與丟長工作時重排「主線＋最多 1 條平行線」（平行線過共用檔判準），把排線表寫進累積報告並推播後直接開工（起因：產品化 session 使用者問了 13 次「還有什麼可以先做」，工具只給第一段；使用者 2026-11-14 裁決三題；lifecycle 2.5.0、workspace 1.13.0） #10
- [x] 功能清單改名 `docs/feature.md`：lifecycle 腳本預設讀新名、找不到退回舊名；plugharbor、Formwright、xiaoxiao 一起改名（使用者 2026-11-14 要求；lifecycle 2.7.0） #11
- [x] 三條線與測試鎖：排線改成主線＋最多 2 條平行線，共用檔（含同檔不同段落）照順序；重測試一律經 `test-lock.sh` 排隊；已各自審查的段可共用一次閘門（起因：產品化 session (c) 回報同時跑 3 條線、重測試撞期多跑一倍；使用者 2026-11-14 裁決兩題；workspace 1.16.0） #12
- [x] 合批：相鄰、同一份 spec、改同批檔案的段合成一批，一個 worktree、每段各自 commit，閘門、審查、合併只走一次；roadmap 同一列多個段號＝使用者指定一起做，autopilot 也可自己合並寫進排線表；上限 3 段或約 800 行先到先停；一段卡住就 revert 該段 commit、其餘重跑閘門後合併，卡住的段放回排程並寫待決（起因：產品化 session 每段固定花 50 分鐘～2 小時跑閘門；a2d4、a2d5 已同 commit 上線；使用者 2026-11-14 裁決三題；lifecycle 2.6.0、workspace 1.14.0） #13
- [ ] 💡 已合併的主控裁決事後被使用者推翻時的重做方式（當插入單元馬上做，或寫回 roadmap 排隊）；等事故再補 #14
- [ ] 💡 暫停後逐題問完待決，是否自動恢復自動駕駛（目前只認「繼續自動駕駛」）；等事故再補 #15

## toolkit：agent-dispatch #16

完成 7／共 7。

- [x] 腳本一律用 skill 的 Base directory：agent-dispatch 寫明不要 ls／glob 外掛快取（起因：2026-11-12～14 產品化 session 壓縮後自己 glob 到快取舊版 0.9.3，沒用 Claude Code 自動附上的 skill 路徑） #17
- [x] 每個 session 自己換新：壓縮後 hook 提示「任務未完、停在沒有背景工作的點才換，完成就不換」；在 herdr 內使用者在場先問一次，同意或無人值守就照 handoff 寫交接檔後自己 `/clear`、`/reload-plugins`、接回；不在 herdr 內建議打 `/handoff`（使用者 2026-11-14 裁決；toolkit 0.23.0） #18
- [x] 版本落後提醒：壓縮後 compact-context hook 比對本 session 載入的 toolkit 版本與已安裝版本，落後就提醒告一段落時換新 session（起因：產品化 session 開 9 天一直跑 toolkit 0.13.0，漏了 8 版修正；使用者 2026-11-14 裁決，取代原「壓縮後重新叫用 skill」——Claude Code 壓縮後已自動附上用過的 skill） #19
- [x] 自動駕駛每段收尾自動換新 session：在 herdr 內背景啟動 `self-rotate.sh`，等自己閒置後 `/clear`、`/reload-plugins`、送「繼續自動駕駛」照帳本接回；有 subagent／背景工作／平行線在跑就這次不換（使用者 2026-11-14 裁決自己換、每段都換；workspace 1.15.0） #20
- [x] 工具故障不靜默降級：`route.mjs reviewer` 回 `crossFamily: false` 才算湊不到別家；腳本報錯或輸出不是 JSON 算工具故障，用正確路徑重試一次，仍失敗就繼續跑、報告標紅並推播（使用者 2026-11-14 裁決；toolkit 0.22.0、workspace 1.12.0） #21
- [x] 無人值守 worker 不卡在提問：無人值守派出的 worker 帶「沒人在場」標記（環境變數，傳不進 herdr pane 就改標記檔），ask-question-guard 擋下 AskUserQuestion，叫它照「（推薦）」做並把題目與選擇寫進結果檔的「主控裁決待確認」；不可逆操作照舊停下（起因：2026-11-08 worker 卡在選擇題，主控臨時寫自動按 Enter 腳本；使用者 2026-11-14 裁決） #22
- [x] ask.mjs 封鎖到期時間改印本地時間並標時區（起因：UTC 無標記，主控誤判封鎖已過） #23

## toolkit：Session 塔台（2026-11-15 規劃） #24

完成 1／共 2。

同一專案多個 session 互相看不到，造成重工與合併衝突；起飛申報、飛行追蹤、進 main 前核對、下機釋放。設計見 `docs/superpowers/specs/2026-11-15-session-tower-design.md`。

- [x] 單機塔台（段 T1）：`tower.py` 登記表、起飛提醒、改動追蹤、進 main 前硬擋（只 Claude Code）、feature.md 核對、unattended 可選接入（使用者 2026-11-15 裁決 11 項） #25
- [ ] 💡 第二階段（段 T2）：跨機器跨人（票的 in-progress／git ref 同步）與 git pre-commit／pre-push 硬擋 #26

## lifecycle：ticket skill 雙軌示範（2026-11-14 規劃） #27

完成 4／共 6。

ticket skill 的 GitHub 後端從沒實測過；拿專案雙軌並行驗證：repo 的 roadmap／feature／todo 為準，GitHub Issues＋Projects 跟著同步，對不上就是 skill 的 bug。段→父票、feature 項目→子票（清單行附 `#n`）、todo→`todo` label 票；外部回饋先開 issue 走 triage。設計見 `docs/superpowers/specs/2026-11-14-ticket-dual-track-design.md`。

- [x] ticket-ops 送出前外洩檢查（lifecycle 2.8.0，標題一併檢查 2.12.1）：建票、留言、改描述前用 `.leak-denylist` 掃內文，命中就停（兩個示範 repo 都公開） #28
- [x] ticket-ops 同步 GitHub Projects：建票自動加進看板，改階段同時改「狀態」欄位（使用者 2026-11-14 裁決；lifecycle 2.12.0，私有看板 #1 實測） #29
- [x] lifecycle 改清單同步票（lifecycle 2.9.0；對帳腳本 reconcile.py 2.10.0）：任何流程改 feature.md／todo.md（新增、改標記、換節、刪除）都同步建票或改階段，行尾附 `#n` #30
- [x] 查 GitHub 原生 sub-issue 與 blocked-by 能否取代內文慣例：都能用，已改為原生、內文慣例降為退路（lifecycle 2.11.0） #31
- [ ] 🚧 第一階段（段 D1）：plugharbor、xiaoxiao 現有項目全部補開（完成的關閉）、跑兩週；過關條件：7 個操作加看板同步各實跑且讀回一致、各階段數量最後連續 5 天差異 0、外洩掃描 0、第二份週報對得上、發現的 bug 都處理（使用者 2026-11-14 裁決） #32
- [ ] 📋 第二階段（段 D2）：條件達成後擴到 Formwright，補驗 qa-verify `--sweep` 與大量票的報表 ⛔ 等：D1 #33

## lifecycle：簡化與拆分（2026-11-15 規劃） #34

完成 2／共 3。

單人專案實際順手的流程靠 superpowers＋workspace＋toolkit，lifecycle 只用到清單腳本；改成 superpowers 當工程核心、lifecycle 只管做之前與做之後，拿掉四份文件規格鏈，拆出 tickets／discovery／delivery。團隊有裝、沒裝 superpowers 產物同格式。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`。

- [x] 第一批「先刪」（段 L1）：拿掉規格鏈與連帶 skill（spec-chain、explore、consolidate-docs、write-doc、dev-feedback）、agent、範本與 `scale`；install-project 不再停用 superpowers；qa-verify 改讀規格 §2.3 驗收案例；ticket-create 拿掉角色子票；勘察檔每個功能一份（使用者 2026-11-15 裁決；lifecycle 3.0.0，未 push） #35
- [x] 第二批「再拆」（段 L2）：tickets、discovery、delivery 三個新 plugin，只搬不改行為；共用 agent 副本改名＋同步測試；有票務設定的專案安裝時自動補裝 tickets（lifecycle major） #7
- [ ] 🚧 第三批「最後接」（段 L3）：專案層 AGENTS.md 標準段落（`--shared` 寫入、含計畫審查與精簡驗收格式）、implement 薄入口＋同格式退路、spec-check 縮成實作前檢查、after.md 只留驗收對照與回填、user 層 superpowers.md 改寫 #36

## 借鏡 agentrun（Parcha-ai/agentrun，2026-11-13 評估） #37

完成 0／共 3。

- [ ] 💡 auto-memory 寫入前程式檢查：秘密樣式、隱藏字元、與既有記憶本文完全重複、索引行數上限、從網頁／貼上內容學來的規則不收；等事故再做 #38
- [ ] 💡 常改的 skill（unattended、agent-dispatch）附 eval 案例，改動後跑一次量效果（可接 `claude plugin eval`；範本參考 dotnet/skills 的 `tests/<plugin>/<skill>/eval.yaml`＋評分腳本、有無 skill 對照、觸發率）；等事故再做 #39
- [ ] 💡 agent-dispatch `bg.mjs wait` 為「待決」回專用 exit code（agentrun 用 8），呼叫端不必讀結果檔第一行；現行 herdr 事故已修，等事故再做 #40

## 借鏡 dotnet/skills（2026-11-13 評估）

完成 0／共 1。

- [-] .NET 工具鏈（MSBuild、測試、診斷、升級、EF 查詢最佳化）不在 plugharbor 自寫——理由：需要時在專案層裝 dotnet/skills 對應 plugin，backend／database 只管架構與慣例（使用者 2026-11-15 確認） #41

## workspace：project-setup（專案 AI 設定補裝） #42

完成 1／共 1。

- [x] 只從 Claude Code 叫用，替四個 CLI 在專案層補裝：plugharbor → 網路純 skill → 自寫 AGENTS.md＋缺口 skill；設計見 `docs/superpowers/specs/2026-11-13-project-setup-design.md`（workspace 1.10.0；agy 載入未驗證） #43

## delivery：demo-video 優化（2026-11-16 規劃）

完成 4／共 4。

第一次實戰（dynamic-fields-design 兩支影片）的摩擦集中在起站／重置、選擇器試錯、操作超時。設計見 `docs/superpowers/specs/2026-11-16-demo-video-optimization-design.md`。

- [x] 錄影環境配方 `video/env.mjs`：引擎自動 reset、自選空埠、驗 PID 才算就緒、只關自己的程序；`env-check` 指令；預設目錄改 `video/` 進版控
- [x] `dry-run`（不配音不錄影、失敗印可互動元素）與配音快取；不做 `--from segN`（理由見設計 §2）
- [x] 操作員 `a.upload`、`a.select`、`a.as`（換人）；每段 `expect`；contact sheet 改抓操作完成那一刻
- [x] 審稿附語音估計與操作秒數表；回報分開寫成片長度與製作時間；配音授權寫進 MP4 metadata、專案層 `tts.licensed` 只問一次
