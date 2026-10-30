# blog

部落格寫作的三段流程。plugin 本身不內建任何站台資訊：站台名稱、文章目錄、frontmatter、作者標示、部署方式都讀**專案自己的**
`.claude/rules/posts.md`（或 `AGENTS.md`），沒有就問使用者。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install blog@plugharbor
```

## Skills

| Skill | 用途 |
|-------|------|
| `blog-capture` | 在做事的 session 趁熱把專案或成果整理成素材包，存到 Google Drive 的 `blog-inbox/`（需 Google Drive connector；沒有就把素材包貼在回覆裡）。公司專案會先去識別化。 |
| `write-post` | 定題（一次問一題）、蒐集素材、寫白話初稿、檢查、交稿。 |
| `publish-check` | 使用者說發布、上線文章時：commit 乾淨、個資掃描、build、同步遠端、上線後驗證。 |
