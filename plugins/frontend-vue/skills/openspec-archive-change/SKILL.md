---
name: openspec-archive-change
description: 封存一個已完成的 OpenSpec change——檢查 artifact/task 完成度、評估 delta spec 同步、移到 archive 目錄。Use when the user wants to finalize and archive a change after implementation is complete；觸發：「封存這個 change」「archive change」「這個 change 做完了收掉」「歸檔 change」。
---

封存一個已完成的 change。

**Input**：可指定 change 名稱。若省略，嘗試從對話脈絡推斷；若模糊或不明，**必須**列出可選 change 讓使用者選。

**步驟**

1. **沒給名稱就讓使用者選**

   跑 `openspec list --json` 取清單，用 **AskUserQuestion tool** 讓使用者選。

   只顯示 active change（非已封存）。若有 schema 資訊一併顯示。

   **重點**：不要猜或自動選。一律讓使用者選。

2. **檢查 artifact 完成狀態**

   跑 `openspec status --change "<name>" --json`。

   解析 JSON：
   - `schemaName`：使用的 workflow
   - `artifacts`：各 artifact 狀態（`done` 或其他）

   **若有 artifact 非 `done`：**
   - 顯示警告，列出未完成的 artifact
   - 用 **AskUserQuestion tool** 確認是否仍要繼續
   - 確認後才繼續

3. **檢查 task 完成狀態**

   讀 tasks 檔（通常 `tasks.md`），統計 `- [ ]`（未完成）vs `- [x]`（完成）。

   **若有未完成 task：**
   - 顯示警告，列出未完成數量
   - 用 **AskUserQuestion tool** 確認是否仍要繼續

   **若無 tasks 檔：** 略過 task 相關警告，繼續。

4. **評估 delta spec 同步狀態**

   檢查 `openspec/changes/<name>/specs/` 是否有 delta spec。沒有就略過同步提示。

   **若有 delta spec：**
   - 逐一與對應的主 spec（`openspec/specs/<capability>/spec.md`）比較
   - 判斷會套用哪些變更（新增、修改、移除、改名）
   - 提示前先顯示合併摘要

   **提示選項：**
   - 若需變更：「立即同步（建議）」、「不同步直接封存」
   - 若已同步：「直接封存」、「仍要同步」、「取消」

   若使用者選同步，用 Task tool（subagent_type: "general-purpose"）派發同步 delta spec 到主 spec 的工作，並附上已分析的 delta spec 摘要。無論選項為何都繼續封存。

5. **執行封存**

   建立 archive 目錄（若不存在）：
   ```bash
   mkdir -p openspec/changes/archive
   ```

   用當前日期產生目標名稱：`YYYY-MM-DD-<change-name>`

   **檢查目標是否已存在：**
   - 若是：報錯，建議改名既有 archive 或用不同日期
   - 若否：把 change 目錄移到 archive

   ```bash
   mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
   ```

6. **顯示摘要**

   顯示封存完成摘要：change 名稱、使用的 schema、archive 位置、是否同步 spec（如適用）、任何警告（未完成 artifact/task）。

**成功輸出**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs（或 "No delta specs" 或 "Sync skipped"）

All artifacts complete. All tasks complete.
```

**護欄**
- 沒給就一律讓使用者選 change
- 用 artifact graph（`openspec status --json`）檢查完成度
- 不因警告卡住封存——只告知並確認
- 移到 archive 時保留 `.openspec.yaml`（它會隨目錄一起移）
- 顯示清楚的結果摘要
- 若要求同步，走 agent 驅動的 delta spec 同步
- 若有 delta spec，一律先跑同步評估、顯示合併摘要再提示
