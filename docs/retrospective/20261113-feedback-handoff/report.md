# 2026-11-13 回顧：feedback-review 轉入的兩群 toolkit 證據

結論：兩群都已有對應修正，本次不再改 plugin。上一版 5 條指標皆未到期；本次 2 個根因、P0 0 項（已修）、新增待驗指標 2 條。

## Step 0：上一版驗證

M-20261109-01～05 的 due 都是 2026-11-23，記 not-due。

## 證據與根因

| 群 | 佇列 id | 根因 | 現況 |
|---|---|---|---|
| 1 語言漂移 | 20261112190946-01f7a1（agent friction） | 壓縮後只注入一次提醒（0.19.0 compact-context.py），撐不過長自主作業；壓縮摘要與續接提示為英文，工具呼叫間的短句漂成英文 | 0.20.0（82afe42）已加 Stop hook `reply-language-guard.py`，逐段檢查本回合文字、英文段擋下要求重述；本機 cache 0.21.0 已含 |
| 2 信任檢查誤導 | 20261113110944-cca167（agent friction） | `herdr-long-task.md` 的檢查腳本只比對 cwd 本身是否在 `~/.claude.json`，不看 `hasTrustDialogAccepted`、不沿上層繼承 | plugharbor 工作目錄已有 0.21.1 修正（腳本沿上層找 `hasTrustDialogAccepted: true`，SKILL.md 同步），**尚未 commit** |

群 1 是「修過又復發」（CLAUDE.md 文字 → 0.19.0 一次性注入 → 0.20.0 Stop hook），改法已從文字升級到逐回合機械檢查，方向正確，先觀察不再加 PreToolUse hook，避免過度反應。

跨 session 蒐證（Step 1-B）未派：兩群都已有修正，蒐證只會重複既有結論。無量化數據。

## 轉交

- 群 1 對應 user 層帳本 `~/.claude/feedback-loop/ledger.md`「2026-11-12｜context 壓縮後注入語言／格式提醒」（❌），已補登 0.20.0 為取代條目。
- 群 2 的 0.21.1 修正由另一個 session 進行中，待它 commit／發版。

## 本次的待驗指標

- M-20261113-01：2026-11-13 之後，「說中文」糾正或回覆漂成英文的 friction＝0（due 2026-11-27）
- M-20261113-02：0.21.1 發版後，信任檢查誤判或 worker 卡信任對話框＝0（due 2026-11-27）
