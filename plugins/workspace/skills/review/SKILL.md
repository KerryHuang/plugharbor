---
name: review
description: Clean Architecture 程式碼審查——委派審查型 subagent 檢查分層依賴、測試、安全性、效能，產出結構化審查報告。Use when reviewing code changes, PRs, or conducting architecture review, "審查程式碼", "review PR", "架構審查", "審查變更".
---

# 程式碼審查

委派專業審查型 subagent，對變更做全面的架構與品質審查。

**預設只報告**：不改檔、不 commit、不留言、不 merge，使用者明確要求才做。結論要附證據——每個變更檔歸到檢查項或寫排除理由、「查無」前先證明查法抓得到已知命中、標出被削弱的測試／拉長的 timeout／新 suppression、新套件查 registry——細則見 `references/evidence.md`，派審查 subagent 時把該檔路徑寫進 prompt。

## 審查範圍

| 範圍 | 用法 | 說明 |
|------|------|------|
| PR 審查 | `review pr {n}` | 審查特定 Pull Request |
| 本地變更 | `review changes` | 審查未提交變更 |
| 分支審查 | `review branch feature/xxx` | 審查特定分支 |

## 工作流程

1. **準備** — 檢查 `git status` / `git diff`；若審 PR 則先 `gh pr view {n} --json state,isDraft`：
   - `CLOSED`／`MERGED` → 停下，告知使用者，不審。
   - 其餘（含 draft）→ `gh pr checkout {n}` 照審；draft 在報告標註。
2. **品質檢查** — 先跑建置與測試確認基本盤（見 `quality-check`）。
3. **委派審查** — 交給審查型 subagent，聚焦下列面向：
   1. Clean Architecture 分層依賴與依賴方向
   2. 架構決策合理性
   3. 外部整合／背景排程／資料存取的實作品質（依專案實際採用者）
   4. 測試覆蓋率與測試品質
   5. 錯誤處理、效能、安全性、可擴展性
   6. 專案規範合規（限路徑範圍、須引用原文，見 `references/evidence.md` 第 7 節）
4. **驗證與過濾** — 見下節「發現驗證與誤報排除」，只留下成立的發現。
5. **彙整報告** — 合併結果，給出總體評估與行動項目，最後附「證據」段（見 `references/evidence.md` 第 6 節）。

## 審查遠端 PR／MR 並 merge

要列出開啟中的 PR／MR、審查後留言 request changes 或 merge 收尾（GitHub `gh`／GitLab `glab`）時，讀 `references/review-remote.md`：CLI 對照、流程、留言規則（完整 SHA 連結、suggestion 條件）。

## 發現驗證與誤報排除

審查 subagent 的發現先過這一關才進報告：

1. **排除**（直接丟，不必驗證）：
   - 既有問題：這次 diff 沒碰到的行，或改動前就存在的寫法。
   - 建置、型別檢查、linter／analyzer 會抓的問題（第 2 步已跑過）。
   - 改動前就存在、已用 ignore／suppress 註解明確靜音的（這次 diff **新增**的 suppression 不排除，照 `references/evidence.md` 第 4 節列出）。
   - 吹毛求疵：命名偏好、格式、「可以更優雅」這類不影響正確性、安全、效能，也不違反專案明文慣例的意見。
2. **驗證**：剩下的 🚫／⚠️ 發現，每條派一個獨立的唯讀 subagent（`model: sonnet`），只給該條發現與 `file:line`，
   要它讀程式碼回答「成立／不成立＋一句依據」。不成立就丟；同一則訊息平行派出。💡 次要項不驗證。
3. 報告的「發現的問題」只列成立的；附一行「排除 N 條、驗證後剔除 M 條」。

## 審查檢查清單

### Clean Architecture
- [ ] Domain 層無外部依賴
- [ ] 層級依賴方向正確（外層依賴內層）
- [ ] 介面定義在適當的層
- [ ] 依賴注入正確使用

### 資料存取
- [ ] 無 N+1 查詢
- [ ] 查詢已最佳化、索引適當
- [ ] 連線／交易管理正確

### 整合與背景工作（如適用）
- [ ] 連線／重試／逾時管理完整
- [ ] 背景工作支援取消令牌
- [ ] 錯誤處理與日誌記錄充分

### 測試
- [ ] 單元測試覆蓋新功能
- [ ] 測試案例有意義、涵蓋邊緣案例
- [ ] 測試可維護

### 安全性
- [ ] 輸入驗證完整
- [ ] 無敏感資訊暴露
- [ ] 認證授權正確
- [ ] 錯誤訊息不洩漏內部資訊

### 效能
- [ ] 無不必要的查詢
- [ ] 適當使用批次處理
- [ ] 非同步操作正確、無阻塞
- [ ] 無記憶體洩漏風險

## 報告格式

```markdown
# 程式碼審查報告

## 整體評估
[✅ 核准 / ⚠️ 需要修改 / 🚫 要求變更]

## 品質指標
| 項目 | 分數 |
|------|------|
| Clean Architecture | [/10] |
| 資料存取 | [/10] |
| 測試覆蓋率 | [%] |
| 效能 | [/10] |
| 安全性 | [/10] |

## 架構評估
[分層與依賴方向的分析]

## 發現的問題
[問題 + 建議]

## 行動項目
- [ ] [需修正項目 1]
- [ ] [需修正項目 2]
```

## 審查結果分類

- ✅ **Approved（核准）** — 無重大問題，可合併。
- ⚠️ **Needs Changes（需要修改）** — 有次要問題，不阻擋合併但建議修正。
- 🚫 **Request Changes（要求變更）** — 有重大問題必須修正，阻擋合併。

## 與其他 skill 銜接

- `quality-check` — 審查前執行品質檢查
- `commit` — 審查通過後建立提交
