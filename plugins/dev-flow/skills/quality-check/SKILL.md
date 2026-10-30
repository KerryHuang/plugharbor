---
name: quality-check
description: 全面程式碼品質檢查——建置驗證、測試執行、覆蓋率分析、問題優先排序。Use when validating code quality before commit or deployment, "品質檢查", "quality check", "跑測試看覆蓋率", "提交前檢查", "建置測試驗證".
---

# 品質檢查

執行全面的品質驗證並產出詳細報告。以 .NET 為例列指令，其他工具鏈比照替換。

## commit 前驗證原則

commit 前的驗證只回答一件事：**這個 repo 自己定義的檢查有沒有過**。下面的原則優先於後面所有範例指令。

1. **只跑專案自帶的 script**：從 README、`CONTRIBUTING`、CI 設定（`.github/workflows/`、`.gitlab-ci.yml` 等）、
   `package.json` scripts、`Makefile`、`scripts/` 找出 CI 實際跑的那組，照抄指令與工作目錄。不自己組 `npx tsc`、`dotnet test <sln>` 之類的替代品——
   專案 script 帶著 heap 上限、設定檔路徑、環境變數、測試 allowlist 這些不起眼的 flag，少一個結果就不同。
   找不到自帶 script 時才退回本頁範例，並在回報裡寫明「無自帶 script，改用 X」。
2. **在 repo 根目錄跑、包在子 shell、輸出先落檔**：
   ```bash
   (cd <repo 絕對路徑> && <指令>) > <scratch>/verify-<repo>.log 2>&1; echo "EXIT=$?"
   ```
   多步用 `&&` 串在同一個子 shell，第一步失敗就停，`EXIT` 是那一步的碼。
3. **禁 `| grep`／`| tail` 直接接檢查指令**：工具崩潰（OOM、找不到設定）和「檢查通過」在管線後都是空輸出，
   而管線的 exit code 是最後一個指令的。要篩就篩落檔後的 log。
4. **只認 exit code**：`EXIT=0` 才算通過；非 0 就停下不 commit，從 log 取失敗段落（測試名＋錯誤訊息）交給使用者。
   沒讀到 exit code 的 repo **不算驗證過**，回報要寫「未驗證」，不可寫成通過。
5. **已知環境性失敗要有清單與依據**：例如整合測試需要本機沒起的 broker／DB。只有全部失敗都落在清單內才視為通過，回報時寫明哪一類、幾條；不在清單上的一律當真。
6. **commit 時 hook 也是驗證的一部分**：有些 lint 只在 pre-commit hook 裡看得到 staged 內容，事前直接跑會漏驗。
   hook 擋下時把原文交給使用者，不自行 `--no-verify` 或加繞過變數。
7. **跨多個 repo 逐一跑**、各自判定；只改文件或只改測試的 commit 依專案慣例可免驗，但要明說「此 repo 無 commit 前驗證」。

| 念頭 | 實際上 |
|---|---|
| 「沒有輸出，應該是過了」 | 崩潰也是沒有輸出。只認 exit code |
| 「直接跑底層工具比較快」 | 少了 script 的 flag，結果不可信 |
| 「只跑我改到的那支測試」 | 別支測試的 mock 可能因你的改動而壞，整套跑 |
| 「失敗是既有的，先跳過」 | 判斷既有要有證據（stash 後重跑同指令比對），且由使用者決定 |
| 「測試太久，跳過」 | 跳過就明說「未驗證」 |

## 工作流程

0. **找專案自帶指令** — 依上節原則從 README／CI 設定找；有就以它取代下列步驟
1. **還原依賴** — `dotnet restore`
2. **建置檢查** — `dotnet build -c Release --no-restore`（Release 組態）
3. **執行測試** — `dotnet test --logger:trx --results-directory TestResults`
4. **程式碼分析** — 啟用分析器並將警告視為錯誤 `dotnet build /p:RunAnalyzers=true /p:WarningsAsErrors=true`
5. **智能分析** — 複雜結果委派品質分析型 subagent 做模式識別與修復排序（見下）

## 常用指令

```bash
# 完整品質檢查
dotnet restore && dotnet build -c Release && dotnet test --logger:trx

# 帶覆蓋率
dotnet test --collect:"XPlat Code Coverage" --results-directory TestResults

# 格式檢查
dotnet format --verify-no-changes

# 套件檢查
dotnet list package --outdated
dotnet list package --vulnerable
```

## 品質標準

### 建置
- 無編譯錯誤
- 無編譯警告（警告視為錯誤）

### 測試
- 所有測試通過
- 無跳過的測試

### 覆蓋率（依層級遞減，數值可依專案調整）
- Domain: 90%+
- Application: 85%+
- Infrastructure: 75%+

## 問題優先級

| 優先級 | 類型 | 行動 |
|--------|------|------|
| 🔴 Critical | 編譯錯誤、測試失敗 | 立即修復 |
| 🟡 High | 品質警告、低覆蓋率 | 今天修復 |
| 🟠 Medium | 技術債、程式碼異味 | 本週修復 |
| 🟢 Low | 清理、格式化 | 待辦清單 |

## 智能分析（委派）

複雜問題委派品質分析型 subagent，要求它：

1. **模式識別** — 按根本原因分組相似的錯誤/警告。
2. **優先排序** — 用「影響 × 工作量」矩陣排序（對應上表優先級）。
3. **可行建議** — 每個問題類別給：檔案:行位置、根因說明、修復方案與程式碼範例、預估修復時間。
4. **修復排程** — 分「立即（接下來數小時）／短期（本週）／長期改進」。

## 報告格式

```
=== 品質檢查報告 ===

【建置狀態】
✅ 建置成功    ⚠️ 警告: 0    ❌ 錯誤: 0

【測試結果】
✅ 通過: {n}    ❌ 失敗: 0    ⏭️ 跳過: {n}
總計: {n}    成功率: {%}

【測試覆蓋率】
Domain / Application / Infrastructure：各層 % 與總體 %

【品質分數】: {0-100}

【關鍵問題】 / 【建議】 / 【下一步驟】
```

## 故障排除

```bash
# 建置失敗：清理並重建
dotnet clean && dotnet restore && dotnet build

# 測試失敗：詳細輸出
dotnet test -v detailed --logger:trx

# 依賴問題：清 NuGet 快取
dotnet nuget locals all --clear && dotnet restore --force
```

## 何時執行

- 建立提交之前
- 開 Pull Request 之前
- 完成重大重構後
- 作為 CI/CD 驗證的一部分

## 與其他 skill 銜接

- `work-on` — 實作段落完成後的品質閘門
- `review` — 審查前先跑品質檢查
- `commit` — 提交前先驗證
