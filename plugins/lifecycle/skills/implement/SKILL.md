---
name: implement
description: 照規格把功能從開分支做到交付——讀前次經驗、規劃任務清單與進度 ledger 落檔、每個 task 派全新 subagent、規格比對、審查修正迴圈、關卡式收尾、完工寫 LEARNINGS.md；支援 TDD。Use when 「開始實作」「實作這個功能」「照規格做」「開新功能」「開發這個功能」「從頭到尾做完」「端到端開發」「work on」「implement feature」。
argument-hint: "<功能名或規格路徑> [--tdd]"
---

# 實作功能

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

從規格到交付的一條龍：讀經驗 → 分支 → 規格閘門 → 規劃落檔 → 基線 → 逐 task 派工 → 規格比對 → 審查迴圈 → 完成驗證 → 寫經驗 → 關卡式收尾。

三條不變的紀律：

- **規格是唯一依據**：實作、審查、驗收都對照 `<spec.dir>` 底下的規格，不對照對話記憶。
- **狀態落檔、不靠對話**：任務清單、進度 ledger、每個 task 的 brief 與報告都寫進 `.tmp/implement/<feature>/`（不進 git）；中斷後讀 ledger 接續。格式見 `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ledger.md`。
- **主 session 只統整、派工、判讀**：寫碼、寫測試、審查都派 subagent；主 session 只讀 ledger 與報告的結論行。

## 使用者輸入

```text
$ARGUMENTS
```

繼續前**必須**先考慮使用者輸入（若不為空）。含 `--tdd`、或規格／任務清單有 `[TDD]` 標記時走 TDD 順序（見 planning.md）。

## 0. 讀設定與前次經驗

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir   # 預設 docs/specs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get scale      # lean｜full，預設 lean
```

- 讀 `<spec.dir>/LEARNINGS.md`（沒有就略過）。挑出跟本功能相關的條目，抄進 ledger 的「已定決策與注意」段，之後每份 brief 都帶上。
- `.tmp/implement/<feature>/ledger.md` 已存在 → 這是續做：讀 ledger，從第一個沒完成的步驟或 task 接續，不重跑已完成的。

## 1. 分支與工作區

```bash
git branch --show-current && git status --short
```

| 檢查項 | 規則 | 失敗處理 |
|--------|------|----------|
| 工作區乾淨 | 沒有未提交變更 | 停下問使用者（先 commit 或保留），不自動 stash |
| 非主幹 | 不在 main／develop 上實作 | 開 `feature/<name>`（從專案慣例的基底分支） |
| 分支對應本功能 | 分支名含功能或票的識別碼 | 停下，提示切分支或 cd 到正確 worktree |
| worktree 一致 | 在 worktree 裡時，目錄名含分支識別碼 | 提醒使用者確認 |

要平行開發時用 `workspace:worktree`（可選；沒裝就 `git worktree add <路徑> -b feature/<name>`）。

## 2. 定位規格與品質閘門

- 規格在 `<spec.dir>/` 底下找本功能的檔（`scale: full` 時是 FRD／SAD／BFS／FFS 一組）。找不到 → 停下，建議先跑 `lifecycle:spec`；使用者明說不寫規格時，把他的描述寫進 ledger「目標」段當依據，回報標「無規格」。
- 規格裡還有 `[NEEDS CLARIFICATION]` → 停下問使用者，不猜。
- 跑 `lifecycle:spec-check` 驗規格品質：
  - 通過 → 繼續。
  - 有條件通過（0 critical、有 warning）→ 告知使用者，繼續。
  - 不通過 → 修規格後重驗，**最多 3 次**；3 次仍不過 → 列剩餘缺失，請使用者決定。

## 3. 規劃：任務清單與 ledger 落檔

1. 建 `.tmp/implement/<feature>/`，確認 `.tmp/` 在專案 `.gitignore`（沒有就提醒使用者加，不自行改 `.gitignore`）。
2. 派一個規劃 subagent（top 等級），輸入：規格路徑、ledger 的已定決策、`${CLAUDE_PLUGIN_ROOT}/skills/implement/references/planning.md`。它負責：
   - 找受影響的層級與模組、可重用的既有實作（照專案慣例，不引入新風格）。
   - 產 `tasks.md`：每個 task 有 ID、目標、對應的規格段落、要讀與要改的檔、驗收指令、依賴、可平行標記 `[P]`。
   - 標出整合點、風險與邊緣案例。
   有技術選型或架構取捨時，另派 `lifecycle:architect` 出 ADR，結論寫進 ledger「已定決策」。
3. **context 預算檢查**：每個 task 的 brief 加上它要讀的檔，必須塞得進一個 subagent 的 context（判準見 dispatch.md）；塞不下就拆。主 session 自己只讀 ledger 與報告結論，不讀實作檔。
4. 把計畫摘要（task 數、順序、平行組、風險）給使用者確認一次，確認後才開工。

## 4. 基線

跑專案的 build 與測試，確認起點是綠的。基線就紅 → 停下告知使用者，不在紅基線上開工（否則之後分不清是誰弄壞的）。

## 5. 逐 task 派工

派工規則（角色、模型等級、路由、prompt 寫法）見 `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/dispatch.md`。重點：

- **每個 task 開全新 subagent**，不續用上一個。prompt 只給 brief 路徑與已定決策；brief 先寫成 `briefs/<task-id>.md`。
- subagent 把完整報告寫進 `reports/<task-id>.md`，回覆只回一行狀態＋報告路徑。
- 依 `tasks.md` 的依賴逐段執行；`[P]` 且不碰同一批檔的 task 同一則訊息平行派；碰同一檔的必須依序。
- **完成判準在主 session**：subagent 說完成不算，主 session 跑該 task 的驗收指令（或派驗證）看到通過才在 `tasks.md` 打勾、更新 ledger。
- 驗收不過 → 派新 subagent 修（brief 附上一份報告路徑與失敗輸出），**最多 3 次**；仍不過 → 停下，列失敗與已試做法，請使用者決定。
- 非平行 task 失敗 → 暫停後續；平行 task 失敗 → 其餘照跑，失敗的列進 ledger。
- 測試或建置失敗要找根因時，用 `workspace:debugging`（可選；沒裝就派 `lifecycle:debugger`：先寫重現失敗的測試，再修，再驗無回歸）。

## 6. 規格系統性比對

全部 task 完成後，派一個 subagent 對照規格逐條比對（不抽查），報告寫 `reports/spec-trace.md`：

- **層一 介面**：規格列的端點／畫面／指令 vs 實際存在的，逐一確認。
- **層二 規則**：規格的業務／驗證規則 ID vs 實作＋測試，逐條確認有實作也有測試。
- **層三 勾選**：比對無缺後，把規格與任務清單的完成項打勾。

| 結果 | 處理 |
|------|------|
| 有介面或規則未實作 | 補 task 回步驟 5，補完重比 |
| 有實作缺測試 | 派 `lifecycle:tester` 補 |
| 全部完成 | 進步驟 7 |

## 7. 審查修正迴圈（最多 3 輪）

- 有裝 workspace：用 `workspace:review`（可選）審本分支相對基底分支的變更；它的證據規則（每個變更檔歸到檢查項、「查無」先證明指令抓得到、標出被削弱的測試與新 suppression）照做。
- 沒裝 workspace 的退路：同一則訊息平行派 `lifecycle:reviewer`（程式碼）、`lifecycle:architect`（分層與依賴方向）、一個規格對照審查者（規格 vs 程式 vs 真實資料），報告各自落檔（reviewer 唯讀，由主 session 代寫，見 dispatch.md）；至少做到「每個變更檔歸到某檢查項或寫排除理由」，並剔除既有問題、linter 會抓的、吹毛求疵三類。
- 分級：重大必修／主要要修／次要列參考。重大與主要派 developer 修 → 重跑 build＋test → 再審一輪。
- **最多 3 輪**；第 3 輪仍有重大問題 → 停下，列剩餘問題，請使用者決定。

## 8. 完成驗證

用 `workspace:quality-check`（可選；沒裝就跑專案自帶的 build、全部測試、lint）。全綠、所有 task 打勾、規格比對無缺、審查通過，才算實作完成。各項分開記進 ledger，不拿一項代替另一項。

## 9. 寫經驗（LEARNINGS.md）

完成驗證後、收尾前，在 `<spec.dir>/LEARNINGS.md` 最上方加一段（檔案不存在就建立）：

```markdown
## yyyy-mm-dd <功能名>
- <下次規劃前該先知道的事：踩過的坑、規格常漏的地方、拆 task 的教訓、哪個指令會騙人>
```

只寫下次用得上的通則，一段最多 5 條，不寫流水帳；跟既有條目重複就改寫舊條目而不是再加。

## 10. 收尾（關卡式）

用一次提問讓使用者選收尾模式；推薦 A：

| 模式 | 內容 |
|------|------|
| **A. 自動鏈式（推薦）** | commit → push → draft PR → 對已 commit 的最終狀態再審一次並修 → 端到端／整合測試並修 → 規格回填 → 提示解除 draft |
| B. 每關手動確認 | 同 A，每關開跑前先問 |
| C. 再審一次 | 回步驟 7 |
| D. 只 commit | 停在 commit，push 與 PR 由使用者手動 |

每一關都記進 ledger 的關卡表，中斷後從**第一個沒過的關卡**接續；**不自動 merge**（merge 屬使用者），使用者要求代為 merge 時一律帶 `--match-head-commit`。關卡定義與細節見 `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/closing.md`。

提交訊息用 `workspace:commit`（可選；沒裝就照 Conventional Commits 手寫），一律逐檔指名 `git add`，不用 `git add -A`。

## 錯誤恢復

| 問題 | 處理 |
|------|------|
| 建置失敗 | 清快取 → 還原相依 → 重建；仍失敗走步驟 5 的除錯退路 |
| 測試失敗 | 單獨跑該測試、開詳細輸出；修之前三方比對（規格、程式、真實資料），不靠靜態猜 |
| migration 失敗 | 照專案的 migration 修復流程（修正後重跑，不硬回退） |
| 同一問題連修 3 次不過 | 停下重估，落檔失敗原因與已排除的假設再換方向 |

## 相關 skill

- `lifecycle:spec`、`lifecycle:spec-check` — 規格的產出與驗證（步驟 2）
- `lifecycle:qa-verify` — 收尾後的實機驗收
- `lifecycle:release` — 發版
- `workspace:review`、`workspace:quality-check`、`workspace:debugging`、`workspace:commit`、`workspace:worktree` — 可選

`workspace:` 開頭的是 workspace plugin 的 skill（user 層，通常已裝）；沒裝時照各處寫的退路做，並在回報寫一行「未安裝 workspace，已改用 …」。
