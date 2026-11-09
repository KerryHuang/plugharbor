---
name: spec-check
description: "實作前檢查規格，三個模式：verify（預設）驗已寫內容的正確性、DB 實查與跨文件一致性；--readiness 對抗式獵邊界缺口並裁決回寫；--sample 對照實際程式碼驗規格覆蓋度。lean 單份規格走精簡檢查。Use when 驗證規格、規格檢查、spec-check、就緒度、dev readiness、驗證規格 vs 程式行為、規格覆蓋度。"
triggers: ["驗證規格", "規格檢查", "spec-check", "dev readiness"]
argument-hint: "[--readiness|--sample] [文件路徑或功能目錄] [--cross] [--recheck] [--quick|--full]"
---

# 規格檢查

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

`analysis/_context.yml` 記 `ffs: skipped`（無畫面功能，見 `${CLAUDE_PLUGIN_ROOT}/references/chain-profile.md`）時，FFS 是刻意不產，不列為缺漏、不要求補寫。

實作前回答一個問題：**開發者能不能只看這份規格就寫 code，而且寫出來在現有架構與真實資料上跑得通？**
三個模式各管一段，不重疊：

| 模式 | 旗標 | 驗什麼 | 做法 |
|------|------|-------|------|
| verify | （預設） | **已寫的**：正確性、DB 逐欄實查、資料流、跨文件追溯（`--cross`） | `references/modes/verify.md` |
| readiness | `--readiness` | **沒寫的**：空值／極值／狀態／並發／例外等邊界缺口，逐項裁決並回寫規格 | `references/modes/readiness.md` |
| sample | `--sample` | **規格 vs 程式**：分組取樣原始碼，找規格漏掉或寫錯的行為 | `references/modes/sample.md` |

各模式檔裡的「本 skill」指該模式；拿掉 `--readiness`／`--sample` 後的參數就是該檔的 `$ARGUMENTS`，檔內的參數表、Task 流程、交棒規則照做。

## Step 0：判斷規格規模

先看輸入是哪一種規格：

- 路徑是單一 `<spec.dir>/<feature>.md`（`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get spec.dir`，預設 `docs/specs`），或檔內沒有 SPEC-INDEX 且不是 FRD／SAD／BFS／FFS → **lean 規格**，走下方「lean 規格檢查」；`--sample` 仍照 sample 模式。
- 其餘（`*_需求文件.md`、`*_系統分析文件.md`、`*_後端功能規格書.md`、`*_前端功能規格書.md` 或功能目錄）→ 依旗標進對應模式。

未給路徑時，從對話推斷最近處理的規格並告知「偵測到：<path>」；推不出才提示用法並終止。

## verify 模式（預設）

verify 不能中途問使用者（模式一律由旗標決定），且要讀大量規格與 DB 結果。為保住主 session 的 context：

1. 派一個 `general-purpose` subagent，模型用 sonnet（照清單驗證，最機械），prompt 帶：plugin 根絕對路徑、`references/modes/verify.md` 的絕對路徑、原始參數（文件路徑、`--cross`／`--recheck`／`--quick`／`--full`）、「依該檔執行，報告落檔後只回報告路徑、結論等級與 CRITICAL／BLOCKER 清單」。
2. 子 agent 內再派平行維度 agent 時一律前景派工（同一則訊息多個呼叫，不背景）；環境若只能背景跑，就等完成通知再讀結果，不提早下結論。
3. 主 session 收回後依該檔「鏈末條件」與 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 決定下一步；修正後的第二輪帶 `--recheck`。

機械閘門可單獨跑：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/spec-check/scripts/check-decision-propagation.py <功能目錄>
```

## readiness 模式（`--readiness`）

在主 session 執行（需要逐項問使用者裁決）。BFS＋FFS 寫完、verify 之前跑；結論 ✅ 即交棒 verify。
裁決時套 `lifecycle:spec` 的決策分類：機械缺口（有唯一正解、慣例已定）自己補並記 `decisions.md`（`拍板`＝`SA`／`證據`），只把品味取捨丟給人。

## sample 模式（`--sample`）

`$ARGUMENTS → --sample <規格路徑> [原始碼範圍] [--full]`。主 session 不讀原始碼，取樣派 `lifecycle:spec-sampler` 分組平行執行，詳見 `references/modes/sample.md`。

## lean 規格檢查

lean 規格只有一份檔，不跑 verify 的五維度與跨文件。主 session 依序檢查，每項記 CRITICAL／BLOCKER／WARNING：

| # | 檢查 | 等級 |
|---|------|------|
| 1 | 全文無殘留 `[NEEDS CLARIFICATION` | BLOCKER |
| 2 | 每條 US 都有 AC；關鍵 BR 有正例與反例，AC 代入具體數字 | CRITICAL |
| 3 | 決策表每列「否決的選項與原因」非空 | CRITICAL |
| 4 | §3 提到的既有元件、端點、資料表實際存在（Grep／唯讀 DB 查詢；範圍大時派 `lifecycle:scout`） | CRITICAL |
| 5 | §3.4 邊界涵蓋空值、極值、狀態、並發、權限（不適用要寫理由） | WARNING |
| 6 | 沒有寫死實作手段（框架、快取、鎖、佇列） | WARNING |
| 7 | 範圍寫了「不包含」；`[推論]` 都附依據 | WARNING |

結論：0 CRITICAL／BLOCKER 且 0 WARNING → ✅ 可直接開發；只有 WARNING → ⚠️ 需修正後開發；其餘 → ❌ 不可開發。
結果以文字回報（lean 不另落報告檔；落檔的只有 verify 模式，見 `references/modes/verify.md` Task 7），修正後重跑同一張表；同一份規格連續第三輪仍不過就停下回報使用者。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 同時帶 `--readiness` 與 `--sample` | 停下問要跑哪一個 |
| 唯讀 DB 查詢工具不可用 | 該模式檔的降級規則照做（verify：DB 實查項標「未查證（無 DB 工具）」，不擋）；lean 第 4 項改以程式碼與既有規格查證並註明 |
| subagent 未回報告路徑 | 不自己補跑 verify；回報失敗並建議重派 |
