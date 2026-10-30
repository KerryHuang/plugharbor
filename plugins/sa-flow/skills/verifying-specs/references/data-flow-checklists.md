# Task 2 資料流驗證檢查清單

> 對應 SKILL.md Task 2.1 / 2.2。**DB 是 Single Source of Truth**，兩節皆需用唯讀 DB 查詢工具實查，不可憑規格書文字推斷。

## 2.1 DB 結構逐欄比對

用唯讀 DB 查詢工具查詢每個涉及的資料表（欄位、關聯、索引）：

| 檢查項目 | 等級 |
|---------|------|
| 欄位名稱/型態/長度與 DB 一致 | CRITICAL |
| NOT NULL 與必填標記一致 | CRITICAL |
| decimal 精度一致 | CRITICAL |
| 規格書未遺漏 DB 欄位 | CRITICAL |
| FRD §5.1 每個欄位「DB 欄位（資料表.欄位名）」欄已填入（非空） | CRITICAL |
| varchar 長度與驗證規則一致 | CRITICAL |
| 外鍵在 ER Diagram 有對應 | CRITICAL |
| 預設值一致 | WARNING |

## 2.2 實際資料真實性驗證

對已存在且有資料的表，**必須**用唯讀 DB 查詢工具查詢：

| 查詢項目 | 等級 |
|---------|------|
| 列舉欄位 DISTINCT 值涵蓋規格書定義 | CRITICAL |
| 編號格式與規格書一致 | CRITICAL |
| 計算公式抽樣比對 | CRITICAL |
| 外鍵無孤兒記錄 | CRITICAL |
| NULL 分布與必填標記一致 | WARNING |

詳細 SQL 模板 → [db-validation-queries.md](db-validation-queries.md)。
