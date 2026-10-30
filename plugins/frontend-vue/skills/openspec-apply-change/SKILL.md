---
name: openspec-apply-change
description: 實作某個 OpenSpec change 的 tasks——選 change、讀脈絡、逐項實作並勾選、遇阻就暫停回報。Use when the user wants to start implementing, continue implementation, or work through tasks；觸發：「開始實作這個 change」「繼續做 tasks」「apply change」「跑這個 change 的實作」。
---

實作某個 OpenSpec change 的 tasks。

**Input**：可指定 change 名稱。若省略，嘗試從對話脈絡推斷；若模糊或不明，**必須**列出可選 change 讓使用者選。

**步驟**

1. **選 change**

   有給名稱就用。否則：
   - 從對話脈絡推斷（若使用者提過某個 change）
   - 只有一個 active change 就自動選
   - 若模糊，跑 `openspec list --json` 取清單，用 **AskUserQuestion tool** 讓使用者選

   一律宣告：「Using change: <name>」並說明如何覆寫（例如 `/opsx:apply <other>`）。

2. **查狀態理解 schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   解析 JSON 理解：
   - `schemaName`：使用的 workflow（例如 "spec-driven"）
   - 哪個 artifact 含 tasks（spec-driven 通常是 "tasks"，以 status 為準）

3. **取 apply 指示**
   ```bash
   openspec instructions apply --change "<name>" --json
   ```
   回傳：
   - context 檔路徑（依 schema 而異——可能是 proposal/specs/design/tasks，或 spec/tests/implementation/docs）
   - 進度（total、complete、remaining）
   - 帶狀態的 task 清單
   - 依當前狀態的動態指示

   **處理狀態：**
   - `state: "blocked"`（缺 artifact）：顯示訊息，建議先補齊 artifact
   - `state: "all_done"`：恭喜，建議 archive
   - 其他：進實作

4. **讀 context 檔**

   讀 apply 指示輸出裡 `contextFiles` 列的檔。檔案依 schema 而異：
   - **spec-driven**：proposal、specs、design、tasks
   - 其他 schema：依 CLI 輸出的 contextFiles

5. **顯示目前進度**

   顯示：使用的 schema、進度「N/M tasks complete」、剩餘 task 概覽、CLI 給的動態指示。

6. **實作 tasks（loop 到完成或受阻）**

   對每個 pending task：
   - 顯示正在做哪個 task
   - 做必要的程式修改
   - 保持變更最小且聚焦
   - 在 tasks 檔把該 task 標完成：`- [ ]` → `- [x]`
   - 進下一個

   **遇下列情況暫停：**
   - task 不清楚 → 請求釐清
   - 實作揭露設計問題 → 建議更新 artifact
   - 遇錯誤或阻礙 → 回報並等指示
   - 使用者打斷

7. **完成或暫停時顯示狀態**

   顯示：本次完成的 tasks、整體進度「N/M tasks complete」、若全完成建議 archive、若暫停說明原因並等指示。

**實作中的輸出**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...實作中...]
✓ Task complete
```

**完成時的輸出**

```
## Implementation Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete ✓

All tasks complete! Ready to archive this change.
```

**暫停時的輸出（遇到問題）**

```
## Implementation Paused

**Change:** <change-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<問題描述>

**Options:**
1. <選項 1>
2. <選項 2>

要怎麼做？
```

**護欄**
- 一路做到完成或受阻
- 開工前一律先讀 context 檔（來自 apply 指示輸出）
- task 模糊就先暫停問，別猜
- 實作揭露問題就暫停、建議更新 artifact
- 程式變更保持最小、聚焦在各 task
- 每完成一個 task 立刻更新 checkbox
- 遇錯誤/阻礙/需求不明就暫停——別亂猜
- 用 CLI 輸出的 contextFiles，別假設特定檔名

**流動式 workflow 整合**

本 skill 支援「對 change 執行動作」的模型：
- **可隨時被叫用**：artifact 未全完成前（只要有 tasks）、部分實作後、與其他動作交錯皆可
- **允許更新 artifact**：實作揭露設計問題時建議更新 artifact——非階段鎖死，流動作業
