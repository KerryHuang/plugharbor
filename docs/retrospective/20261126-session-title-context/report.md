# 流程回顧報告

結論：上一版沒有到期指標可判定（10 條未到期）。本次歸併出 2 個根因，P0 共 2 項，都已修正；新增待驗指標 2 條。

**日期**：2026-11-26
**回顧範圍**：feedback-review 轉入的 1 筆 friction，加上回饋歸檔中同類的「改名沒生效」4 筆，以及本機全部 Claude Code transcript 的建議標題套用紀錄
**使用的 Skills**：toolkit:feedback-review（轉入）、toolkit:retrospective
**Plugin 版本**：toolkit 0.41.0 → 0.42.0

## 上一版驗證（Step 0）

| 上次的觀察指標 | 判定 | 本次證據 |
|---|---|---|
| M-20261113-01～M-20261123-06（10 條 open） | 未到期 | 最早 2026-11-27 到期；各追加一筆 not-due |

## 根因歸併（Step 2）

| 根因 | 表徵 | 出現次數 |
|---|---|---|
| agent 沒有可靠的「目前標題」視圖，各來源（ai-title、custom-title、sessions 檔 name、Herdr terminal title／分頁名）意義不同，只能每次自己猜 | 使用者問「怎麼沒改名」時 agent 重查或誤判；本次拿 derived 名稱當證據 | 5（見 evidence.md） |
| hook 在 prompt 送出當下執行，排隊送出的 prompt 讀不到之後才寫出的建議行；下一輪的掃描又停在那則 prompt，建議永遠不會套用 | 建議標題漏套用 | 排隊案例 4/4 |

使用者層的「先查本機」條文早就有了但沒有被遵守，所以這條根因要靠機制解決，不再加文字。

## 改進摘要

| 類別 | P0 | P1 | P2 | P3 | 合計 |
|---|---|---|---|---|---|
| 流程（hook） | 2 | | | | 2 |

## 詳細發現

### P0 — 立即修復

1. **標題問題沒有實查來源**
   - 證據：佇列 20261126121405-475036，另有 4 筆同類歸檔。
   - 修復：`auto-session-title.py` 在使用者訊息提到「標題／改名／rename」時，以 additionalContext 注入各來源：
     - 內建 ai-title 與 custom-title；transcript 沒有紀錄就照實寫「沒有紀錄」。
     - 本次正在套用的建議標題。
     - sessions 檔的 name，並標明 derived 名稱不是標題。
     - 在 Herdr 內時，加上 `hc get` 的 terminal title 與分頁名。
   - 動作：增。刪改都不夠，原因是條文已證明無效。

2. **排隊送出的 prompt 漏套用建議標題**
   - 證據：2b9f1c22 第 1572～1606 行，另有其他 3 例。
   - 修復：
     - `sentAtMs` 早於建議行的 prompt 不算回合邊界，下一次送出時補套用。
     - `promptSource: system`（通知、peer 訊息）不算回合邊界。
   - 重播 2381 個 prompt 時點，沒有發現誤套用舊建議。
   - 動作：改寫既有掃描邏輯。

## 轉交（非 plugin 歸屬）

無。使用者層的「先查本機」條文維持原樣，等 M-20261126-01 判定後再決定能不能刪。
