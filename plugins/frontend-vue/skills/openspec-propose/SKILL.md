---
name: openspec-propose
description: 提出一個新的 OpenSpec change——一步到位產出全部 artifact（proposal / design / tasks），直接可進實作。Use when the user wants to quickly describe what they want to build and get a complete proposal ready for implementation；觸發：「提一個 change」「開一份 proposal」「我要做這個功能，先產規格」「openspec propose」。
---

提出一個新的 change——建立 change 並一步產出全部 artifact。

我會建立一個 change 及其 artifact：
- proposal.md（做什麼 & 為什麼）
- design.md（怎麼做）
- tasks.md（實作步驟）

準備好實作時，執行 /opsx:apply

---

**Input**：使用者的請求應包含一個 change name（kebab-case），**或**一段「想建什麼」的描述。

**步驟**

1. **若沒有清楚的輸入，先問要建什麼**

   用 **AskUserQuestion tool**（開放式，無預設選項）問：
   > 「你想做哪個 change？描述你要建或要修什麼。」

   從描述導出 kebab-case 名稱（例如「add user authentication」→ `add-user-auth`）。

   **重點**：沒搞懂使用者要建什麼之前，不要往下走。

2. **建立 change 目錄**
   ```bash
   openspec new change "<name>"
   ```
   這會在 `openspec/changes/<name>/` 建立含 `.openspec.yaml` 的 scaffold。

3. **取得 artifact 建置順序**
   ```bash
   openspec status --change "<name>" --json
   ```
   解析 JSON 取得：
   - `applyRequires`：實作前需完成的 artifact ID 陣列（例如 `["tasks"]`）
   - `artifacts`：所有 artifact 及其狀態與相依

4. **依序建立 artifact 直到可 apply**

   用 **TodoWrite tool** 追蹤 artifact 進度。

   依相依順序（無 pending 相依的先）逐一處理：

   a. **對每個 `ready`（相依已滿足）的 artifact**：
      - 取指示：
        ```bash
        openspec instructions <artifact-id> --change "<name>" --json
        ```
      - 指示 JSON 含：
        - `context`：專案背景（是給你的約束，**不要**放進輸出）
        - `rules`：該 artifact 的規則（是給你的約束，**不要**放進輸出）
        - `template`：輸出檔要用的結構
        - `instruction`：該 artifact 類型的 schema 導引
        - `outputPath`：寫到哪
        - `dependencies`：需先讀的已完成 artifact
      - 讀相依檔取脈絡
      - 用 `template` 當結構建立 artifact 檔
      - 把 `context` 與 `rules` 當約束套用——但**不要**抄進檔案
      - 顯示簡短進度：「Created <artifact-id>」

   b. **持續到所有 `applyRequires` artifact 完成**
      - 每建完一個就重跑 `openspec status --change "<name>" --json`
      - 檢查 `applyRequires` 裡每個 ID 是否 `status: "done"`
      - 全部 done 就停

   c. **若某 artifact 需要使用者輸入**（脈絡不明）：
      - 用 **AskUserQuestion tool** 釐清
      - 再繼續建立

5. **顯示最終狀態**
   ```bash
   openspec status --change "<name>"
   ```

**輸出**

完成後摘要：
- change 名稱與位置
- 建立的 artifact 清單與簡述
- 就緒訊息：「All artifacts created! Ready for implementation.」
- 提示：「執行 `/opsx:apply` 或叫我實作，即可開始處理 tasks。」

**Artifact 建立準則**

- 依每個 artifact 類型的 `instruction` 欄位建立
- schema 定義了每個 artifact 該含什麼——照著做
- 建新 artifact 前先讀相依 artifact 取脈絡
- 用 `template` 當輸出檔結構，填它的區塊
- **重點**：`context` 與 `rules` 是給你的約束，不是檔案內容
  - 不要把 `<context>`、`<rules>`、`<project_context>` 區塊抄進 artifact
  - 它們引導你寫什麼，但絕不該出現在輸出裡

**護欄**
- 建齊實作所需的全部 artifact（依 schema 的 `apply.requires`）
- 建新 artifact 前一律先讀相依 artifact
- 脈絡嚴重不明才問使用者——但盡量自行做合理決策以維持動能
- 若同名 change 已存在，問使用者要續用還是建新的
- 每寫完一個 artifact 檔，先確認檔案存在再進下一個
