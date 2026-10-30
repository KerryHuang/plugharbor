# 派工偏好

agent-dispatch 選對象前讀這份。前半段是使用者的偏好，以使用者寫的為準；後半段是實測事實，會隨版本變。用過有新心得就補在這裡，不寫進腳本。

## 使用者偏好

- 使用者有指定對象時，一律照做。
- pi 走 claude-bridge（Claude Agent SDK），官方允許用訂閱額度，用量和 Claude Code 算在同一份；派 pi 等於花 Claude 的額度。
- 想要不同模型家族的看法（審查、第二意見）時，優先交給另一家：codex 是 OpenAI，agy 是 Google，不要再派給同一家的 Claude。

## 實測事實（2026-10-23，macOS）

| 對象 | 回應速度 | 成本提示 | 備註 |
|---|---|---|---|
| claude | 約 3～5 秒 | Claude 訂閱 | 最快 |
| codex | 約 7～10 秒 | 保留使用者設定時一次約 3 萬 token | 唯讀沙箱下它執行的指令連不了網 |
| agy | 約 8～12 秒 | Google 帳號額度 | 回覆乾淨、偏慢 |
| pi | 約 6 秒 | 走 Claude 訂閱（claude-bridge） | 模型同 Claude，不算另一家觀點 |
