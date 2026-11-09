# Changelog

格式：每次改動 `skills/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.5.0] - 2026-11-09

- feat(ai-radar): 每日版——launchd 工作日 09:00 叫 `skills/ai-radar/scripts/daily.py run`，每天把採納待辦分數最高、能在 repo 內完成的 1 項做成專用 worktree 裡的本機 `radar/<日期>-<編號>` branch 草稿（不 push，待審滿 3 個就停），另蒐集工作模式內工具的官方 changelog 最多 3 條，報告寫 `<OUT>/<日期>-daily.md`；流程見 `skills/ai-radar/references/daily.md`。
- feat(ai-radar): 執行邊界——模型沒有 Bash，分兩階段跑 `claude -p`：消化只有 worktree 內的 Read／Edit／Write／Glob／Grep、看得到挑中的那一項待辦；蒐集只有 WebSearch／WebFetch、看得到工具名稱與公開官方發布資料。兩階段都不載入任何 settings 檔、hook、plugin 與 MCP（`--setting-sources ""`、`--strict-mcp-config`、`--restricted`、`dontAsk`）。git、驗證、backlog 標記、報告、通知全由 runner 做：檢查改動路徑、以 `main` 已 commit 的 `validate.py` 驗證、固定訊息 `radar: #<編號>` commit 且不跑 hook；檔名另外做外洩掃描，沒有 `.leak-denylist` 就不做草稿；任一項失敗就丟棄改動並通知。
- feat(ai-radar): runner 驗證 worktree 身分（拒絕主 checkout、核對 common git dir 與註冊紀錄）、`fcntl.flock` 互斥鎖、週末不跑（含睡眠補跑）、全部成功才寫完成標記（失敗報告保留、同日可重跑）。
- feat(ai-radar): `skills/ai-radar/scripts/work_profile.py` 統計近 30 天 transcript 用到的 skill、CLI、MCP server、副檔名，輸出 `work-profile.md`（純腳本、不呼叫模型，每日版每週重算；給蒐集階段的只有列在 `references/public-tools.txt` 或 plugharbor marketplace 的工具名稱，用白名單、不靠黑名單）。
- feat(ai-radar): `skills/ai-radar/scripts/install-daily.sh` 安裝／移除 launchd 排程；plist 先寫暫存檔、`plutil -lint` 通過才原子替換。只在新草稿、草稿滿、執行失敗時通知。

## [0.4.2] - 2026-11-05

- fix(plugin-harvest): `lock check` 對 monorepo 子目錄只看該子目錄——`lock add` 多記 `subtree`（子目錄的 tree id），repo 有新 commit 但子目錄沒變時回 `SAME`，不再誤報 `UPDATED`；授權檔先找子目錄自己的，沒有才用 repo 根目錄。舊鎖定檔沒有 `subtree` 時照舊比整個 repo、授權照舊看根目錄（不會一律誤報 `LICENSE-CHANGED`）。
- fix(plugin-harvest): 查授權的暫存 clone 在 Windows 刪不掉唯讀的 `.git/objects` 而殘留在 %TEMP%，改成補上寫入權限再刪（Windows 實機回報）；讀不到的目錄照舊略過，不讓 `lock check` 中斷。
- fix(plugin-harvest): 深讀後比對基準 repo 的 `git status` 排除 `.claude/worktrees/`，並行 session 的 worktree 不再被誤判成深讀污染而中止（ai-radar 週報實跑回報）。
- docs(plugin-eval): 「跳過已評過的」比對前先用 `gh api` 把 repo 轉成現名，改名的 repo 不會繞過去重。

## [0.4.1] - 2026-11-05

- fix(plugin-harvest): 第④批延後小問題——`parse-url` 支援無 scheme 與 SSH 網址、非 GitHub 主機的 key 帶主機名、裸字不再被當成本機路徑；授權檔認 `LICENSE-MIT`／`LICENSE-APACHE`／`UNLICENSE` 等並支援雙授權；`lock check` 每筆一行、鎖定檔壞掉 exit 2 不丟 traceback、查授權改無 blob 淺 clone（`--filter=blob:none` + `ls-tree`）；測試清理相容 Windows 唯讀檔。
- docs: plugin 搜尋來源從 ai-radar `sources.md` 搬到共用 `references/plugin-sources.md`，plugin-harvest 搜尋步驟引用；`plugin-eval.md` 比對鍵說明對齊程式，註明分支名含 `/` 的限制。
- chore: `package.json` 版號補齊（0.4.0 漏改）。

## [0.4.0] - 2026-11-05

- feat(plugin-harvest): 候選來源加入 skills.sh 搜尋 API（查不到就略過），搜尋階段不執行 `npx skills`；排序的相關度也納入觸發這次搜尋的能力缺口。

## [0.3.0] - 2026-11-05

- feat(plugin-harvest): 新 skill——領域搜尋熱門 plugin → 深讀對照基準 → 逐條核准的具體提案 → 只套用核准的；採納時寫 `harvest-lock.json`（來源、commit、授權檔 hash），`--check-lock` 檢查上游更新與授權變動；`--lean` 給 ai-radar 週報用。
- feat(plugin-harvest): `skills/plugin-harvest/scripts/harvest.py`（網址拆解、鎖定檔寫入與檢查，純標準庫＋git）。
- refactor(ai-radar): 只留情報（大廠規範、工程實踐、設定最佳化、知識庫稽核）；區塊 4 改叫用 `plugin-harvest --lean`，`--plugin <網址>` 保留為轉交入口。
- fix(plugin-harvest): 實測回饋——深讀必讀加 `commands/` 與非 plugin 形態的設定／主程式、prompt 帶基準 repo 路徑、README 宣稱不算證據且主執行緒抽查；monorepo 子目錄不計整個 repo 星數；排行表與領域 slug 有落點；清理改為獨立步驟。
- fix(plugin-harvest): 審查修正——網址去 query／fragment、支援 `/blob/`、`www.` 正規化；annotated tag 取 peeled commit、釘 commit 的 ref 報 PINNED；stdout UTF-8、git 不等帳密；深讀後檢查基準 repo 未被改；本機路徑與直接裝用不寫鎖定檔；ai-radar 改讀檔照做精簡模式（Skill 工具叫不動 disable-model-invocation 的 skill）。
- refactor: `plugin-eval.md`、`adoption-backlog.md` 搬到 plugin 根 `references/`，兩個 skill 共用；網址一律經 `harvest.py parse-url` 拆解。

## [0.2.1] - 2026-11-03

- fix(ai-radar): 深讀 subagent 不再自己 rm -rf clone 目錄（會被使用者確認規則擋下而卡住），改回報「待清」路徑，由主執行緒一條指令刪完。

## [0.2.0] - 2026-11-03

- feat(ai-radar): 區塊 4 每週深讀前 5 個 plugin 候選並產評估卡（裝用／借鑒／不理），新增 --plugin <網址> 單獨評估；結論接進採納待辦。

## [0.1.0] - 2026-10-30

- feat: 初版——`graphify`（資料夾建知識圖譜）、`ai-radar`（每週 AI 情報雷達與採納待辦對帳）。
- chore: `adoption-backlog.md` 只留規則與格式，個人待辦不隨 plugin 發佈；graphify 去除本機安裝說明。
