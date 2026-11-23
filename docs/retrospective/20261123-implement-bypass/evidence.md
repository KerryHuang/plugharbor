# 證據附檔（20261123-implement-bypass）

來源：本機 Claude Code transcript（`~/.claude/projects`，跳過 `-private-tmp` 測試沙箱），期間 2026-11-09 12:21（+08）～11-23；量測腳本 `scan.py`。僅本機 Claude Code，Codex／pi／別台機器未計。

## M-20261109-02：implement 入口

- 「照規格實作」session 判定：使用者訊息含「照規格／照計畫／開始實作」等，或叫了 `superpowers:executing-plans`／`subagent-driven-development`。
- 全部 repo：22 個 session，叫到 `lifecycle:implement` 2 個（約 9%）。
- 只算有 `.plugharbor/lifecycle.yml` 的 repo（plugharbor 含 worktree、formwright）：9 個，叫到 1 個（約 11%）。
- 繞過路徑：
  - brainstorming → writing-plans → 直接執行：13 次（5e9bc2c6、eae5ad0f、737d0587、d79793d8、306014a1、235cf7ee、89f8aa02、26ede331、12a58800、a7947a21、6adb12cc 等）
  - 派工 worker 拿到「照計畫實作」prompt 直接叫 SDD／executing-plans：6 次（d251cac7、aed55813、d317fa34、45c09b63、ee563918、f67a980a）
- 後段（`implement/references/after.md`）抽查 9 個 session：`spec_to_cases`／`acceptance-trace` 工具呼叫 0 筆。
- 事後補回填 `docs/feature.md` 的獨立 commit（plugharbor，11-14～11-17）：62efbfb、21dc4a5、6793a35、dabe34b、878181d、a3930bc、3d54269、b5dfc41、492b0bb。blog：9834399、46c6817。

## M-20261109-03：workspace 三個 skill

- `workspace:debugging`、`workspace:agent-orchestration`、`workspace:review` 的 Skill 叫用次數：改前 14 天（10-26～11-09）1 次（review），改後 14 天 0 次。
- 和 superpowers 同名 skill 在同一 session 重複叫用：0 次。
- `workspace:agent-orchestration` 目前已由使用者停用。

## M-20261109-04：派工帶模型

- Agent 派工 1,233 次，帶 model 1,231 次（99.8%）。
- 漏帶的 2 次都是 `web-fetch`（5c26ed20 L1561、8d86b449 L48）。web-fetch 是內建專用 agent，`agent-model-guard` 只替通用型補 model，屬設計內行為。

## M-20261109-05：Bug 票走 implement

- 期間沒有任何 session 同時叫了 `ticket-create` 和 `lifecycle:implement`，樣本為 0。

## feature.md 行尾寫了 #號 卻沒開票

| commit | 日期 | 內容 |
|---|---|---|
| e7eb532 | 11-16 | 段 D1 補開票、回填票號 |
| 5fc534e | 11-16 | demo-video 新節沒開票，對帳差異 7，補開 #46～#52 |
| 1853d0c | 11-18 | Herdr.app 節與速度規則寫了 #53～#55 但沒開票，撞號，補開 #56～#58 |
| 6cce665 | 11-23 | agent-mesh-check 構想寫了 #62 但沒開票，與 PR #62 撞號，補開 #64（來源是 dfaa520） |

每日對帳（reconcile.py）只能事後發現，沒有攔下這幾次。

## 本 session 觀察（各 1 次，列觀察不改）

- `ask-question-guard` 擋下 description 太短的選項，修正後重問，花了 1 輪。
- 自動模式擋下 `gh issue create`，改用 AskUserQuestion 取得同意後放行。
