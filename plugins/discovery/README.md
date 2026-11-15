# discovery

需求與會議：會議記錄、訪談準備、既有系統勘察、HTML 原型。
自 `lifecycle` 3.0.0 拆出（1.0.0），命名空間一律 `discovery:`。

## 定位

`[workflow]` 專案層 plugin，用 `setup/install-project.sh <專案根> discovery` 依專案安裝；可單獨使用，不需要 lifecycle。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
cd <專案> && claude plugin install discovery@plugharbor --scope local
```

## 設定

專案根 `.plugharbor/lifecycle.yml`，鍵與預設值見 `references/config.md`。

## 可選依賴

`lifecycle`（`spec` 等下游 skill）、`tickets`、`superpowers`、`browser-docs`、`toolkit`（錄音轉逐字稿）都是可選，沒裝時照 `references/shared-preludes.md`「可選依賴」降級。

## Skills（4）

| Skill | 用途 |
|-------|------|
| `meeting-minutes` | 記錄客戶／內部／研討會會議：即時記錄、會後整理，或把錄音轉逐字稿後整理成結構化會議記錄，可選第二意見審閱 |
| `interview-prep` | 正式訪談前後準備：把多場會議／訪談素材彙整成已知／未知盤點，或為受訪者產出訪談大綱 |
| `survey-existing-system` | 勘察現役系統某段行為的現況，產出 SA 現況分析文件 |
| `prototype-html` | 產出單一檔案、可點切換多畫面的 HTML 原型，供 PO 或客戶確認畫面 |

## Agents（4）

| Agent | 用途 |
|-------|------|
| `discovery-scout` | 證據蒐集：codebase／DB／文件勘察結果，只列證據不解讀（lifecycle `scout` 的副本） |
| `discovery-domain-advisor` | 業務領域解讀：對蒐集到的證據做領域判讀（lifecycle `domain-advisor` 的副本） |
| `discovery-report-writer` | 報表撰寫：吃備妥的資料集、範本與輸出路徑，產一份檔案（tickets `report-writer` 的副本，供 meeting-minutes 派發） |
| `discovery-silent-failure-hunter` | 靜默失敗獵手：審查「錯誤被吞掉、資料悄悄流失」的模式（tickets `silent-failure-hunter` 的副本） |
