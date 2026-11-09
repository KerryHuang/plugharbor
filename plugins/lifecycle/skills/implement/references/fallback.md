# 極簡退路（沒裝 superpowers 時）

可用 skill 清單沒有 `superpowers:writing-plans` 時照本檔做，只取代「規劃 → 實作 → 審查 → 收尾」；前段（SKILL.md）與後段（after.md）照跑。功能只做最基本的，完整流程請安裝 superpowers。

1. **任務清單**：寫進 `.tmp/implement/<feature>/tasks.md`（`<feature>` 只用 ASCII kebab-case；`.tmp/` 沒在 `.gitignore` 就問使用者，推薦「加」，不自行改）。開頭抄規格路徑、`spec.dir` 與 LEARNINGS 相關條目（含否決）；每項一行：

   ```markdown
   - [ ] T1 <目標>（規格：§3.2 BL-04）— 依賴：無 — 驗收：`<指令>` 預期 <結果>
   ```

   最後一項固定是「後段：照 `<plugin 根>/skills/implement/references/after.md` 做」（plugin 根＝本檔往上三層 `../../../`，寫成絕對路徑）。給使用者確認一次再開工；中斷後從第一個沒勾的項目接續。
2. **逐項做**：主控自己做，不派 subagent。開工前跑一次既有測試，紅的就停下告知。照依賴順序，每項：寫失敗測試、看它失敗 → 實作 → 跑該項驗收與既有測試 → 通過才勾選。同一項連修 3 次不過 → 停下，列失敗與已試做法問使用者。
3. **審查**：全部勾完後派一個全新的 subagent 審整份 diff（`git diff <基底分支>` 加 `git status --short` 列出的未追蹤新檔；有 `lifecycle:reviewer` 就用它，它沒有 Bash，先把 diff 寫成 `.tmp/implement/<feature>/diff.patch` 再給路徑）。沒有 subagent 工具就自審，回報標「自審」。重大與主要問題修完重跑測試。
4. **提交**：逐檔 `git add`（不用 `-A`／`.`），用 Conventional Commits 訊息 commit；再問使用者要不要 push、開 PR。不 merge。
