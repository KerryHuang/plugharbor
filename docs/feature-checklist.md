# 功能清單

## workspace：unattended（自動駕駛）

- [ ] 💡 已合併的主控裁決事後被使用者推翻時的重做方式（當插入單元馬上做，或寫回 roadmap 排隊）；等事故再補
- [ ] 💡 暫停後逐題問完待決，是否自動恢復自動駕駛（目前只認「繼續自動駕駛」）；等事故再補

## 借鏡 agentrun（Parcha-ai/agentrun，2026-11-13 評估）

- [ ] 💡 auto-memory 寫入前程式檢查：秘密樣式、隱藏字元、與既有記憶本文完全重複、索引行數上限、從網頁／貼上內容學來的規則不收；等事故再做
- [ ] 💡 常改的 skill（unattended、agent-dispatch）附 eval 案例，改動後跑一次量效果（可接 `claude plugin eval`；範本參考 dotnet/skills 的 `tests/<plugin>/<skill>/eval.yaml`＋評分腳本、有無 skill 對照、觸發率）；等事故再做
- [ ] 💡 agent-dispatch `bg.mjs wait` 為「待決」回專用 exit code（agentrun 用 8），呼叫端不必讀結果檔第一行；現行 herdr 事故已修，等事故再做

## 借鏡 dotnet/skills（2026-11-13 評估）

- [ ] 💡 .NET 工具鏈（MSBuild、測試、診斷、升級、EF 查詢最佳化）不在 plugharbor 自寫，需要時在專案層裝 dotnet/skills 對應 plugin；backend／database 只管架構與慣例

## workspace：project-setup（專案 AI 設定補裝）

- [ ] 🚧 只從 Claude Code 叫用，替四個 CLI 在專案層補裝：plugharbor → 網路純 skill → 自寫 AGENTS.md＋缺口 skill；設計見 `docs/superpowers/specs/2026-11-13-project-setup-design.md`
