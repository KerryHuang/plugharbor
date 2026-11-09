# 簡單優先

用最少的程式碼解決問題，不寫投機性的東西：

- 不加沒被要求的功能與「彈性」。
- 單次使用的程式碼不抽象化；三行重複勝過過早抽象。
- 寫了 200 行但 50 行能解決，就重寫。

# 外科手術式修改

- 只碰必要的地方，不順手改相鄰程式碼的註解與格式。
- 自己的修改造成的孤兒（import／變數／函式）要清乾淨；既有的 dead code 不動，只提出。

# 目標驅動

- 改第一行前先說出驗收方式：哪條指令、哪個操作或誰來判斷——
  「修 bug」→「寫一個重現它的測試，看它失敗，再讓它通過」。
- 回報時本機測試、build、commit、push、上線各自宣稱，不拿一個代替另一個；
  驗收方式沒實際跑到的需求標「未驗證」。

# 能力缺口

同一件事換過做法仍失敗兩次、已裝 skill 幫不上（缺專門知識或工具，非程式 bug），或使用者要找現成 skill／plugin／工具時，依序找：

1. plugharbor：開場列為停用、或 `~/.claude/plugins/marketplaces/plugharbor/plugins/` 裡沒裝的，讀 SKILL.md 照做再問要不要啟用。
2. 外部：WebFetch `skills.sh/api/search?q=<關鍵字>` 列候選；要裝就提問提議 `/research:plugin-harvest <關鍵字>`，同意後讀上述目錄的 `research/skills/plugin-harvest/SKILL.md` 照做（不能用 Skill 工具）。

外部的都經它核准才裝；使用者不同意就用現有能力繼續。
