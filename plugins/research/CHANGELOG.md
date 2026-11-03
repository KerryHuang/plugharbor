# Changelog

格式：每次改動 `skills/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.2.1] - 2026-11-03

- fix(ai-radar): 深讀 subagent 不再自己 rm -rf clone 目錄（會被使用者確認規則擋下而卡住），改回報「待清」路徑，由主執行緒一條指令刪完。

## [0.2.0] - 2026-11-03

- feat(ai-radar): 區塊 4 每週深讀前 5 個 plugin 候選並產評估卡（裝用／借鑒／不理），新增 --plugin <網址> 單獨評估；結論接進採納待辦。

## [0.1.0] - 2026-10-30

- feat: 初版——`graphify`（資料夾建知識圖譜）、`ai-radar`（每週 AI 情報雷達與採納待辦對帳）。
- chore: `adoption-backlog.md` 只留規則與格式，個人待辦不隨 plugin 發佈；graphify 去除本機安裝說明。
