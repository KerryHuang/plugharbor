# 流程回顧報告

上一版 7 條待驗指標都未到期；本次 2 個根因（1 個流程缺陷、1 個偶發）、P0 1 項、新增待驗指標 2 條。

**日期**：2026-11-17
**回顧範圍**：feedback-review 轉交 2 群（f6146a、74c3fb）＋本機 transcript 中 11-01～11-17 的 SendMessage 失敗 9 起、10-21～22 批次 69 次
**使用的 Skills**：toolkit:feedback-review、toolkit:retrospective
**Plugin 版本**：toolkit 0.25.0

## 上一版驗證（Step 0）

7 條 open 指標（M-20261109-02～05、M-20261113-01／02）均未到期（11-23、11-27）；M-20261113-01 期間無漂英文，17b9d7 屬誤擋已由 2e47aaf 修。

## 根因歸併（Step 2）

| 根因 | 表徵 | 出現次數 |
|---|---|---|
| 回報位址是派工當下的名稱快照，收件方之後改名（建議標題 hook、使用者 /rename、重開）就失效；worker 照指示「送不到不重試」，沒有用不變的 ref 找回收件方 | 派工後改名（事件 1、6、8；10-21 批次 61 次）、改名後沿用舊快照（事件 9）、重開換 ref（事件 7） | 5 起事件＋批次 61 次 |
| 手動起的拋棄式 `claude -p` 繼承 `AGENT_DISPATCH_*`（`ask.mjs` 的 scrubEnv 已濾 RESULT，手動路徑只有 SKILL.md:104 的文字提醒，沒列這組） | f6146a | 1 |

附帶：送達比對看名稱不看 ref；裸 ref／只有括號 ref 0／3 成功。細節見 `evidence.md`。

## 改進摘要

| 類別 | P0 | P1 | P2 | P3 | 合計 |
|---|---|---|---|---|---|
| 流程（hook） | 1 | | | | 1 |
| Skill 內容 | | | 1 | | 1 |

## 詳細發現

### P0 — 立即修復

**送不到時用 ref 找回收件方重送**
- 問題：SKILL.md:107 的「先用 ListAgents 取位址」擋不住派工後才改名；11-08 加的 rename 例外（文字）後仍復發。
- 修復方案：新增 toolkit hook（PostToolUseFailure，matcher SendMessage）：錯誤是 `No agent named '<X> [ref]'` 時注入「收件方可能改名：用 ListAgents 找帶同一 ref 的那列，用該列目前名稱加 ref 重送一次；仍失敗才寫 undelivered」。SKILL.md:107 的「送不到…不重試」改寫成同義一句，不新增句子。
- 動作：增 hook＋改一句。只改文字不夠：prompt 由主控臨時寫，hook 對所有發送方生效。
- ⚠️ 未驗證：PostToolUseFailure 對 SendMessage 的錯誤會不會觸發、能不能拿到錯誤文字，要先實測。

### P2 — 排入待辦

**SKILL.md:104 濾除清單補 `AGENT_DISPATCH_*`**：只發生 1 次，列入觀察；等下次改到這一行時順手補。

## 轉交（非 plugin 歸屬）

| 根因 | 歸屬層 | 去向 | 狀態 |
|---|---|---|---|
| `communication.md`「已派出 worker 未回報時不建議 rename」：P0 hook 生效後，這條例外可以合併或刪除 | 使用者層 | 待使用者處理（user 帳本 2026-11-08 條目觀察中） | 僅列報告 |

## 值得固化的好模式

失敗後 ListAgents 現查、改送「目前名稱 [ref]」，每次都成功。

## 本次的待驗指標

| 編號 | 指標 | 判準 | 到期條件 | 不如預期時 |
|---|---|---|---|---|
| M-20261117-01 | 改名導致回報送不到 | hook 發版後，transcript 中 `No agent named '<名稱> [ref]'` 失敗之後的 2 次呼叫內，改用同 ref 的新名稱重送成功的比例 ≥ 80%，且沒有使用者再糾正「位址錯了／改名」 | date: 2026-12-08 | 查 hook 有沒有觸發；不觸發就改在 mux.py spawn 產生的 prompt 裡帶固定的重送步驟 |
| M-20261117-02 | 拋棄式 CLI 繼承派工變數 | 佇列出現 dispatch-stop-guard 誤逼子程序寫結果檔的 friction 筆數＝0 | date: 2026-12-08 | 補 SKILL.md:104 清單，或讓 dispatch-stop-guard 比對 pane id |

## 版本建議
- 當前版本：toolkit 0.25.0
- 建議版本：0.26.0（新增 hook＝minor）
- 變更摘要：SendMessage 收件方改名時，自動提示用 ref 找回收件方重送
