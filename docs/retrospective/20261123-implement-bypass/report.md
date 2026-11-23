# 流程回顧報告

上一版 4 條到期指標有 2 條未生效；本次歸出 3 個根因，P0 2 項、P1 1 項；新增待驗指標 3 條。

**日期**：2026-11-23
**回顧範圍**：本機 Claude Code 在 11-09～11-23 的全部 session（跳過測試沙箱），重點是 22 個照規格實作的 session，以及 plugharbor `docs/feature.md` 的 commit 史
**使用的 Skills**：toolkit:retrospective
**Plugin 版本**：lifecycle 4.3.1、workspace 1.20.5、toolkit 0.32.1

## 上一版驗證（Step 0）

| 上次的觀察指標 | 判定 | 本次證據 |
|---|---|---|
| M-20261109-02 照規格實作叫到 implement ≥ 80% | ❌ | 22 個 session 中 2 個（約 9%）；只算有 lifecycle 設定的 repo 是 9 個中 1 個 |
| M-20261109-03 workspace 三個 skill 沒有歸零 | ❌ | 改前 1 次，改後 0 次 |
| M-20261109-04 派工帶 model ≥ 95% | ✅ | 1,231／1,233（99.8%），漏帶的 2 次都是內建 web-fetch，屬設計內 |
| M-20261109-05 Bug 票走 implement 的摩擦為 0 | ✅ | 0 次，但樣本為 0 |

## 根因歸併（Step 2）

| 根因 | 表徵 | 次數 |
|---|---|---|
| R1：implement 入口放在 superpowers 自動交接鏈的外面，鏈一啟動就不會再經過它 | brainstorming→writing-plans→直接執行 13 次；派工 worker 拿到「照計畫實作」直接開工 6 次；後段驗收 0／9；事後另外補回填的 commit ≥ 9 | 19 |
| R2：先寫票號、後開票（或忘了開） | feature.md 撞號或對帳差異 4 次；11-16 修過之後，11-18、11-23 又發生 | 4 |
| R3：workspace 的 debugging、review 已被 superpowers 取代，description 卻仍常駐每個 session | 4 週內只叫用過 1 次 | 固定成本 |

## 改進摘要

| 類別 | P0 | P1 | P2 | P3 | 合計 |
|---|---|---|---|---|---|
| 流程 | 1 | | | | 1 |
| Reference | | 1 | | | 1 |
| Skill 內容 | 1 | | | | 1 |

## 詳細發現

### P0 — 立即修復

**1. R1：implement 入口被繞過（上一版 ❌）**
- 上一版的解法是改 description 觸發句、改 superpowers.md 的措辭。這個方向已經失敗：鏈條根本沒有經過「使用者說開始實作」那一刻，措辭寫得再清楚也不會被讀到。
- 修法要換方向，擇一：
  - **(a) 掛 hook**：lifecycle 新增 PreToolUse hook，在 Skill 叫 `superpowers:writing-plans`、`executing-plans` 或 `subagent-driven-development` 時檢查。若 repo 有 `.plugharbor/lifecycle.yml`，且本 session 還沒叫過 `lifecycle:implement`，就注入提醒「先叫 lifecycle:implement」。worker session 也會觸發，不必另改派工 prompt。
  - **(b) 退回入口角色**：把 implement 的必要部分（after.md 的驗收對照和回填）改成計畫範本固定的最後一個 task，由 writing-plans 帶進計畫；implement 本身降為選用。
- 動作：(a) 是新增 hook。刪或改既有句都不夠，因為觸發點根本不在文字裡；(b) 是改寫既有流程。由使用者裁決走哪個。

**2. R3：workspace:debugging、workspace:review 退場（固定成本）**
- 修法：從 workspace 移除這兩個 skill，或把 description 縮成一句只在沒裝 superpowers 時才觸發的退路。agent-orchestration 已經由使用者停用，維持現狀。
- 動作：刪。

### P1 — 下次更新

**3. R2：票號先寫後開**
- 修法：改寫 `lifecycle/references/feature-checklist.md`「同步票」表的「新增項目」和「新增 `##` 節」兩列，寫明「先 create，行尾只能寫 create 回傳的號碼，不可自行預編號」。
- 動作：改寫既有句。

### P2／P3

無。

## 轉交（非 plugin 歸屬）

無。派工 prompt 不寫 implement 的問題併入 R1(a) 一起解，hook 在 worker session 也會觸發。

## 值得固化的好模式

- 用一支 transcript 掃描腳本（`scan.py`）一次量完 4 條指標，判定都附數字。下次 Step 0 可以直接重跑。

## 本次的待驗指標

| 編號 | 指標 | 判準 | 到期 | 不如預期時 |
|---|---|---|---|---|
| M-20261123-01 | implement 入口（R1 修法上線後） | 有 lifecycle 設定的 repo 中，叫了 writing-plans／executing-plans／SDD 的 session，同 session 也叫了 lifecycle:implement 的比例 ≥ 80% | date: 2026-12-14 | (a) 失敗就改走 (b)；到期時 R1 還沒套用就判 fail 並重新排程 |
| M-20261123-02 | 票號先寫後開（R2） | 11-24～12-14 期間，plugharbor 寫「補開票、撞號、對帳差異」的 commit 數 = 0 | date: 2026-12-14 | 改成清單新增項目一律走腳本，由腳本開票並寫回票號 |
| M-20261123-03 | workspace 兩個 skill 退場（R3） | 退場後到 12-14，回饋佇列中要求恢復，或找不到這兩個 skill 的糾正 = 0 | date: 2026-12-14 | 恢復成只在沒裝 superpowers 時觸發的退路版 |

## 版本建議

- R1(a)：lifecycle 4.3.1 → 4.4.0（新增 hook）；R1(b)：lifecycle 4.4.0（改流程結構）
- R2：lifecycle 補 patch（可與 R1 同版）
- R3：workspace 1.20.5 → 2.0.0（刪 skill 屬 BREAKING）
