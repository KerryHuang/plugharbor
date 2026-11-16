---
name: implement
description: 照設計文件實作功能的入口——開分支、實作前檢查，再交給 superpowers 規劃與執行（沒裝走同格式退路）；計畫審查後才開工，最後一步對照驗收、回填。Use when 「開始實作」「實作這個功能」「照規格做」「照規格實作」「開發這個功能」「implement feature」。
argument-hint: "<功能名或規格路徑>"
---

# 實作功能（入口）

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔實體路徑：symlink 先 `realpath`，同目錄有 `.plugharbor-root` 就以其內容為 plugin 根；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

本 skill 夾在 superpowers 的頭尾：前段（本檔）開分支、實作前檢查；規劃、執行、審查、收尾交給 superpowers；後段（`references/after.md`）由計畫的最後一個 task 執行。**設計文件是唯一依據**：實作與驗收都對照 `<spec.dir>` 的設計文件，不對照對話記憶。

## 使用者輸入

```text
$ARGUMENTS
```

繼續前**必須**先考慮使用者輸入（若不為空）。

## 0. 讀設定

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir   # 預設 docs/superpowers/specs
```

## 1. 分支與工作區

```bash
git branch --show-current && git status --short
```

| 檢查項 | 規則 | 失敗處理 |
|--------|------|----------|
| 工作區乾淨 | 沒有未提交變更 | 未提交的只有本功能的設計文件與 `<spec.dir>/analysis/<feature>/`（spec 寫完不 commit）、只多了 `spec:` 區塊的 `.plugharbor/lifecycle.yml`，以及 `.tmp/` 底下的工作檔 → 不停下：先照下兩列確認分支（在主幹就開功能分支；不在主幹但分支名不對照第三列停下），逐檔 `git add` 設計文件與設定檔（`.tmp/` 不 add），commit 成分支第一個 commit（`docs(spec): <功能名> 設計文件`），再繼續；有其他未提交變更 → 停下問使用者（先 commit 或保留），不自動 stash |
| 非主幹 | 不在 main／develop 上實作 | 開 `feature/<name>`（從專案慣例的基底分支） |
| 分支對應本功能 | 分支名含功能或票的識別碼 | 停下，提示切分支或 cd 到正確 worktree |
| worktree 一致 | 在 worktree 裡時，目錄名含分支識別碼 | 提醒使用者確認 |

要平行開發時用 `workspace:worktree`（可選；沒裝就 `git worktree add <路徑> -b feature/<name>`）。

## 2. 定位設計文件與實作前檢查

- 設計文件在 `<spec.dir>/` 底下找本功能的檔（`*-design.md`、`<feature>.md`，找不到再找 `*<feature>*.md`）。找不到 → 停下，建議先跑 `lifecycle:spec`；使用者明說不寫時，把他的描述當目標交給步驟 3，回報標「無設計文件」。
- 還有 `[NEEDS CLARIFICATION]` → 停下問使用者，不猜。
- 重算雜湊，與開頭行下一行的 `> 實作前檢查：✅ YYYY-MM-DD（內容 <8 碼>）` 比對：

  ```bash
  grep -v '^> 實作前檢查：' <文件> | shasum | cut -c1-8
  ```

  相同 → 已通過、正文沒改過，跳過；沒有紀錄行或不同 → 跑 `lifecycle:spec-check`。有條件通過（⚠️）或不通過 → 修設計文件後重驗，**最多 3 次**；3 次仍不過 → 列剩餘缺失，請使用者決定。

## 3. 交給規劃與執行

計畫與計畫審查不因改動小而省略；只有使用者明說不寫計畫才跳過，回報標「未寫計畫」。

**既有計畫**：`docs/superpowers/plans/` 下已有 **Spec** 欄指向本設計文件的計畫（使用者直接走 superpowers 寫完）→ 不重叫 writing-plans，只補：最後一個 task 是 after.md（沒有就加，路徑寫實際絕對路徑）；找不到 `.tmp/implement/<feature>/plan-review-*.md` 就照 `plan-review.md` 審；然後交執行。

沒有既有計畫時，可用 skill 清單裡有 `superpowers:writing-plans` → 叫用它，輸入設計文件路徑，並明確要求：

> 計畫的 **Spec** 欄寫設計文件路徑。最後一個 task 是後段：照 `<plugin 根>/skills/implement/references/after.md` 做。計畫存好、自審後，先照 `<plugin 根>/skills/implement/references/plan-review.md` 審，必修修完再做 Execution Handoff（請使用者看的是審過的版本）。

`<plugin 根>` 即 `${CLAUDE_PLUGIN_ROOT}`，寫進指令時換成實際絕對路徑（計畫檔不展開變數）。計畫審查（`plan-review.md`）排在使用者核准與開工之前。之後：

- **執行**交給 superpowers（`superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，照 writing-plans 結尾的選擇）。
- **收尾**交給 `superpowers:finishing-a-development-branch` 的選單；要 draft PR 就選 push＋開 PR，開成 draft。**不自動 merge**。

沒有 `superpowers:writing-plans` → 建議使用者安裝 superpowers（`claude plugin install superpowers@claude-plugins-official`），這次照 `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/fallback.md`（計畫格式相同）做。回報寫一行「未安裝 superpowers，已改用退路」。

## 錯誤恢復

| 問題 | 處理 |
|------|------|
| 測試失敗 | 單獨跑該測試、開詳細輸出；修之前三方比對（設計文件、程式、真實資料），不靠靜態猜 |
| migration 失敗 | 照專案的 migration 修復流程（修正後重跑，不硬回退） |
| 同一問題連修 3 次不過 | 停下重估，落檔失敗原因與已排除的假設再換方向 |

## 相關 skill

- `lifecycle:spec`、`lifecycle:spec-check` — 設計文件的產出與實作前檢查（步驟 2）
- `superpowers:writing-plans`、`superpowers:subagent-driven-development`、`superpowers:executing-plans`、`superpowers:finishing-a-development-branch` — 規劃到收尾（可選，建議安裝）
- `lifecycle:qa-verify` — 收尾後的實機驗收；`lifecycle:release` — 發版
- `workspace:worktree`、`workspace:quality-check` — 可選

`workspace:` 開頭的是 workspace plugin 的 skill（user 層，通常已裝）；沒裝時照各處寫的退路做，並在回報寫一行「未安裝 workspace，已改用 …」。
