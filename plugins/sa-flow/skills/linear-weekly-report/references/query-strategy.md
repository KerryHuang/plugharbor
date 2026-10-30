# Linear 查詢策略

## 原則

1. **無相依查詢同批發出**
2. **分頁拉到底**：`hasNextPage` 為真就帶 `cursor` 續拉。只取第一頁會少算
   （實測初版因此少算數張，淨變化誤報）
3. **大結果會自動落檔**：工具回傳超限時會存成檔案並給路徑，
   改用 `jq`／`python` 讀，**不要為了塞進對話而砍欄位重試**。
   落檔複本與所有衍生檔一律放 workspace 根 `.tmp/weekly-report/`，用完即刪
4. **需要 title 的清單，故意把 `description` 加進 `fields`** 逼它落檔，
   再用 jq 砍掉 description 留下要的欄位——比分次撈快

## 兩批

**第一批（平行）**

| 用途 | 條件 |
|------|------|
| 上週異動全量 | `updatedAt: -P7D`，含 `completedAt`／`createdAt`／`labels`／`project` |
| 期限資料 | 同上再撈一次帶 `dueDate`／`estimate`，用 id join |
| 各狀態存量 | 依狀態名分別查（測試中／待驗收／前端被擋／需求中；實際 state 名稱用 `list_issue_statuses` 查） |

**第二批（依第一批結果）**

- 要判斷「缺票」時的全量查詢（`query` 關鍵字 + team 篩選）
- 案子維度的補查

## 客戶歸戶

規則（label 而非 `project`）見 SKILL.md Step 3。客戶 label 組用 `list_issue_labels` 查，
「通用／全客戶」類 label 另列，不寫死名稱。`project` 覆蓋率實測偏低。
