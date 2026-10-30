# --apply 模式：修改、版號同步與進化追蹤

> 由 `retrospective` SKILL.md Step 6 指向；SKILL.md 只保留「先確認再改」的決策，執行細節在此。

## 執行修改

確認後執行：

1. **P0 項目**：修改對應的 SKILL.md / 範本 / reference
2. **P1 項目**：修改，標記 `<!-- retrospective {date}: {改進描述} -->`
3. **P2/P3 項目**：不修改，僅列入報告

修改後：

1. **版號同步——不要自己改版號。** 交該 repo 既有的版號同步機制（release 腳本或 skill）
   統一處理，它應同步 **plugin.json ／ marketplace.json ／ README.md** 等所有版號位置。

   > ⚠ 版號級距要依變更性質判斷（新增 skill／reference 或改流程結構是 **minor**，非 patch）；
   > 只改一處會讓安裝端拿到舊版。**改 plugin 這件事本身就有既有機制，不要在這裡重新發明。**

2. 依該 plugin 的 `CLAUDE.md` 規範完成其餘要求（多數 plugin 要求同批更新 `CHANGELOG.md`）
3. 執行 `claude plugin validate .` 確認結構正確；若失敗，顯示錯誤並回滾該項修改
4. **驗證新增檔案的引用可達性**——新增 reference 時，確認引用它的 skill 用對路徑
   （`${CLAUDE_PLUGIN_ROOT}/references/x.md` 對 plugin 根、裸 `references/x.md` 對該檔所在目錄），
   兩種基準不可混用
5. 列出所有變更檔案

---


