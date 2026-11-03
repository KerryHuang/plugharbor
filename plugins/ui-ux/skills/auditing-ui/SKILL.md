---
name: auditing-ui
description: 依通用檢查清單（與受眾附錄的加項）唯讀審查 app 既有的畫面，回報不符合的地方、嚴重度與依據。Use when 使用者要求審查畫面、檢查 UI 一致性、"審查 UI"、"audit UI"、"review screens"、"畫面檢查"。
context: fork
agent: Explore
model: sonnet
effort: medium
disable-model-invocation: true
argument-hint: "[要審的畫面或檔案；空白＝全部]"
---

# 審查介面

唯讀：不改檔、不 commit。範圍：$ARGUMENTS（空白就審全部畫面）。

## 0. 偵測受眾

先判斷受眾，並在回報第一行寫「受眾：<名稱>」。

| 偵測到 | 附錄 |
|---|---|
| 使用者明確說兒童，或專案 README／設定標明兒童受眾 | `${CLAUDE_PLUGIN_ROOT}/references/audience-kids.md`（讀其中「審查清單」與「要一致的元件」） |

一般專案不套兒童規範。沒有對應附錄：只用通用清單，加上專案既有畫面的寫法比對；回報寫「受眾：一般」。

## 步驟

```
審查進度：
- [ ] 1. 讀 references/checklist.md；有受眾附錄就一併讀其審查清單
- [ ] 2. 讀專案自己的 UI 規則與元件說明（.claude/rules/、.claude/skills/designing-ui/this-app.md、設計系統文件）
- [ ] 3. 照範圍列出要看的檔案（UI 程式碼、場景或畫面）
- [ ] 4. 每一條照「怎麼查」做；需要開瀏覽器的條目標「待實測」，不要猜
- [ ] 5. 回報
```

檢查清單位置：`${CLAUDE_SKILL_DIR}/references/checklist.md`。

## 回報格式

只報有證據的，不湊數。每項一列：

| 條目 | 嚴重度 | 依據 | 對使用者的影響 | 工作量 |
|---|---|---|---|---|

- 嚴重度：該修（使用者會吃虧或卡住）／建議（體驗不好）／可加。
- 依據：`檔案:行號`。
- 工作量：小（30 分內）／中（半天內）／大。

最後列「待實測」的條目，和全部通過的條目編號。
