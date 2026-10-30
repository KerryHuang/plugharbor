---
name: auditing-kid-ui
description: 依兒童介面規範的檢查清單，唯讀審查 app 既有的畫面，回報不符合的地方、嚴重度與依據。使用者要求審查畫面、檢查同系列 app 一致性時使用。
context: fork
agent: Explore
model: sonnet
effort: medium
disable-model-invocation: true
argument-hint: "[要審的畫面或檔案；空白＝全部]"
---

# 審查兒童介面

唯讀：不改檔、不 commit。範圍：$ARGUMENTS（空白就審全部畫面）。

## 步驟

```
審查進度：
- [ ] 1. 讀 checklist.md
- [ ] 2. 讀 ../designing-kid-ui/components.md（要一致的元件）；專案若有 .claude/skills/designing-kid-ui/this-app.md 也讀（元件在哪個檔案）
- [ ] 3. 照範圍列出要看的檔案（UI 程式碼、場景或畫面）
- [ ] 4. 每一條照「怎麼查」做；需要開瀏覽器的條目標「待實測」，不要猜
- [ ] 5. 回報
```

檔案位置：`${CLAUDE_SKILL_DIR}/checklist.md`、`${CLAUDE_SKILL_DIR}/../designing-kid-ui/components.md`。

## 回報格式

只報有證據的，不湊數。每項一列：

| 條目 | 嚴重度 | 依據 | 對孩子或家長的影響 | 工作量 |
|---|---|---|---|---|

- 嚴重度：該修（孩子會吃虧或卡住）／建議（體驗不好）／可加。
- 依據：`檔案:行號`。
- 工作量：小（30 分內）／中（半天內）／大。

最後列「待實測」的條目，和全部通過的條目編號。
