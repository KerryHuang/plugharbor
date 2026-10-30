---
name: migration-troubleshoot
description: Use when diagnosing special EF Core migration situations — ModelSnapshot 衝突、歷史紀錄遺失、資料庫已套用但 migration 對不上、生產緊急回滾判斷。一般失敗修復循環走 ef-migration skill。觸發：「migration 對不上」「snapshot 衝突」「緊急回滾」「migration 診斷」。
---

# EF Core Migration 特殊情境診斷

> **職責邊界**：
> - 一般 migration flow（建立 / 套用 / 回復 / 失敗修復）→ `ef-migration` skill
> - 特殊診斷情境（本 skill）→ ModelSnapshot 衝突、歷史遺失、生產緊急回滾

共用參數（依專案調整 project 路徑與 sln 名稱）：

```bash
EF_ARGS="--project src/YourApp.Domain --startup-project src/YourApp.Domain"
```

## 診斷表

| 症狀 | 可能原因 | 診斷指令 |
|------|---------|---------|
| Migration 無法建立 | 建置失敗 | `dotnet build YourApp.sln -c Release` |
| Migration 套用失敗 | SQL 錯誤 | `dotnet ef database update --verbose $EF_ARGS` |
| ModelSnapshot 衝突 | 多人並行開發 | 檢查 git 衝突 |
| 資料庫狀態不明 | 手動修改資料庫 | `dotnet ef migrations list $EF_ARGS` |
| Factory log 顯示連錯 host | 連線 CLI args / env var 設錯 | 檢查連線注入參數 |

## 常見錯誤處理

### ModelSnapshot 衝突

```bash
git stash                                        # 保存你的變更
git pull                                          # 拉最新
dotnet ef migrations remove $EF_ARGS              # 移除你的 migration
git stash pop                                     # 還原變更
dotnet ef migrations add {NewName} $EF_ARGS --context AppDbContext
```

### 資料庫已套用但 Migration 遺失（同步狀態）

```bash
dotnet ef migrations add EmptySync $EF_ARGS       # 建立空 migration
# 手動清空 Up() 和 Down()
dotnet ef database update $EF_ARGS                # 只寫 __EFMigrationsHistory
```

### 一般失敗修復循環

走 `ef-migration` skill 的失敗修復段（讀錯誤、修 .cs、重跑，不用 `migrations remove`）。

### 生產緊急回滾

回滾指令見 `ef-migration` skill。本 skill 補充**診斷檢查清單**：

- [ ] 確認回滾版本 `Down()` 方法正確
- [ ] 產生回滾 SQL 腳本並審查（`dotnet ef migrations script {from} {to} $EF_ARGS --output rollback.sql`）
- [ ] 備份資料庫
- [ ] 測試環境驗證回滾
- [ ] 通知相關團隊
- [ ] 記錄事故報告
