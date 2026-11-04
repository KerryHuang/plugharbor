# Light API 存在性確認指引

> 此步驟對應 specify-backend SKILL Step 4.1。目的：撰寫 BFS §6（API 規格）之前，確認規格書將引用的參照表 Light API 是否已存在，避免 FFS 引用不存在的端點。

## 確認方式（擇一）

```bash
# 搜尋現有 Light API Controller
grep -r "Light" . --include="*{Controller 檔副檔名}" -l

# 或直接搜尋 Light Response 定義
grep -r "GetLight" . --include="*.{原始碼副檔名}" -l
```

## 處理方式

| 確認項目 | 狀態 | 處理方式 |
|---------|------|---------|
| 所有 §5 分析出的參照實體（廠商、類別、倉庫等）是否已有 `/Light` 端點 | ✅ 已存在 / ❌ 不存在 | 存在：BFS §6 直接引用 |
| Light API 不存在的參照實體 | ❌ 不存在 | 在 BFS §6 新增此端點規格（`GET /Light`），同時通知前端需等候 Light API 完成後才能開發選擇器 |

> **注意**：若 Grep 與其他可用工具都無法確認，可詢問使用者（`AskUserQuestion`），但不可在規格書中直接引用未確認存在的 Light API。
