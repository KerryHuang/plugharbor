# ai-radar 預設來源清單

可自由增刪。掃描時以這些為起點，並允許從搜尋結果延伸到其他高信譽來源。

## 區塊 1 — 大廠更新與教學

| 來源 | 說明 | 可信度 |
|------|------|--------|
| `code.claude.com/docs/llms.txt` + 規範頁 | Claude Code 官方規格（skill/rule/hook/settings）；用 WebFetch 讀 `https://code.claude.com/docs/llms.txt` | 官方 |
| Anthropic News / Engineering blog | Claude 模型與工具公告 | 官方 |
| OpenAI Blog / Release notes | GPT / 工具更新 | 官方 |
| Google AI / Gemini blog | Gemini 更新 | 官方 |
| Cursor changelog / blog | Cursor IDE 更新與用法 | 官方 |
| GitHub Copilot changelog | Copilot 更新 | 官方 |

## 區塊 2 — 最佳實踐（論壇 / 社群）

| 來源 | 說明 |
|------|------|
| Reddit r/ClaudeAI、r/cursor、r/LocalLLaMA、r/ChatGPTCoding | Claude Code / vibe coding 實作討論 |
| Hacker News（news.ycombinator.com） | 軟體工程 + AI 高品質討論 |
| dev.to / Medium（AI、agentic coding 標籤） | 實作教學與心得 |
| X / Twitter（透過搜尋摘要） | 即時動態、作者第一手分享 |
| GitHub Trending / awesome-* 清單 | 熱門工具與範式 |

## 區塊 4 — Marketplace / Plugin 排行

| 來源 | 說明 |
|------|------|
| GitHub topic：`claude-code`、`claude-code-plugin`、`awesome-claude-code` | plugin / skill 集散與排行 |
| Claude Code plugin marketplaces（官方與社群） | 可裝的 marketplace 列表 |
| npm / VS Code Marketplace（AI、agent 類） | 下載量 / 安裝量排行 |
| Reddit / HN「推薦 plugin」討論串 | 真實使用者推薦 |

## 篩選原則

- 優先**近一週**、**高互動**（星數 / 讚 / 留言）、**有具體做法或規範**的內容。
- 官方來源與社群來源分開標記，避免把社群臆測當官方規範。
