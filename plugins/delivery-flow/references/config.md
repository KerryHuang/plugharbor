# delivery-flow 設定

專案設定放在專案根的 `.plugharbor/delivery-flow.yml`。缺檔或缺鍵時，skill 以 `scripts/config.py` 讀取並停下，給一行建檔指引：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get ticket.tool   # 缺檔或缺鍵：退出碼 2，stderr 一行指引
```

## 鍵

| 鍵 | 說明 | 預設 |
|----|------|------|
| `ticket.tool` | 票務工具：`linear`、`github`、`jira` | 無（必填） |
| `ticket.team` | Linear 的 team 名稱或 key | 無（`linear` 時必填） |
| `ticket.repo` | GitHub Issues 的 `owner/repo` | 無（`github` 時必填） |
| `ticket.states` | 抽象階段 → 工具的狀態名（Linear、Jira）或 label（GitHub）對照 | 無（必填） |
| `publish-target` | 會議記錄等文件的發布位置，`file:<相對目錄>` | `file:docs/meetings` |
| `manual-brand` | 操作手冊的品牌設定（名稱、色票等） | 無 |

抽象階段固定為 `backlog`、`todo`、`in-progress`、`in-review`、`done`、`canceled`；skill 只用這些名字，由 `ticket.states` 轉成工具上的實際名稱。

## 範例

Linear：

```yaml
ticket:
  tool: linear
  team: Platform
  states:
    backlog: Backlog
    todo: Todo
    in-progress: In Progress
    in-review: In Review
    done: Done
    canceled: Canceled
publish-target: file:docs/meetings
```

GitHub Issues（狀態用 label，`done`、`canceled` 對應 issue 的 closed）：

```yaml
ticket:
  tool: github
  repo: example-org/example-repo
  states:
    backlog: "status: backlog"
    todo: "status: todo"
    in-progress: "status: in-progress"
    in-review: "status: in-review"
    done: closed
    canceled: "closed: not planned"
```

Jira 對照範例（**未實測**，僅供參考；`config.py` 接受 `jira`，但沒有對應的票務層實作驗證過）：

```yaml
ticket:
  tool: jira
  states:
    backlog: Backlog
    todo: To Do
    in-progress: In Progress
    in-review: In Review
    done: Done
    canceled: Won't Do
```

## 跨 plugin 依賴的決定

delivery-flow 的實機驗收、操作手冊、PDF 轉檔等流程要叫用 `browser-docs` 的 skill 與 agent。查證結論（Claude Code 以官方文件為準，Codex 與 pi 未實測）：

- **Claude Code**：`plugin.json` 支援 `dependencies` 欄位。delivery-flow 宣告 `"dependencies": ["browser-docs"]`（同 marketplace 寫 bare name，不寫 version）。安裝、`/reload-plugins`、marketplace 更新時自動補裝並啟用 `browser-docs`；依賴缺失或停用時，delivery-flow 會被停用。
- **Codex**：plugin 欄位清單沒有依賴欄位，視為不支援。
- **pi**：沒有依賴機制。
- Codex、pi 由 `setup/install.sh` 補（預設安裝全部 plugin），使用者手動安裝時需一併裝 `browser-docs`。
- 跨 plugin 叫用用命名空間 `browser-docs:<skill>`；A 叫 B 的 skill 在文件中未明說，僅依賴定義暗示支援（**未實測**）。
- `${CLAUDE_PLUGIN_ROOT}` 只指向擁有該檔的 plugin，不能用它讀 `browser-docs` 的檔案；因此 `harness-terms.md` 在兩個 plugin 各放一份、內容一致。
