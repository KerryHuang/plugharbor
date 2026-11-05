# Changelog

格式：每次改動 `skills/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.4.0] - 2026-11-05

- feat(plugin-harvest): 候選來源加入 skills.sh 搜尋 API（查不到就略過），搜尋階段不執行 `npx skills`；排序的相關度也納入觸發這次搜尋的能力缺口。

## [0.3.0] - 2026-11-05

- feat(plugin-harvest): 新 skill——領域搜尋熱門 plugin → 深讀對照基準 → 逐條核准的具體提案 → 只套用核准的；採納時寫 `harvest-lock.json`（來源、commit、授權檔 hash），`--check-lock` 檢查上游更新與授權變動；`--lean` 給 ai-radar 週報用。
- feat(plugin-harvest): `skills/plugin-harvest/scripts/harvest.py`（網址拆解、鎖定檔寫入與檢查，純標準庫＋git）。
- refactor(ai-radar): 只留情報（大廠規範、工程實踐、設定最佳化、知識庫稽核）；區塊 4 改叫用 `plugin-harvest --lean`，`--plugin <網址>` 保留為轉交入口。
- fix(plugin-harvest): 實測回饋——深讀必讀加 `commands/` 與非 plugin 形態的設定／主程式、prompt 帶基準 repo 路徑、README 宣稱不算證據且主執行緒抽查；monorepo 子目錄不計整個 repo 星數；排行表與領域 slug 有落點；清理改為獨立步驟。
- fix(plugin-harvest): 審查修正——網址去 query／fragment、支援 `/blob/`、`www.` 正規化；annotated tag 取 peeled commit、釘 commit 的 ref 報 PINNED；stdout UTF-8、git 不等帳密；深讀後檢查基準 repo 未被改；本機路徑與直接裝用不寫鎖定檔；ai-radar 改讀檔照做精簡模式（Skill 工具叫不動 disable-model-invocation 的 skill）。
- refactor: `plugin-eval.md`、`adoption-backlog.md` 搬到 plugin 根 `references/`，兩個 skill 共用；網址一律經 `harvest.py parse-url` 拆解。

## [0.2.1] - 2026-11-03

- fix(ai-radar): 深讀 subagent 不再自己 rm -rf clone 目錄（會被使用者確認規則擋下而卡住），改回報「待清」路徑，由主執行緒一條指令刪完。

## [0.2.0] - 2026-11-03

- feat(ai-radar): 區塊 4 每週深讀前 5 個 plugin 候選並產評估卡（裝用／借鑒／不理），新增 --plugin <網址> 單獨評估；結論接進採納待辦。

## [0.1.0] - 2026-10-30

- feat: 初版——`graphify`（資料夾建知識圖譜）、`ai-radar`（每週 AI 情報雷達與採納待辦對帳）。
- chore: `adoption-backlog.md` 只留規則與格式，個人待辦不隨 plugin 發佈；graphify 去除本機安裝說明。
