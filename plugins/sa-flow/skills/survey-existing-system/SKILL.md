---
name: survey-existing-system
description: 勘察現役（in-production）系統某段行為的現況，產出系統分析師（SA）現況分析文件。當 SA 需要獨立釐清某個現有 app／服務目前怎麼運作時使用。不適用於新功能需求（用 sa-flow:explore），也不適用於 FoxPro／舊系統遷移（用 sa-flow:foxpro-analyzer 或 reverse-engineer）。觸發：「勘察現有系統」「現況分析」「看懂這個 app 的現況」「survey existing system」。
argument-hint: "[app 路徑或行為範圍]"
---

# 勘察現有系統

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

SA 薄編排：用既有 agent 蒐集唯讀證據，再彙整成**現況分析文件**。
委派調查、自己負責彙整與定稿寫檔。

## 先確認範圍

蒐集前先與使用者確認：
1. **目標**——哪個 app／服務（monorepo 或 submodule 容器下的哪個子目錄）、要勘察哪段行為／範圍。
2. **產出**——預設 `{docs-root}`（依專案 CLAUDE.md 的 `sdlc-docs-path`，未設定為 `docs/`），
   落點與命名依該專案的文件慣例；判不出落點就問，不自建第一階目錄。
3. **來源判斷**——若對象是待汰換的 FoxPro／舊系統，停止並改用
   `sa-flow:foxpro-analyzer`；本 skill 只處理**現役 in-production** 系統。

## 蒐集證據（唯讀、委派）

用 Agent 工具派發既有 agent，不要自己重做它們的工作：
- **`sa-flow:scout`**——codebase／DB／文件勘察；只回證據，不做解讀。涉及 DB 資料表時（結構、抽樣、狀態碼語意），
  在派工裡寫明要查的表；scout 用專案提供的唯讀 DB 工具，沒有就只看 migration／entity 定義。
- **`sa-flow:silent-failure-hunter`**——勘察寫入鏈、或現況是「資料少了／欄位空了但沒錯誤」時。
- **`sa-flow:domain-advisor`**——選用，對蒐集到的證據做業務領域解讀；有 domain 邊界時依
  `${CLAUDE_PLUGIN_ROOT}/references/analysis-rigor.md` 是必經閘。

各自獨立的蒐集可並行。需要精確 `file:line` 溯源時直接讀關鍵原始碼。

## 彙整分析文件

產出現況文件，涵蓋：
- 勘察的範圍與進入點
- 工作流／資訊流／資料流
- 關鍵業務規則，每條溯源到 `file:line`
- 整合邊界（對外 API、與其他服務共用的 schema、身分驗證、訊息佇列…）
- 待釐清問題／風險

## 寫檔與審閱

- **定稿文件在主執行緒寫，絕不透過 subagent**（subagent 在此無法可靠寫檔）。
- **審閱檢查點**：先呈現草稿、取得 SA 確認再定稿，不自動 commit。
- 確認後才依專案 CLAUDE.md 的 git 規則 commit；文件 repo 是 submodule 時，先 commit 子模組，再更新主 pointer。
- 完成後依動線用 AskUserQuestion 建議下一步：要對現役功能做 CR 或加新功能 → `sa-flow:explore`；為有票的 bug 而勘察 → `sa-flow:linear-triage {票號}`；已上線但沒有規格、要逆向補 → `sa-flow:requirement`（現況文件是這三條路的共同輸入）；使用者同意才接著跑，不自動執行。
