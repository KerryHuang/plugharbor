---
name: spec-check
description: "實作前檢查設計文件：對照真實程式碼與 DB 查一份 <spec.dir> 的設計文件能不能直接開發、驗收案例可不可測；--sample 對照實際程式碼驗設計文件覆蓋度。Use when 驗證規格、規格檢查、spec-check、dev readiness、驗證規格 vs 程式行為、規格覆蓋度。"
triggers: ["驗證規格", "規格檢查", "spec-check", "dev readiness"]
argument-hint: "[--sample] [規格路徑] [原始碼範圍]"
---

# 規格檢查

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔實體路徑：symlink 先 `realpath`，同目錄有 `.plugharbor-root` 就以其內容為 plugin 根；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

實作前回答一個問題：**開發者能不能只看這份設計文件就寫 code，而且寫出來在現有架構與真實資料上跑得通？**

| 模式 | 旗標 | 驗什麼 | 做法 |
|------|------|-------|------|
| 實作前檢查 | （預設） | 下方檢查表：待澄清清零、驗收案例可測、引用的既有元件真的存在 | 本檔 |
| sample | `--sample` | **設計文件 vs 程式**：分組取樣原始碼，找設計文件漏掉或寫錯的行為 | `references/modes/sample.md` |

## Step 0：找設計文件

設計文件是 `<spec.dir>/<feature>.md` 或 `<spec.dir>/*<feature>*-design.md`（`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir`，預設 `docs/superpowers/specs`；檔名可能有日期前綴，給短名找不到時用 `*<feature>*` 找）。舊範本的規格（§ 編號章節、表頭表格）照舊檢查，不強制轉檔。
未給路徑時，從對話推斷最近處理的文件並告知「偵測到：<path>」；推不出才提示用法並終止。

## sample 模式（`--sample`）

`$ARGUMENTS → --sample <規格路徑> [原始碼範圍] [--full]`。主 session 不讀原始碼，取樣派 `lifecycle:spec-sampler` 分組平行執行，詳見 `references/modes/sample.md`。

## 實作前檢查

主 session 依序檢查，每項記 CRITICAL／BLOCKER：

| # | 檢查 | 等級 |
|---|------|------|
| 1 | 全文無殘留 `[NEEDS CLARIFICATION` | BLOCKER |
| 2 | 驗收一節可測：先 `python3 ${CLAUDE_PLUGIN_ROOT}/skills/qa-verify/scripts/spec_to_cases.py <文件> .tmp/qa/<feature>.md`（exit 4＝缺欄，stderr 逐條列缺什麼；`.tmp/` 未被忽略的提醒見 `qa-verify/references/spec-to-acceptance.md`），再 `python3 ${CLAUDE_PLUGIN_ROOT}/skills/qa-verify/scripts/validate.py acceptance .tmp/qa/<feature>.md` 要 `OK`；預期可觀察（訊息逐字）；關鍵規則有正例與反例且代入具體數字 | CRITICAL |
| 3 | 既有元件查證：全文引用的既有元件、端點、資料表實際存在（新格式主要在「決定」「留給 builder」，舊範本在 §3；Grep／唯讀 DB 查詢；範圍大時派 `lifecycle:scout`） | CRITICAL |

沒裝 `superpowers`（建造者檢查由 `superpowers:brainstorming` 負責）時多跑一項「建造者讀法」：以 builder 身分讀一遍，列出「會改變做出什麼」的未答問題，有就記 WARNING。

文件開頭行有「來源：舊系統移植」（舊範本為表頭「來源｜舊系統移植」，兩種都認）時，缺口照 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md` 的 spec-check 段判定（對齊、P-FIX、不處理）。

結論：0 CRITICAL／BLOCKER 且 0 WARNING → ✅ 可直接開發；只有 WARNING → ⚠️ 需修正後開發；其餘 → ❌ 不可開發。
✅ 時在開頭行（舊範本在 `# ` 標題行）下一行寫 `> 實作前檢查：✅ YYYY-MM-DD（內容 <8 碼>）`（已有就更新）；8 碼＝`grep -v '^> 實作前檢查：' <文件> | shasum | cut -c1-8`。這是 `lifecycle:implement` 判斷不重跑的依據：之後正文有改，雜湊就對不上、會重跑；⚠️／❌ 不寫。
結果以文字回報，不另落報告檔；修正後重跑同一張表；同一份文件連續第三輪仍不過就停下回報使用者。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 唯讀 DB 查詢工具不可用 | 「既有元件查證」改以程式碼與既有規格查證並註明「未查證（無 DB 工具）」，不擋 |
| 帶舊旗標 `--readiness`、`--cross`、`--recheck`、`--quick`，或給的是舊的四份文件規格 | 回一句「verify／readiness 模式已在 lifecycle 3.0.0 移除，照實作前檢查表跑」，照預設模式繼續 <!-- allow-legacy --> |
