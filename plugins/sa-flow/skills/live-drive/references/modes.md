# 四模式 — 觀察重點與產出模板

所有模式共用 `browser-bootstrapping.md`(連線/登入/截圖)與 `safety.md`(環境判定)。以下只列各模式的差異。

## investigate — 重現/調查問題、issue/bug

**觀察重點**:重現步驟、`list_console_messages` 的錯誤、失敗 network 請求(4xx/5xx)、前後狀態截圖。**失敗請求一律用 `get_network_request` 取完整 Request/Response**——這是開 Bug 票的關鍵證據。

**步驟**:
1. 取得問題描述(票號 / 使用者回報)與預期 vs 實際。
2. 依描述逐步操作重現;截圖只拍重現前、重現瞬間各一張,中間步驟不拍。
3. 重現的瞬間蒐證(等同 F12「Console + Network」):
   - `list_console_messages` 取 console 錯誤。
   - `list_network_requests`(`resourceTypes:["xhr","fetch"]`)找出失敗請求的 `reqid`。
   - 對該 `reqid` 呼叫 `get_network_request` 取**完整 Request(方法/URL/標頭/payload)+ Response(狀態碼/內文/trace id)**。
   - 導頁會清掉清單;必要時 `includePreservedRequests:true`,或在導頁前先取。
4. 嘗試最小重現路徑(能穩定重現的最短步驟)。

**產出模板**(存 `.tmp/live-drive/<session>/`,結尾問是否交棒):
```markdown
# {問題} 重現報告
- 環境 / URL：
- 預期 vs 實際：
## 最小重現步驟
1. … （附截圖）
## 證據（Bug 票就緒）
- Console 錯誤：
- 失敗請求：
  - {方法} {URL} → {狀態碼}
  - Request payload：{JSON / 表單欄位}
  - Response body：{錯誤碼 / 訊息 / 欄位驗證明細}
  - Trace ID：{x-trace-id，供後端對 log}
## 初判
- 可能根因方向（待 linear-triage 深入）：
```
**交棒**:→ `sa-flow:linear-triage`(開/分流票)或 `sa-flow:linear-reply`(回票);上述「Bug 票就緒」證據可直接貼入票內。

## manual — 寫操作手冊

**觀察重點**:每一步的畫面與操作對象。

**步驟**:
1. 與使用者確認手冊涵蓋的流程與目標讀者。
2. 逐步操作,**每步 `take_screenshot`** 落 `.tmp/`,再複製到交付 repo 的圖片資料夾。
3. 依目標文件格式撰寫(步驟編號 + `![img]` 截圖 + 注意事項)。

**產出模板**:
```markdown
# {功能} 操作手冊
## 前置
## 步驟
1. {動作說明}
   ![img](Images/xx-01.png)
## 常見問題
```
**交棒**:獨立成品,寫到使用者指定路徑(預設詢問路徑)。

## e2e — 端對端測試

**觀察重點**:每步「預期結果」vs「實際結果」,逐步斷言。

**步驟**:
1. 取得要驗的使用者流程與各步預期結果。
2. 逐步操作;每步比對實際(畫面 / 文字 / network 結果)與預期,標記 PASS/FAIL。
3. FAIL 步驟附截圖 + console。

**產出模板**:
```markdown
# {流程} E2E 執行報告
- 環境 / URL：
| # | 步驟 | 預期 | 實際 | 結果 |
|---|------|------|------|------|
| 1 | … | … | … | ✅/❌ |
## 失敗詳情
- 步驟 N：{截圖 + console}
## 結論：{全通過 / N 項失敗}
```
**交棒**:→ 建議將通過流程落成 Cypress spec(由使用者決定,**不自動寫**)。

## explore — 現況分析 / 新 feature 探索

**觀察重點**:既有功能實際**怎麼運作**、輸入輸出、邊界、隱含規則。

**步驟**:
1. 鎖定要勘察的功能 / 模組。
2. 操作各路徑(正常 + 邊界輸入),觀察畫面、欄位、狀態變化、network。
3. 記錄行為事實與疑點(與預期不符、未文件化的規則)。

**產出模板**:
```markdown
# {功能} 現況行為分析
- 環境 / URL：
## 觀察到的行為
- {畫面/欄位/狀態}（附截圖）
## 邊界與隱含規則
## 疑點 / 待釐清
```
**交棒**:→ `sa-flow:explore`(進需求探索)/ `sa-flow:system-analysis`(成現況分析文件)/ `sa-flow:requirement`。
