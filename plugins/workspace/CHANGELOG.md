# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.14.0] - 2026-11-14

- feat(unattended): `skills/unattended/references/autopilot.md` 新增「合批：一條線一次做幾段」。roadmap 同列多段號與 `--open` 的可合批（平行線同條件）在確認改同批檔案後合成一批：一個 worktree、每段各自 commit，閘門、審查、合併只走一次；上限 3 段或約 800 行；一段卡住就 revert 該段 commit、其餘重跑閘門後合併，卡住的段放回排程並推播。起因同 lifecycle 2.6.0。

## [1.13.0] - 2026-11-14

- feat(unattended): `skills/unattended/references/autopilot.md` 新增「排線：主線＋最多 1 條平行線」。每段收尾與丟長工作時重排：主線取 `--open` 的可開工，平行線從「可平行」挑第一個和主線不共用檔的段、開在另一個 worktree，重測試錯開；有列序矛盾就不繞過、寫待決並推播；排線表寫進累積報告並推播後直接開工，使用者回訊息改排線當插手。沒裝 lifecycle 時自己照同樣規則挑。起因同 lifecycle 2.5.0。

## [1.12.0] - 2026-11-14

- feat(unattended): 派審查的工具故障而退回同家時照常往下做，但在回來報告最前面標 🔴、附錯誤訊息並推播，不能寫成湊不到別家；開 herdr pane worker 時帶 `--env AGENT_DISPATCH_UNATTENDED=1`（toolkit 0.22.0 起 worker 的提問會被擋下、改照推薦做），worker 代做的決定收進「主控裁決待確認」。起因：同 toolkit 0.22.0——自動駕駛 session 的跨家族審查因工具故障悄悄降級十多段，以及 11-08 worker 卡在選擇題。

## [1.11.0] - 2026-11-14

- feat(unattended): 長工作丟背景時改成照「空檔判準」挑工作：計畫、文件、報告永遠可做；另一個 worktree 的實作要和進行中的單元沒有共用檔、且重測試錯開；改到同一批檔案的照順序。每次在帳本記一行 `空檔：…`。實作與修正只跑相關測試加 typecheck、build，完整套件只在閘門跑一次（本機或 CI 照專案設定）。資源規則改為只共用 CPU 的可並行實作、重測試不同時跑。`skills/unattended/references/project-config.md` 範本加「完整套件在哪跑」與共用檔清單。起因：2026-11-14 一個專案的自動駕駛 session，主控多半在等 20–30 分鐘的本機完整測試，實作 subagent 和 CI 各跑一次佔掉本機兩次；同晚測試並行佔滿 xUnit 工作執行緒，一個有牆鐘上限的測試讓 CI 失敗兩次。原規則只寫「先做不衝突的待辦」，沒有判準，主控照樣閒著等。

## [1.10.1] - 2026-11-13

- fix(project-setup): `detect.py`、`vendor.py`、`mirror.py` 的 stdout 改用 `errors="surrogateescape"`，ASCII locale 下含中文的路徑被解成 surrogate 時照原位元組輸出 UTF-8，不再 `UnicodeEncodeError`。起因：merge 後 Linux CI（`LC_ALL=C`、`PYTHONUTF8=0`）的中文路徑測試失敗，macOS 檔案系統編碼固定 UTF-8 所以本機沒重現。

## [1.10.0] - 2026-11-13

- feat(project-setup): 新增 `skills/project-setup`，只從 Claude Code 叫用，在新目錄或接手的 repo 一次補裝專案層設定：盤點現況（`detect.py`）→ 依需求裝 plugharbor 專案層 plugin → 網路純 skill（`vendor.py`，帶 hook／MCP／腳本或授權不寬鬆的只列「待你決定」）→ 自寫 `AGENTS.md`、`CLAUDE.md`（單行 `@AGENTS.md`）與缺口 skill → 鏡像到 `.agents/skills/` 並處理 `.git/info/exclude`（`mirror.py`）→ 交清單。只補缺、不覆寫既有檔案。腳本：`detect.py`、`vendor.py`、`mirror.py` 與各自的 `test_*.py`；references：`flow.md`、`external-search.md`、`report.md`。
- `setup/install-project.sh` 新增 `--no-claude`（略過 Claude Code，只裝 pi／Codex／agy，不可與 `--shared` 併用），供 shared 模式補裝另外三個 CLI。
- 常駐 context：新增 skill 的 description 77 字元；本版相對上一個發行版淨增 77 字元，新 skill 無替換項（先前的佔位只存在於本分支內）。
- pi 查證結論（2026-11-13 實測）：pi 讀專案根的 `.agents/skills/` 與 `.pi/skills/`，也跟隨 symlink，專案要信任（非互動加 `--approve`）才載入；因此 `mirror.py` 不另建 `.pi/skills`，`flow.md`、`report.md` 改寫實際結論，`docs/agent-parity.md` 加 pi／agy 結論與 project-setup 一列。agy 無列 skill 的方式且實測遇額度用盡，標未驗證。
- `mirror.py` 的 `exclude` 把既有的無錨定同路徑行（如 `install-project.sh` 寫的 `.pi/settings.json`）視為已存在，不再重複寫錨定版；`flow.md` 的 `--check` 說明補「shared、init 要各跑 `--shared`、`--no-claude` 一次」。
- 腳本涵蓋：既有 repo 子目錄不 `git init` 且 exclude 錨定頂層、symlink 目的地不得指到專案外、二進位與更多執行檔副檔名列待確認。
- 起因：使用者提出的需求。在新目錄或接手的 repo 開工時沒有任何專案層設定，事後要手動補裝；希望叫用一次就依需求與目錄現況裝好，並交一份可核對的清單。

## [1.9.1] - 2026-11-13

- fix(tmp-scratch): 清理段加「刪除用單獨一條 `rm -rf <絕對路徑>`，最多接唯讀指令」。起因：自動駕駛與無人值守卡在 rm 確認；toolkit 0.21.0 的 `rm-scratch-allow.py` 只核准這種寫法，近一週沒被核准的 rm 多半串了 heredoc、`git add`、`$(…)`（使用者回報）。

## [1.9.0] - 2026-11-12

- feat(debugging): 新增 `skills/debugging/references/legacy-refactor.md`，處理「要重構但沒有測試」的舊程式碼：先用特徵測試或黃金樣本鎖住現有行為（疑似 bug 照錄、另案修，故意改壞驗證測試會抓），大型改動用 Mikado 排前置順序、整模組替換走絞殺榕，小步執行時改名與移動優先用 IDE／LSP 自動重構，刪「沒有呼叫端」的程式碼前查反射、DI、序列化與公開 API，複雜度與 linter 警告數只用來找下手處、不當目標。SKILL.md 與 `tdd-cycle.md` 的 Refactor 階段各加一行指過去。description 加「重構沒測試的舊碼」，同時把「並把規格書轉成測試案例」縮成「規格轉測試」、拿掉「的除錯與 TDD」「要精簡」，長度從 105 字元減為 104；`triggers` 加兩個詞。
- 起因：沒有事故。使用者看了一份流傳的「用 AI 重構程式碼 100 招」速查圖後，比對發現既有的 Red-Green-Refactor 都假設已有測試，沒有涵蓋無測試舊碼；使用者裁決不等事故、先補上。速查圖裡丟給 AI 會出事的指令（一次修全部 linter 警告、依複雜度數字硬拆、靜態搜尋找不到呼叫端就刪），反過來寫成本檔的禁止事項。

## [1.8.0] - 2026-11-12

- feat(context-hygiene): 操作手冊新增第 6 節「把對話搬到另一個專案目錄」，細節在新檔 `skills/context-hygiene/references/move-session.md`。先分兩種需求：只想從新目錄接著談，`claude --resume <sid>` 就夠了；要出現在新目錄的 `/resume` 清單，就 `/exit` 後原樣複製 `<sid>.jsonl` 和附屬資料夾到新目錄的專案資料夾，不改檔案內容。記憶逐條判斷：只屬於新專案的搬過去，通用的兩邊各留一份。另外列出已知限制：開場設定留在歷史裡，搬家前派出的 worker 可能找不到這段對話。description 加觸發詞「對話要搬到別的專案目錄」，同時刪掉與既有詞重複的「context 變長」「感覺 Claude 變笨」，長度從 177 字元減為 163。
- 起因：某 session 開在 workspace 目錄，做的卻一直是另一個專案，使用者想把整段對話歸過去。當時的手動腳本保守地改寫了每行的 `cwd`（約 7,000 行）。實測（Claude Code 2.1.322）三點：`--resume <sid>` 在任何目錄都接得回；原樣複製的互動對話會出現在新目錄的 `/resume` 清單，`cwd` 仍指向舊目錄也沒關係；改寫對話紀錄會被 auto mode 當成竄改擋下。只發生過一次，所以先寫成既有 skill 的一節，不另開 skill。本地 e2e 第一輪：description 沒有觸發詞時，agent 讀了 skill 卻沒找到這一節，又提議改 `cwd`，因此補上觸發詞。

## [1.7.0] - 2026-11-12

- feat(unattended): 新增「自動駕駛」模式，細節在新檔 `skills/unattended/references/autopilot.md`。路線改成每段開工前重讀專案的 `docs/roadmap.md`，取第一個未完成段。使用者在不在場都照跑，只有說「暫停」「停止自動駕駛」才停，一般訊息當插手、處理完就繼續。開場必須有合併授權（`.plugharbor/unattended.md` 的「合併」一節），否則不開。遇到只有佔位的段或被 ⛔ 擋住的段，就記進待決並推播，往後找有設計、又不依賴它的段。每段做完，用同一個 commit 改 roadmap 段狀態和清單勾選。回來報告改成每段累積更新。暫停時做完手上的工作單元才停，說「繼續自動駕駛」照帳本接回。單元流程、帳本、停下條件都沿用無人值守。
- description 加「自動駕駛」「照 roadmap 跑」兩個觸發詞，刪掉「夜間模式」「依你的建議做」「不限晚上」「多個」，長度從 113 字元減為 112。
- 起因：使用者要求自動駕駛照 roadmap 走。lifecycle 2.4.0 讓 roadmap 段表成為可以機械讀取的開發順序，「下一步做什麼」不必再由人講。設計見 `docs/superpowers/specs/2026-11-12-autopilot-design.md`。

## [1.6.0] - 2026-11-11

- feat(dual-tool-mirror): 原本的「兩份平行檔：CLAUDE.md 與 AGENTS.md」改寫成「專案指示：內容只寫在 AGENTS.md」。新做法：內容只放 `AGENTS.md`，兩個工具不同的地方並列寫；`CLAUDE.md` 只留一行 `@AGENTS.md`，不放副本。另外補上切換步驟：先 grep 讀取端，看有沒有寫死去讀 `CLAUDE.md` 內文的地方；合併兩份；一起改寫寫著「兩份同步」的 rule 與 README；最後在真實專案驗收。description 同步改寫，比原本短。
- 起因：plugharbor 本身改成只用 `AGENTS.md` 時實測（Claude Code 2.1.322）發現，Claude Code 只在整條路徑上都沒有 `CLAUDE.md`、`CLAUDE.local.md` 時才自動載入 `AGENTS.md`。兩份並存時它只讀 `CLAUDE.md`，有 `CLAUDE.local.md` 時 `AGENTS.md` 會靜默不載入；`@AGENTS.md` import 則兩種情況都讀得到。改版先給線上 session 唯讀試用，回報了三件事：某 workspace 有 `CLAUDE.local.md`；某公司 plugin 約 34 個檔用 grep 讀專案 `CLAUDE.md` 的設定鍵，腳本不會展開 import；寫著「人工同步兩份」的 rule 與 README 要連帶改寫。本地 e2e 用含 local 檔與寫死讀取端的測試 repo 驗過。

## [1.5.1] - 2026-11-10

- docs: 4 個 skill 的 frontmatter 加 `triggers` 欄位（單行 JSON 陣列，不進 skill 清單、description 不變）。這個 plugin 被明確停用時，toolkit 的 `disabled-skills.py` 會拿它比對使用者訊息，提示這個 skill 存在。起因同 toolkit 0.18.0：別的專案跑 /doctor 關掉少用的 plugin 後，之後要用時找不到。

## [1.5.0] - 2026-11-09

- feat: 新增 `unattended`（無人值守模式）。使用者叫用或說要離開時，主控照路線連續推進工作單元，直到使用者回來（送出新訊息）為止：開場讀專案的 `.plugharbor/unattended.md`（範本 `skills/unattended/references/project-config.md`，沒有就趁使用者還在先問），裁決帳本分開記使用者與主控的決定，設計單元的使用者行為類決定標待確認，只在停下條件停，回來時交 `return-report.md`。跨家族審查有 `toolkit:agent-dispatch` 才用，沒有就退回同家新 context。起因是一個專案的專案層夜間 skill 實跑一次判斷點皆正確，通用流程與專案細節已分開，其他專案也需要；s2e 設計因方向在審查中翻盤多審 3 輪，促成「行為類先標待確認」。常駐 context 多一行 description，換掉該專案層 skill 的 description（隨後拆除）。

## [1.4.1] - 2026-11-09

- fix: agent-orchestration 的共用資源清單補上「同時跑會互搶 CPU 的測試」，與 user 層 `dispatch.md` 同步；`dispatch.md` 同時加上「長工作丟背景前先做或派不衝突的待辦，沒有才等、不輪詢」，並精簡其他措辭使總長不增。起因是一個專案的主控 session 把全套測試（約 10 分鐘）、部署（約 5 分鐘）、跨家族審查（20～40 分鐘）丟到背景後就停下來等，路線圖上可平行的工作沒做；兩支吃 CPU 的測試同時跑也曾讓測試逾時。

## [1.4.0] - 2026-11-09

- refactor: 方法類交給 superpowers，debugging 與 agent-orchestration 瘦身。debugging 開頭寫明裝了 superpowers 照 `systematic-debugging`／`test-driven-development`，本 skill 只留專案指令、症狀對照根因、改在正確的層、規格轉測試案例與輸出格式，一般方法敘述縮成幾行退路迴圈；`tdd-cycle.md` 的 Green／Refactor 說明精簡。agent-orchestration §6 由「專案資源優先」改成新分工（方法類 superpowers 優先，自家管 chain、output file 交棒、清理，herdr 與跨 CLI 用 `toolkit:agent-dispatch`），§0 保留。debugging、agent-orchestration、review 的 description 收掉與 superpowers 撞名的觸發詞（「systematic debugging」「TDD」「debug」「code review」「派 subagent」「orchestration」等），都比原本短。worktree、quality-check 檢查後不動。起因是近 14 天 workspace 的 debugging、agent-orchestration 叫用 0 次，方法類被 superpowers 接走，description 撞名讓兩邊搶觸發。

## [1.3.2] - 2026-11-09

- fix: commit、quality-check、tmp-scratch 的 description 加上主控自己動手時的觸發（自己要下 git commit、合併或 commit 前要跑 gate、要寫一次性腳本或開 `.tmp`），並刪掉重複的中英觸發詞，三個都比原本短。起因是一個 session 叫了 122 次 Skill，這三個一次都沒觸發：主控自己下了 76 次 commit、重複手寫 gate 指令 21 次，因為原本只寫使用者會講的話。

## [1.3.1] - 2026-11-09

- docs(agent-orchestration): 平行判準的共用資源補上「同一個 worktree」與「build／測試產物」。起因是同一個 worktree 裡跑 gate 測試與做修正的 subagent 同時在跑，互相干擾。

## [1.3.0] - 2026-11-05

- feat: `review` 新增「專案規範合規」審查面向：只比對路徑涵蓋變更檔的 `CLAUDE.md`／`AGENTS.md`，違規須引用規則原文（`skills/review/references/evidence.md` 第 7 節）。
- feat: `review` 審遠端 PR／MR 前先看留言，已有先前審查就問要不要重審；使用者要求留言但無發現時也留摘要（`skills/review/references/review-remote.md`）。
- 做法借鑒自 anthropics/claude-plugins-official 的 `plugins/code-review`（Apache-2.0），內容重新撰寫。

## [1.2.0] - 2026-11-04

- feat: `review` 新增 `skills/review/references/evidence.md`——預設只報告、變更檔歸屬表、「查無」前先證明查得到、被削弱的測試／拉長的 timeout／新 suppression 要列出、新套件查 registry；只排除改動前就存在的 suppression。
- fix: `quality-check` 的可選銜接改指 `lifecycle:implement`。

## [1.1.2] - 2026-11-04

- fix: 可選叫用與退路改指向 `lifecycle`（sa-flow／delivery-flow／dev-flow 已合併為 lifecycle）。

## [1.1.1] - 2026-11-03

- fix: `debugging` 的 tdd-cycle 角色分工補沒裝 dev-flow 時的退路，並要求把職責 plugin 的附錄路徑帶進派工 prompt。

## [1.1.0] - 2026-11-03

- feat: 新 skill `cross-platform`（跨平台路徑、換行、大小寫、shell 差異），改寫自 desktop-avalonia 的同名 skill，不再綁 Avalonia。
- feat: `debugging` 吸收 backend-dotnet 的 `tdd-cycle`（Red-Green-Refactor 通用做法放 `skills/debugging/references/tdd-cycle.md`，.NET 指令移到 backend 的附錄）。
- feat: `review` 吸收 frontend-vue 的 `review-remote`（審查遠端 PR／MR，`skills/review/references/review-remote.md`）。

## [1.0.1] - 2026-11-03

- fix: `dual-tool-mirror` 同步時略過含 `.plugharbor-root` 的目錄（plugharbor install-project 複製模式的 skill 複本），不再把它們當成多餘副本刪掉；加 node 測試。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 dev-flow 0.3.0 拆出 12 個與規格流程無關、任何專案都用得到的 skill：`commit`、`worktree`、`triage-branch-cleanup`、`submodule-relay`、`tmp-scratch`、`context-hygiene`、`agent-orchestration`、`dual-tool-mirror`、`convention-first`、`debugging`、`review`、`quality-check`。內容不變；叫用 dev-flow 的地方（`quality-check` 銜接 `work-on`、`submodule-relay` 銜接 `release`）改寫成 `dev-flow:` 並標可選。
- feat: 加 `package.json`（`pi.skills`），pi 也載入得到。
