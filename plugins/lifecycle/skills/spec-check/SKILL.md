---
name: spec-check
description: "實作前檢查規格：對照真實程式碼與 DB 查一份 <spec.dir>/<feature>.md 能不能直接開發、§2.3 驗收案例可不可測；--sample 對照實際程式碼驗規格覆蓋度。Use when 驗證規格、規格檢查、spec-check、dev readiness、驗證規格 vs 程式行為、規格覆蓋度。"
triggers: ["驗證規格", "規格檢查", "spec-check", "dev readiness"]
argument-hint: "[--sample] [規格路徑] [原始碼範圍]"
---

# 規格檢查

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔實體路徑：symlink 先 `realpath`，同目錄有 `.plugharbor-root` 就以其內容為 plugin 根；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

實作前回答一個問題：**開發者能不能只看這份規格就寫 code，而且寫出來在現有架構與真實資料上跑得通？**

| 模式 | 旗標 | 驗什麼 | 做法 |
|------|------|-------|------|
| 規格檢查 | （預設） | 下方檢查表：待澄清清零、驗收案例可測、決策完整、引用的既有元件真的存在 | 本檔 |
| sample | `--sample` | **規格 vs 程式**：分組取樣原始碼，找規格漏掉或寫錯的行為 | `references/modes/sample.md` |

## Step 0：找規格

規格是單一 `<spec.dir>/<feature>.md`（`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir`，預設 `docs/specs`）。
未給路徑時，從對話推斷最近處理的規格並告知「偵測到：<path>」；推不出才提示用法並終止。

## sample 模式（`--sample`）

`$ARGUMENTS → --sample <規格路徑> [原始碼範圍] [--full]`。主 session 不讀原始碼，取樣派 `lifecycle:spec-sampler` 分組平行執行，詳見 `references/modes/sample.md`。

## 規格檢查

主 session 依序檢查，每項記 CRITICAL／BLOCKER／WARNING：

| # | 檢查 | 等級 |
|---|------|------|
| 1 | 全文無殘留 `[NEEDS CLARIFICATION` | BLOCKER |
| 2 | §2.3 每條驗收案例符合 `${CLAUDE_PLUGIN_ROOT}/skills/qa-verify/references/acceptance-format.md`（降兩級標題、有步驟與預期、預期可觀察）；每條 US 都有案例，關鍵 BR 有正例與反例且代入具體數字 | CRITICAL |
| 3 | 決策表每列「否決的選項與原因」非空 | CRITICAL |
| 4 | §3 提到的既有元件、端點、資料表實際存在（Grep／唯讀 DB 查詢；範圍大時派 `lifecycle:scout`） | CRITICAL |
| 5 | §3.4 邊界涵蓋空值、極值、狀態、並發、權限（不適用要寫理由） | WARNING |
| 6 | 沒有寫死實作手段（框架、快取、鎖、佇列） | WARNING |
| 7 | 範圍寫了「不包含」；`[推論]` 都附依據 | WARNING |

規格表頭有「來源｜舊系統移植」時，缺口照 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md` 的 spec-check 段判定（對齊、P-FIX、不處理）。

結論：0 CRITICAL／BLOCKER 且 0 WARNING → ✅ 可直接開發；只有 WARNING → ⚠️ 需修正後開發；其餘 → ❌ 不可開發。
✅ 時在規格表頭寫一列 `| 規格檢查 | ✅ YYYY-MM-DD（版本 x.y.z） |`（已有就更新；版本取表頭「版本」），這是 `lifecycle:implement` 判斷不重跑的依據；⚠️／❌ 不寫。通過後再改任何內容（含非 CR 的小改）都要把表頭版本 +1，否則 implement 會當成沒改過。
結果以文字回報，不另落報告檔；修正後重跑同一張表；同一份規格連續第三輪仍不過就停下回報使用者。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 唯讀 DB 查詢工具不可用 | 第 4 項改以程式碼與既有規格查證並註明「未查證（無 DB 工具）」，不擋 |
| 帶舊旗標 `--readiness`、`--cross`、`--recheck`、`--quick`，或給的是舊的四份文件規格 | 回一句「verify／readiness 模式已在 lifecycle 3.0.0 移除，照規格檢查表跑」，照預設模式繼續 <!-- allow-legacy --> |
