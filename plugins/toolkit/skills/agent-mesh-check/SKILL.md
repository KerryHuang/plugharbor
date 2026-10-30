---
name: agent-mesh-check
description: 驗證本機 agent CLI（claude、codex、agy、pi）都裝好、登入有效、能互相呼叫：先查哪些有裝，有裝才驗自己回話與「入口 ↔ 其他」互叫，--full 驗全部兩兩組合。Use when 使用者說「驗證 agent CLI」「四個 CLI 都能用嗎」「CLI 互相呼叫測試」「裝新機器／升級 CLI 後檢查」，或輸入 /agent-mesh-check。
argument-hint: "[--full]"
---

# Agent CLI 互通驗證

一支腳本做完全部檢查，你只負責執行它和轉述結果。不要自己逐一手動呼叫各個 CLI，那樣結果不能和下次比較。

## 執行

腳本和本 SKILL.md 放在同一個目錄的 `scripts/` 下。在非 Claude 入口，`${CLAUDE_SKILL_DIR}` 指的就是本 SKILL.md 所在的目錄，請自己換成實際路徑。

```bash
node "${CLAUDE_SKILL_DIR}/scripts/mesh.mjs" --from <你自己是哪個 CLI：claude|codex|agy|pi> [--full]
```

- `--from` 一律帶上，填正在執行你的那個程式（harness），**不是你的模型**。例如你在 pi 裡跑 Claude 模型，就填 `pi`。腳本會以它為中心，驗它和其他已安裝 CLI 的雙向互叫。環境裡只有一個 CLI 的標記時，腳本會以標記為準；和你填的不一樣時，會印一行 `[入口]` 提示。
- `--full` 只在使用者要求時才加。它會驗全部兩兩組合，四個都裝時是 12 組，約 28 次模型呼叫，成本大約是預設模式的兩倍。
- 這個指令通常要跑 1～3 分鐘。工具的逾時要設 10 分鐘以上，能放背景就放背景。
- 腳本會用 shell 叫起其他 CLI，叫起的 CLI 自己又會連網呼叫模型。如果你的沙箱擋網路或擋子程序，要申請放寬權限再跑。不要把被擋下的結果當成「CLI 壞了」。

## 三層檢查

1. **安裝**：在 PATH 上找得到才算有裝。沒裝的標「略過」，不算失敗。
2. **自己回話**：用唯讀模式要求每個 CLI 回一個隨機字串的大寫版，驗證登入有效、模型叫得到。
3. **互叫**：在一個空的暫存目錄裡，讓 A 用 shell 執行 B 的唯讀呼叫，再把 B 的回答轉回來。只有這一步的 A 會用自動核准模式，而且 prompt 是寫死的。

狀態分五種：通過、略過、失敗、逾時、未登入或額度不足。Exit code：全部通過或略過回 0，其他回 1，用法錯誤回 2。

## 回報

- 原樣貼出腳本印的結果表。有不通過的組別時，附上該列的錯誤摘要，並依 `references/cli-notes.md` 的已知坑推測原因。
- 腳本若印出「版本和上次不同」，要特別點出來，升級後壞掉通常就是這裡造成的。
- 結果檔路徑照腳本印的轉述。結果檔只存本機，不進任何 repo。

## 注意

- pi 若透過 claude-bridge（Claude Agent SDK）跑 Claude 模型，用量會算進 Claude 訂閱額度；`--full` 會多叫幾次 pi，額度吃緊時先跟使用者說。
- 這支 skill 只驗「叫得動」。MCP、hook、guard 是否生效，屬於各專案自己的檢查。
- 各 CLI 的無互動參數與已知坑，見 `references/cli-notes.md`。
