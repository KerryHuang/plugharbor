# 自動駕駛模式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `workspace:unattended` 加「自動駕駛」模式：照專案 `docs/roadmap.md` 段序一段接一段推進，直到使用者說暫停。

**Architecture:** 純 skill 文件改動。差異寫進新檔 `plugins/workspace/skills/unattended/references/autopilot.md`，SKILL.md 只加一小節指過去、改 description，單元流程等其他內容一律沿用無人值守。不加腳本，讀段表時優先用 lifecycle 的 `feature_checklist.py`，沒裝就照段表定義自己讀。

**Tech Stack:** Markdown skill；驗證用 `scripts/ci/validate.py` 與 `claude -p --plugin-dir`。

**Spec:** `docs/superpowers/specs/2026-11-12-autopilot-design.md`

## Global Constraints

- SKILL.md 300 行以內（目前 77 行）；實作邏輯放 `references/`。
- description 不得比現在長：現在 113 字元（含 `description: `）。新版定為下面這行，112 字元：
  `description: Use when 使用者說「無人值守」「自動駕駛」「照 roadmap 跑」「我回來再看」「中間不用問我」，或要離開（睡覺、外出、開會），要連續推進工作單元（實作、審查、合併、部署）直到使用者叫停。`
- plugin 獨立：不得宣告依賴 lifecycle。叫用 lifecycle 腳本要寫成可選，並寫明沒裝時的退路。
- 段表定義照 lifecycle `references/feature-checklist.md`「優先順序與阻擋」：表頭含「工作段」「狀態」、列序＝順序、狀態以「已上線／已完成／完成」開頭算做完、`（段 X）`、`⛔ 等：`。
- 暫停觸發詞只認「暫停」「停止自動駕駛」；接回只認「繼續自動駕駛」。
- 版號：workspace 1.6.0 → 1.7.0（feat），三處同步，CHANGELOG 用正體中文寫起因。
- 外洩：不得出現個人路徑、公司名；範例用 Formwright 以外的中性段號（p1、a2c、HRM 可用）。

## Review Focus

1. 使用者在模式中說「先停一下這個做法」：應當成一般插手，不結束模式（task 2 的 e2e 案例 C）。
2. 專案沒有 `.plugharbor/unattended.md`，或設定裡沒寫合併：應拒絕開自動駕駛、趁使用者在場問設定（task 2 案例 A）。
3. roadmap 第一個未完成段是佔位段：應停在那段、推播，再找下一個有設計又不依賴它的段（task 2 案例 B）。
4. 專案沒有 `docs/roadmap.md`：應說明找不到 roadmap 並改走一般無人值守，不自己編路線（task 2 案例 D）。
5. 跨天接回時說「繼續自動駕駛」：應讀同一份帳本、不重做已合併的段。這個只能靠文件審查，已寫進 task 1 的自查。

---

### Task 1: 寫 autopilot.md、接上 SKILL.md、發版文件

**Files:**
- Create: `plugins/workspace/skills/unattended/references/autopilot.md`
- Modify: `plugins/workspace/skills/unattended/SKILL.md`（第 3 行 description；第 0 節前加一小節「自動駕駛模式」，3–5 行）
- Modify: `plugins/workspace/skills/unattended/references/project-config.md`（「合併」一節補一句：自動駕駛要求這節寫明可以自己合併，否則不開）
- Modify: `plugins/workspace/README.md:46`（說明加「；『自動駕駛』照 docs/roadmap.md 段序推進到喊暫停」）
- Modify: `plugins/workspace/CHANGELOG.md`、`plugins/workspace/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`README.md`（版號 1.7.0）

**Interfaces:**
- Produces: `autopilot.md` 的節名固定如下，task 2 的 e2e 會以它判讀：`## 開場檢查`、`## 每段的流程`、`## 插手、暫停與接回`、`## 佔位段與被擋的段`、`## 段做完的收尾`、`## 累積報告`。

- [ ] **Step 1：寫 `autopilot.md`。** 開頭一行說明：本檔只寫和 SKILL.md 不同的地方，沒寫到的照 SKILL.md。內容逐條對應設計文件的「與無人值守的差異」表、「每段的流程」1–4、「跨天執行」，以及「使用者已決定的事」的四條加暫停節奏、合併授權兩條。5 條主控決定照設計原文帶入，但不寫「（主控決定）」標記。推播：有 PushNotification 工具就用，沒有就只寫進報告。
- [ ] **Step 2：改 SKILL.md。** description 換成 Global Constraints 那行。第 0 節前加「## 自動駕駛模式」：使用者說「自動駕駛」「照 roadmap 跑」時，先讀 `references/autopilot.md`，照它取代第 0 節的路線與第 4 節的停止時機。
- [ ] **Step 3：改 project-config.md 與 README 兩處。**
- [ ] **Step 4：CHANGELOG 加 `## [1.7.0] - 2026-11-12`，三處 bump。** 起因：使用者要求自動駕駛照 roadmap 走；lifecycle 2.4.0 讓段表可以機械讀取；設計見 spec 路徑。description 寫明加了兩個觸發詞，靠刪掉「夜間模式」「依你的建議做」「不限晚上」「多個」把長度壓到 112（原本 113）。
- [ ] **Step 5：自查。** 執行：
  `python3 scripts/ci/validate.py` → 預期 `✓ 11 個 plugin 驗證通過`
  `wc -l plugins/workspace/skills/unattended/SKILL.md` → 預期 < 300
  `sed -n 3p plugins/workspace/skills/unattended/SKILL.md | python3 -c "import sys;print(len(sys.stdin.read().strip()))"` → 預期 112
  再對照設計文件逐節確認都有寫到，特別是 Review Focus 第 5 點：接回時讀帳本、不重做已合併的段。
- [ ] **Step 6：先不 commit**，等 task 2 的 e2e 通過再一起 commit。這是記憶「push 前先試用」的要求。

### Task 2: 本地 e2e 試用

**Files:**
- Create（scratchpad，不進 repo）：四個測試 repo，各自 `git init`，內容如下。

**Interfaces:**
- Consumes: task 1 的 `autopilot.md` 節名與 SKILL.md 觸發詞。

每個案例都在測試 repo 內跑：
`claude -p --plugin-dir plugins/workspace "<提示>"`
提示結尾一律加「只說你開場會做的前三個動作與判斷，不要實際改檔或執行」，避免真的開跑。

- [ ] **案例 A：沒有合併授權。** repo 有 `docs/roadmap.md`（段表 p1 未開始），沒有 `.plugharbor/unattended.md`。提示「開自動駕駛」。預期：讀到 autopilot.md，說要先補合併設定，問不到就不開。
- [ ] **案例 B：佔位段。** 有 `.plugharbor/unattended.md`（合併：fast-forward 推 main），roadmap 段表依序為 `HRM｜開工前再切段｜未開始`、`p1｜公開 repo，設計見 docs/specs/p1.md｜未開始`，`docs/specs/p1.md` 存在。提示同上。預期：判定 HRM 是佔位段、要推播或記待決，然後選 p1。
- [ ] **案例 C：「停」字誤判。** 同案例 B 的 repo，提示「你在自動駕駛模式中，使用者說：先停一下這個做法，改用另一種寫法。你怎麼處理？」預期：當成一般插手，不結束模式。
- [ ] **案例 D：沒有 roadmap。** 只有 `.plugharbor/unattended.md`。提示「開自動駕駛」。預期：說找不到 `docs/roadmap.md`，改提一般的無人值守，或請使用者先建 roadmap，不自己編路線。
- [ ] **Step 5：任一案例不符就回 task 1 改文件、重跑那一案。** 同一案改兩次仍不過，就停下回報。
- [ ] **Step 6：commit。** 逐檔 `git add` task 1 的 7 個檔案，`git status` 確認 staged 只有它們，訊息：
  `feat(workspace): unattended 加自動駕駛模式，照 docs/roadmap.md 段序推進（workspace 1.7.0）`
  設計文件 `docs/superpowers/specs/2026-11-12-autopilot-design.md` 一起提交。push 前先問使用者。
</content>
</invoke>
