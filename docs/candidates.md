# 候補改動

評估過、但依「改動要有起因」先延後的規則或機制。出現觸發條件寫的事故時，再照「做法」提案；CHANGELOG 的起因寫那次事故。

## C1 收工驗收提醒（close guard）

- **來源**：wayne930242/anchorloop 3.0.0 的 `pi/close-guard.ts`（2026-11-24 版），3.0 把 loop book、階段機制全拆掉，只留這一支，理由是每輪的額外成本（turn tax）。
- **做什麼**：一輪結束時讀對話紀錄；最後一次 `write`／`edit` 之後，宣告的驗收指令沒有一次通過的執行，就補一行提醒。不擋、不另起一輪、不寫檔，同一次改動只提醒一次。
- **觸發條件**：出現一次 agent 改完檔、沒跑宣告的驗收就回報完成的事故（回饋佇列或使用者當場糾正）。
- **做法**：
  - 規則：setup 的 home 目錄下 `shared/engineering.md`「目標驅動」的驗收方式改成可偵測的固定行（如 ``驗收：`<指令>` ``），要拿同等字數交換。
  - pi：toolkit 加 extension，掛 `agent_before_settle`（同 `plugins/toolkit/pi/guard.ts` 的形式）。
  - Claude Code：不用 Stop hook 擋（會逼多跑一輪）；改在 UserPromptSubmit 注入提醒，或 Stop 時只用 `systemMessage` 顯示給使用者。
- **評估日**：2026-11-25；當時佇列＋歸檔 91 筆，相關僅 1 筆（2026-11-11 本地 e2e，已另行處理）。

## C2 放寬檢查不算修好

- **來源**：anchorloop coding skill（2026-11-04 後版本；3.0 併入 loop card 第 1 條）。
- **內容**：提高門檻、加 allowlist／ignore、skip 或 xfail 測試、把檢查改成不擋，都是改關卡不是修好；回報要逐項點名理由，等使用者接受。
- **觸發條件**：出現 agent 靠放寬檢查過關的事故。
- **做法**：加進 setup 的 home 目錄下 `shared/engineering.md`「目標驅動」，字數拿同等內容交換。
- **評估日**：2026-11-09。
