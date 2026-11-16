# 退路（沒裝 superpowers 時）

可用 skill 清單沒有 `superpowers:writing-plans` 時照本檔做，取代「規劃 → 執行 → 審查 → 收尾」；SKILL.md 前段與 `after.md` 照跑。計畫格式與 superpowers 相同，之後裝了可無縫接手。

1. **寫計畫**（不因改動小而省略；使用者明說不寫才跳過，回報標「未寫計畫」）：存 `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`（進版控；專案沒這個目錄先問使用者）。`.tmp/` 沒在 `.gitignore` 就提醒一次、推薦加，不自行改。表頭與 task 骨架：

   ````markdown
   # [功能名] Implementation Plan

   > **For agentic workers:** 逐 task 照 `- [ ]` 步驟做、做完就勾；最後一個 task 讀 `after.md`。沒裝 superpowers 時主控自己照本計畫做。

   **Goal:** [一句話]

   **Architecture:** [2-3 句做法]

   **Tech Stack:** [關鍵技術]

   **Spec:** [設計文件路徑]

   ## Global Constraints

   [設計文件的專案層限制，一條一行，值照抄]

   ## Review Focus

   [設計文件暗示、但沒有 task 測到的失敗情境，一條一行；每條補測試到負責的 task]

   ---

   ### Task N: [元件名]

   **Files:**
   - Create: `路徑`
   - Modify: `路徑:行號`
   - Test: `路徑`

   **Interfaces:**
   - Consumes: [取自前面 task 的簽名]
   - Produces: [後面 task 依賴的名稱與型別]

   - [ ] **Step 1: 寫失敗測試**（測試名與斷言）
   - [ ] **Step 2: 跑測試確認失敗**（指令與預期）
   - [ ] **Step 3: 實作**（簽名與檔案）
   - [ ] **Step 4: 跑測試確認通過**
   - [ ] **Step 5: Commit**（逐檔 `git add`）
   ````

   最後一個 task 固定是「照 `<plugin 根>/skills/implement/references/after.md` 做」（plugin 根＝本檔往上三層 `../../../`，寫成絕對路徑）。
2. **計畫審查**：照 `plan-review.md`；必修修完才往下。給使用者確認一次再開工；中斷後從第一個沒勾的 step 接續。
3. **逐 task 做**：主控自己做，排除最後的 after.md task（留到步驟 5，只跑一次）。開工前跑一次既有測試，紅的就停下告知。每個 task：寫失敗測試、看它紅 → 實作 → 看它綠 → 勾選。同一項連修 3 次不過 → 停下，列失敗與已試做法問使用者。
4. **自審**：全部完成後自己審整份 diff（`git diff <基底分支>` 加 `git status --short` 的未追蹤新檔），對照設計文件找漏與多做；重大問題修完重跑測試。回報標「自審」。
5. **收尾**：自審與修正完成後才跑最後一個 task（`after.md`）；逐檔 `git add`（不用 `-A`／`.`）、Conventional Commits commit；問使用者要不要 push、開 PR。不 merge。
