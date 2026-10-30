> 本檔是 `templates/cr-frd.md` / `cr-bfs.md` / `cr-ffs.md` 的範例集，**按需讀取**：撰寫該章且不確定寫法時才讀。
> JSON 範例僅示範巢狀／批量結構寫法；一般扁平欄位一律用模板內的欄位表（見 `references/doc-boundaries.md`「BFS §6 表達法」）。

# CR-BFS §4 API 異動規格 — 完整範例

## §4.1 新增端點 完整範例

**Request：**

```json
{
  "{propertyName}": "{value}",
  "{anotherId}": "00000000-0000-0000-0000-000000000000"
}
```

**Response：**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "{field}": "{value}"
}
```

## §4.2 修改端點 完整範例

**完整 Request（含原有欄位）：**

```json
{
  "{existingField}": "{value}",
  "{newField}": "{value}"
}
```

**完整 Response（含原有欄位）：**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "{existingField}": "{value}",
  "{newField}": "{value}"
}
```
