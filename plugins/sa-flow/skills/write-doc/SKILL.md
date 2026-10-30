---
name: write-doc
description: "手動把一份文件寫入磁碟：詢問路徑與內容後寫檔。用於使用者口述或手邊已有內容要落檔；規格鏈四大棒（FRD／SAD／BFS／FFS）由 spec-writer agent 直接寫入指定路徑，不經此。"
argument-hint: "[目標路徑]"
model: haiku
---

# 寫入文件

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

手動將文件內容寫入磁碟。

## 執行流程

### 1. 取得路徑與內容

使用 `AskUserQuestion` 詢問：
- 目標檔案完整路徑
- 要寫入的完整文件內容

### 2. 確認目錄存在

```bash
mkdir -p "{父目錄路徑}"
```

### 3. 寫入文件

使用 Write 工具寫入 `path`。

### 4. 確認完成

輸出一行：

```
文件已寫入：{path}
```

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| 路徑格式無效（含非法字元） | 提示路徑格式有誤，用 `AskUserQuestion` 重新詢問 |
| 目錄建立失敗 | 顯示錯誤訊息，終止 |
| 寫入失敗 | 顯示錯誤訊息，不重試，終止 |

## 使用範例

```bash
write-doc
# → 詢問路徑：docs/訂單管理/訂單查詢/訂單查詢_需求文件.md
# → 詢問內容：（貼入完整 markdown）
```
