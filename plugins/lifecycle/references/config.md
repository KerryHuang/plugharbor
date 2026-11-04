# lifecycle 設定

專案設定放在專案根的 `.plugharbor/lifecycle.yml`，由 `scripts/config.py` 讀取。退出碼 2 是「缺檔、缺鍵（值為空也算）或格式錯誤」的訊號：呼叫的 skill 依 `harness-terms.md` 的提問方式問使用者，再把答案寫進該檔，不自行猜值。

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get ticket.tool   # 缺檔、缺鍵或格式錯誤：退出碼 2，stderr 一行說明
```

有預設值的鍵（`scale`、`spec.dir`）缺檔或缺鍵時直接回預設值。專案只有舊檔 `.plugharbor/delivery-flow.yml` 時一律退出碼 2 並提示改名為 `lifecycle.yml`（鍵不變）：不要當成沒設定而重問全部鍵。

## 鍵

| 鍵 | 說明 | 預設 |
|----|------|------|
| `scale` | 產出規模：`lean`（一份規格、一張票、不拆角色）或 `full`（FRD／SAD／BFS／FFS 與 PM／SA／QA／Dev 四角色票樹）。只決定產出哪些檔、拆幾張票，流程相同 | `lean` |
| `spec.dir` | 規格與 `LEARNINGS.md` 的目錄（相對專案根） | `docs/specs` |
| `ticket.tool` | 票務工具：`linear`、`github`、`jira` | 無（必填） |
| `ticket.team` | Linear 的 team 名稱或 key | 無（`linear` 時必填） |
| `ticket.repo` | GitHub Issues 的 `owner/repo` | 無（`github` 時必填） |
| `ticket.states` | 抽象階段 → 工具的狀態名（Linear、Jira）或 label（GitHub）對照 | 無（必填） |
| `publish-target` | 會議記錄等文件的發布位置，`file:<相對目錄>` 或 `hedgedoc:<url>` | 無（必填；詢問時建議 `file:docs/meetings`） |
| `manual-brand` | 操作手冊封面的品牌文字（字串）。`--brand` 優先；留空或不設則封面不印品牌 | 無（選填） |
| `qa.environments` | `qa-verify` 可驗收的環境清單，每項 `{name, url, writable}`；`writable` 為 true 才允許建資料與送出 | 無（`qa-verify` 必填） |

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

新建的 Linear team 預設 workflow 沒有 In Review：先到 team 的 Settings → Workflow 補上，否則改到 `in-review` 時 ticket-ops 會查不到狀態而停下。

GitHub Issues（狀態用 label `stage:<名稱>`，`done`、`canceled` 改為關閉 issue，對照值僅作記號）：

```yaml
ticket:
  tool: github
  repo: example-org/example-repo
  states:
    backlog: "stage:backlog"
    todo: "stage:todo"
    in-progress: "stage:in-progress"
    in-review: "stage:in-review"
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

## qa.environments

`qa-verify` 的環境可寫性只看這個鍵，不看網址、不查任何環境表，也與有無 DB 工具無關（沒有 DB 工具只影響 `含個資` 與資料斷言查核）。判準是**環境歸屬**：團隊自有、資料可任意異動的測試環境設 `writable: true`；含真實客戶資料（或自正式環境還原）的環境設 `false`。不在清單上的環境一律視為不可寫。

```yaml
qa:
  environments:
    - {name: dev, url: "https://dev.example.test/", writable: true}
    - {name: customer-copy, url: "https://copy.example.test/", writable: false}
```

登入帳密不進設定檔，放專案根的 `.plugharbor/qa.local.md`（本機檔，須加進 `.gitignore`），一個環境兩行：

```
dev-username: qa-user
dev-password: <密碼>
```

## 跨 plugin 依賴的決定

lifecycle 的實機驗收、操作手冊、PDF 轉檔等流程會叫用 `browser-docs` 的 skill 與 agent，`toolkit` 亦同。`plugin.json` 不宣告 `dependencies`：每個 plugin 都要能單獨安裝，叫用其他 plugin 一律可選，沒裝時照 `shared-preludes.md`「可選依賴」降級。

- 跨 plugin 叫用用命名空間 `browser-docs:<skill>`。
- `${CLAUDE_PLUGIN_ROOT}` 只指向擁有該檔的 plugin，不能用它讀 `browser-docs` 的檔案；因此 `harness-terms.md` 等共用素材在兩個 plugin 各放一份，由 `scripts/test_harness_terms_sync.py` 驗內容一致。
