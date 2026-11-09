---
name: implement
description: 照規格實作功能的入口——讀前次經驗、開分支、規格品質閘門，再交給 superpowers 規劃與執行（沒裝走極簡退路）；計畫最後一步做規格比對、整合測試、寫 LEARNINGS.md、回填規格。Use when 「開始實作」「實作這個功能」「照規格做」「照規格實作」「開發這個功能」「implement feature」。
argument-hint: "<功能名或規格路徑>"
---

# 實作功能（入口）

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

本 skill 夾在 superpowers 的頭尾：前段（本檔）讀經驗、開分支、過規格閘門；規劃、執行、審查、收尾交給 superpowers；後段（`references/after.md`）由計畫的最後一個 task 執行。**規格是唯一依據**：實作與驗收都對照 `<spec.dir>` 的規格，不對照對話記憶。

## 使用者輸入

```text
$ARGUMENTS
```

繼續前**必須**先考慮使用者輸入（若不為空）。

## 0. 讀設定與前次經驗

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir   # 預設 docs/specs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get scale      # lean｜full，預設 lean
```

讀 `<spec.dir>/LEARNINGS.md`（沒有就略過），挑出跟本功能相關的條目，步驟 3 交給規劃時一起帶上。「否決」條目一律照抄：規劃不再提出已否決的方案，除非使用者自己重開。

## 1. 分支與工作區

```bash
git branch --show-current && git status --short
```

| 檢查項 | 規則 | 失敗處理 |
|--------|------|----------|
| 工作區乾淨 | 沒有未提交變更 | 未提交變更只有 `<spec.dir>` 下的規格／探索摘要（explore、spec 不 commit）→ 不停下：先照下一列開功能分支，逐檔 `git add` 這些檔，commit 成分支第一個 commit（`docs(spec): <功能名> 規格`），再繼續；有其他未提交變更 → 停下問使用者（先 commit 或保留），不自動 stash |
| 非主幹 | 不在 main／develop 上實作 | 開 `feature/<name>`（從專案慣例的基底分支） |
| 分支對應本功能 | 分支名含功能或票的識別碼 | 停下，提示切分支或 cd 到正確 worktree |
| worktree 一致 | 在 worktree 裡時，目錄名含分支識別碼 | 提醒使用者確認 |

要平行開發時用 `workspace:worktree`（可選；沒裝就 `git worktree add <路徑> -b feature/<name>`）。

## 2. 定位規格與品質閘門

- 規格在 `<spec.dir>/` 底下找本功能的檔（`scale: full` 時是 FRD／SAD／BFS／FFS 一組）。找不到 → 停下，建議先跑 `lifecycle:spec`；使用者明說不寫規格時，把他的描述當目標交給步驟 3，回報標「無規格」。
- 規格裡還有 `[NEEDS CLARIFICATION]` → 停下問使用者，不猜。
- 跑 `lifecycle:spec-check` 驗規格品質（lean 規格已在 `lifecycle:spec` 之後跑過、結論 ✅ 且規格之後沒再改 → 不重跑，直接繼續；沒跑過或之後改過才跑。lean 的 spec-check 全流程只跑這一次）：
  - 通過 → 繼續。
  - 有條件通過（⚠️，0 critical、有 warning）或不通過 → 修規格後重驗（⚠️ 也是修正後才開發，與 spec-check 一致），**最多 3 次**；3 次仍不過 → 列剩餘缺失，請使用者決定。

## 3. 交給規劃與執行

可用 skill 清單裡有 `superpowers:writing-plans` → 叫用它，輸入規格路徑、`spec.dir`、`scale`、步驟 0 挑出的 LEARNINGS 條目（含否決），並明確要求：

> 計畫開頭寫明規格路徑與 `spec.dir`。計畫的最後一個 task 是後段：照 `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/after.md` 做。

寫進計畫時把 `${CLAUDE_PLUGIN_ROOT}` 換成實際絕對路徑（計畫檔不會展開變數）。之後：

- **執行**交給 superpowers（`superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，照 writing-plans 結尾的選擇）。
- **收尾**交給 `superpowers:finishing-a-development-branch` 的選單；要 draft PR 就選它的 push＋開 PR 選項，開成 draft。**不自動 merge**。

沒有 `superpowers:writing-plans` → 告訴使用者建議安裝 superpowers（`claude plugin install superpowers@claude-plugins-official`），這次照 `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/fallback.md` 的極簡退路做。回報寫一行「未安裝 superpowers，已改用極簡退路」。

## 錯誤恢復

| 問題 | 處理 |
|------|------|
| 測試失敗 | 單獨跑該測試、開詳細輸出；修之前三方比對（規格、程式、真實資料），不靠靜態猜 |
| migration 失敗 | 照專案的 migration 修復流程（修正後重跑，不硬回退） |
| 同一問題連修 3 次不過 | 停下重估，落檔失敗原因與已排除的假設再換方向 |

## 相關 skill

- `lifecycle:spec`、`lifecycle:spec-check` — 規格的產出與驗證（步驟 2）
- `superpowers:writing-plans`、`superpowers:subagent-driven-development`、`superpowers:executing-plans`、`superpowers:finishing-a-development-branch` — 規劃到收尾（可選，建議安裝）
- `lifecycle:qa-verify` — 收尾後的實機驗收；`lifecycle:release` — 發版
- `workspace:worktree`、`workspace:quality-check` — 可選

`workspace:` 開頭的是 workspace plugin 的 skill（user 層，通常已裝）；沒裝時照各處寫的退路做，並在回報寫一行「未安裝 workspace，已改用 …」。
