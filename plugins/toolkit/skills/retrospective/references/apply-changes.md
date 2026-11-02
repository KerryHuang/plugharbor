# --apply 模式：修改與版號同步

> 由 `retrospective` SKILL.md Step 6 指向；SKILL.md 只保留「先確認再改」的決策，執行細節在此。

## 執行修改

確認後執行：

1. **P0 項目**：修改對應的 SKILL.md / 範本 / reference
2. **P1 項目**：修改，標記 `<!-- retrospective {date}: {改進描述} -->`
3. **P2/P3 項目**：不修改，僅列入報告

修改後：

1. **版號同步——不要自己改版號。** 呼叫 marketplace 的 `release-plugin` skill（或該 repo 等效機制）
   統一處理，它會同步 **plugin.json ／ marketplace.json ／ README.md 三處**。

   > ⚠ **本 skill 曾寫死「patch +1」且只提 plugin.json，兩點都錯**：
   > 版號級距要依變更性質判斷（新增 skill／reference 或改流程結構是 **minor**，非 patch）；
   > 且 marketplace 的 law 要求三處同步，只改一處會讓安裝端拿到舊版。
   > **改 plugin 這件事本身就有既有機制，不要在這裡重新發明。**

2. 依該 plugin 或專案的 `CLAUDE.md` 完成其餘要求（多數要求同批更新 `CHANGELOG.md`）
3. 執行該專案的驗證指令（如 `claude plugin validate .`）確認結構正確；若失敗，顯示錯誤並回滾該項修改
4. **驗證新增檔案的引用可達性**——新增 reference 時，確認引用它的 skill 用對路徑
   （`${CLAUDE_PLUGIN_ROOT}/references/x.md` 對 plugin 根、裸 `references/x.md` 對該檔所在目錄），
   兩種基準不可混用
5. 確認本次待驗指標已追加進 `{retrospective.path}/metrics.yml`，且 `yaml.safe_load` 解析通過
6. 列出所有變更檔案

---


