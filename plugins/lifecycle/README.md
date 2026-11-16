# lifecycle

開發主線：規格 → 規格檢查 → 實作入口 → QA 實機驗收 → 發版。工程核心（brainstorming、計畫、實作、審查）交給 superpowers，lifecycle 管做之前與做之後。
票務、需求與會議、交付文件在 4.0.0 拆成 `tickets`、`discovery`、`delivery` 三個獨立 plugin（見「搬到哪」）。

## 定位

`[workflow]` 專案層 plugin，用 `setup/install-project.sh <專案根> lifecycle` 依專案安裝。
技術層面（後端、前端、資料庫、桌面）交給職責 plugin；git 與工作區工具在 `workspace`。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
cd <專案> && claude plugin install lifecycle@plugharbor --scope local
```

## 設定

專案根 `.plugharbor/lifecycle.yml`，鍵與預設值見 `references/config.md`。重點：

- `spec.dir`：規格目錄，預設 `docs/superpowers/specs`。
- `ticket.tool`：`linear`、`github`、`jira`；票務動作經 `tickets:ticket-ops`（沒裝 `tickets` 時只更新清單，見可選依賴）。

舊專案只有 `.plugharbor/delivery-flow.yml` 時，讀設定的 skill 會停下提示改名為 `lifecycle.yml`（鍵不變）。

## 可選依賴

建議搭配 superpowers（`implement` 把規劃、執行、審查、收尾交給它）。`superpowers`、`tickets`（票務）、`discovery`（會議記錄）、`browser-docs`（畫面勘察、PDF 轉檔）、`toolkit`（herdr pane 派工）沒裝時照 `references/shared-preludes.md`「可選依賴」降級。

## Skills（5）

| Skill | 用途 |
|-------|------|
| `implement` | 照設計文件實作的入口：開分支、實作前檢查，再交給 superpowers 規劃與執行（沒裝走同格式退路），計畫審查後開工，最後一步對照驗收與回填 |
| `qa-verify` | Dev 完工後依驗收案例做實機 E2E 驗收 |
| `release` | 分關卡發版：release branch、品質閘、merge 回 main、反合 develop；含線上急修（hotfix） |
| `spec` | 寫功能規格：產一份 `<spec.dir>/<feature>.md`（`## 驗收` 為可直接驗收的案例）；`--change` 就地更新既有設計文件並記變更紀錄 |
| `spec-check` | 實作前檢查規格：待澄清清零、驗收案例可測、引用的元件與資料表真的存在；`--sample` 覆蓋度取樣 |

## Agents（10）

| Agent | 用途 |
|-------|------|
| `architect` | 架構顧問（不綁技術棧） |
| `developer` | 功能開發專家（不綁技術棧） |
| `domain-advisor` | 通用 Domain 知識顧問，協助 SA/PM 在需求分析與系統分析階段確保業務 Domain 正確性 |
| `qa-fixture` | QA 前置資料：判定環境可寫性，逐條解析前置條件並備妥資料；另可查核資料斷言 |
| `qa-planner` | QA 驗收計畫：讀驗收案例檔（或票面的重現步驟），開畫面對出案例欄位↔實機表頭，把案例轉成可執行步驟與預期觀察，產 plan.yml |
| `qa-runner-ui` | QA 實機執行：照 steps-only 計畫逐條操作，結構化記錄觀察並回寫成功步驟為快取；可依環境送出資料，唯讀環境只到送出前 |
| `reviewer` | 程式碼審查專家（不綁技術棧，後端與前端皆適用） |
| `scout` | 證據蒐集：codebase／DB／文件勘察結果，供 domain-advisor 與規格撰寫共用 |
| `spec-sampler` | 規格覆蓋度取樣 agent |
| `tester` | 測試工程專家（不綁技術棧，後端與前端皆適用） |

## 搬到哪

4.0.0 把與開發主線無關的 skill、agent 拆出去，叫用名改了：

| 舊（lifecycle 內） | 新 |
|----|----|
| `ticket-ops`、`ticket-create`、`ticket-reply`、`ticket-report`、`triage` | `tickets:` 同名 |
| `report-writer`、`silent-failure-hunter`（agent） | `tickets:` 同名 |
| `meeting-minutes`、`interview-prep`、`survey-existing-system`、`prototype-html` | `discovery:` 同名 |
| `operation-manual`、`demo-video` | `delivery:` 同名 |
| `manual-explorer`、`manual-reviewer`、`manual-writer`（agent） | `delivery:` 同名 |
| `plugin-healthcheck` | 本 repo 的 `.claude/skills/plugin-healthcheck`（`/plugin-healthcheck <plugin>`，只給維護者） |
| `scout`、`domain-advisor` | 留在 lifecycle；副本為 `tickets-scout`、`discovery-scout`、`discovery-domain-advisor`（tickets 沒有 domain-advisor 副本） |

安裝：`setup/install-project.sh <專案根> tickets`（或 `discovery`、`delivery`，可與 `lifecycle` 一起列）。

## 維護

改 skill 或 agent 前對照 `references/skill-design.md`（設計慣例）。
