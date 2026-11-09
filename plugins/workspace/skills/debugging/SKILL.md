---
name: debugging
description: 照專案自帶指令除錯，並把規格書轉成測試案例（補 superpowers 的除錯與 TDD）。Use when 任務標記 [TDD]、--tdd、要由規格轉測試案例、沒裝 superpowers 要精簡除錯退路.
---

# 除錯與測試先行（環境細節）

裝了 superpowers 時，方法照 `superpowers:systematic-debugging` 與 `superpowers:test-driven-development`，本 skill 只補下列環境細節；沒裝就照下方「退路迴圈」。

**沒有可重現的失敗測試就不動手改碼。**

- 測試與建置指令一律用**專案自帶**的（README、CI、`package.json`、`Makefile` 找得到的那支）；迭代期帶篩選條件只跑相關測試，全 suite 留到最後回歸。有裝 `backend` 且是 .NET 專案時，指令與範本見其 `unit-testing` 的 .NET 附錄（可選）。
- 規格轉測試案例、`[TDD]`／`--tdd` 標記的任務、輸出格式：見 [references/tdd-cycle.md](references/tdd-cycle.md)。

## 退路迴圈（沒裝 superpowers）

重現（寫失敗測試，確認紅燈；一開始就綠代表沒重現到）→ 找根因（從失敗點向上追，追到源頭，不在下游遮症狀）→ 修（改在正確的層）→ 驗證（目標測試轉綠、全測試無回歸、建置成功）。

## 症狀對照根因

| 症狀 | 可能原因 |
|------|---------|
| Null 參考例外 | 依賴未註冊、設定值／連線字串為空 |
| 資料不正確 | 查詢或轉換邏輯錯誤 |
| 輸出未更新 | 狀態變更未觸發、快取未失效 |
| 操作無回應 | 前置條件判斷回傳 false、事件未綁定 |

## 改在正確的層

- 領域邏輯問題 → 修改實體／領域規則
- 應用流程問題 → 修改應用服務
- 資料存取問題 → 修改 Repository／查詢
- 呈現層問題 → 修改 Controller／視圖模型
