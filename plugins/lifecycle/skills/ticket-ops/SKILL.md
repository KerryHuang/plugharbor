---
name: ticket-ops
description: "票務工具層：對 Linear 或 GitHub Issues 做建票（含父子）、改階段、留言、附圖、查詢、blocked-by，依 ticket.tool 設定載入對應做法。其他 skill 需要操作票時叫用，不單獨觸發。觸發：「開票」「改票狀態」「在票上留言」「ticket-ops」。"
argument-hint: "<操作名> [參數…]"
model: sonnet
---

# 票務工具層（ticket-ops）

> 非 Claude Code（如 Pi）執行時，先讀 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`（Claude Code 照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

其他 skill（`issue-triage`、報表、規格類 skill）只說「建票／改階段／留言…」，實際怎麼打工具由本 skill 依設定決定。

## 0. 讀設定

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get ticket.tool
```

退出碼 2（缺檔、缺鍵或格式錯誤）→ 依 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md` 的提問方式問使用者：`ticket.tool`，以及對應的 `ticket.team`（Linear）或 `ticket.repo`（GitHub），再逐階段問 `ticket.states` 對照（格式與範例見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`），寫入 `.plugharbor/lifecycle.yml`。不自行猜值。

## 1. 載入對應 reference

| `ticket.tool` | 讀 |
|---|---|
| `linear` | `${CLAUDE_SKILL_DIR}/references/linear.md` |
| `github` | `${CLAUDE_SKILL_DIR}/references/github.md` |
| `jira` | **先告知「Jira 只有設定對照範例（`${CLAUDE_SKILL_DIR}/references/jira-example.md`），沒有實測過的實作」，使用者明確確認要繼續才往下**；確認後依範例與 Jira MCP／REST 自行對映，結果標「未實測」 |
| 其他值 | 停下，列出合法值請使用者更正設定 |

操作名稱、參數與回傳一律以 `${CLAUDE_SKILL_DIR}/references/contract.md` 為準：`create`、`set_stage`、`comment`、`attach`、`query`、`get`、`link_blocked_by`。

## 2. 執行

1. 叫用端給操作名與參數；缺必填參數就問，不猜。
2. `set_stage`、建票帶 `stage` 時，先換成工具原生值：

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/ticket_backend.py stage <stage>
   ```

   輸出 JSON（Linear：`{"state": 名稱}`；GitHub：`labels_add`／`labels_remove`／`close`／`reason`）。退出碼 2 → 階段名不合法或 `ticket.states` 缺該階段，把 stderr 回報給叫用端，不自行補值。
3. 照 reference 的對應步驟呼叫工具（Linear MCP 或 `gh`）。
4. 回傳票 ID／URL 與實際做了什麼；工具降級（例如 GitHub 的 blocked-by 只能寫在內文）時明講落差。

## 紅線

- 改描述前先讀回原文再整份送回；送出後讀回確認有寫入（成功回應不等於寫入）。
- 不替叫用端改階段語意：階段只用 contract 的六個名字。
- 工具不支援的能力一律明講降級方式，不默默略過。
