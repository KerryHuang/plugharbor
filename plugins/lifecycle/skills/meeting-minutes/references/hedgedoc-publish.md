# 發布到自架 HedgeDoc（`publish-target: hedgedoc:<url>`）

**未驗證**：以下依 HedgeDoc 1.x 的 `POST /new` 建立筆記行為撰寫，尚未對實際伺服器實測。plugharbor 不提供公用 HedgeDoc；使用者需自架，且 `<url>` 是自己的伺服器。

## 流程

1. 發布前用 `AskUserQuestion` 取得同意（SKILL.md §3.3）。
2. 嘗試匿名建立（伺服器允許匿名編輯時）：

   ```bash
   curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' \
     -X POST -H 'Content-Type: text/markdown' \
     --data-binary @<會議記錄檔> "<url>/new"
   ```

   回 `302` 且 `redirect_url` 是筆記網址 → 回報該網址。
3. 回其他狀態（常見：需要登入）→ **不要試著繞過驗證**。告知使用者登入方式因伺服器而異，請他自行貼上檔案內容或處理登入後重發；本機檔案已落檔，不受影響。

## 規則

- 發布**整份**記錄，與本機檔一致，不另做精簡版。
- 不把登入憑證寫進檔案或對話。
- 發布失敗不回頭改本機檔。
