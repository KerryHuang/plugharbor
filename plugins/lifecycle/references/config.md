# lifecycle 設定

專案設定放在專案根的 `.plugharbor/lifecycle.yml`，由 `scripts/config.py` 讀取。退出碼 2 是「缺檔、缺鍵（值為空也算）或格式錯誤」的訊號：呼叫的 skill 依 `harness-terms.md` 的提問方式問使用者，再把答案寫進該檔，不自行猜值。退出碼 3（只找到舊檔 `.plugharbor/delivery-flow.yml`）→ 停下，請使用者改名為 `lifecycle.yml`（或經同意代為 `git mv`），不問鍵、不寫檔。

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get ticket.tool   # 缺檔、缺鍵或格式錯誤：退出碼 2；只有舊檔：退出碼 3；stderr 一行說明
```

有預設值的鍵（`spec.dir`）缺檔或缺鍵時直接回預設值。專案只有舊檔 `.plugharbor/delivery-flow.yml` 時一律退出碼 3 並提示改名為 `lifecycle.yml`（鍵不變），有預設值的鍵也一樣：不要當成沒設定而重問全部鍵。`spec.dir` 沒設、而專案根 `CLAUDE.md` 有舊鍵 `sdlc-docs-path:` 時沿用其值，stderr 提示改設 `spec.dir`。兩者都沒有而專案規則（AGENTS.md、`.claude/rules/`）指定了設計文件目錄時，`lifecycle:spec` 會把它寫成 `spec.dir`。

## 鍵

「必填」指**用到時才必填**：沒用到該鍵的流程不檢查，到用的 skill 才因退出碼 2 詢問。例如只跑 `spec` 不需要任何 `ticket.*` 或 `publish-target`。

| 鍵 | 說明 | 預設 |
|----|------|------|
| `spec.dir` | 規格與 `LEARNINGS.md` 的目錄（相對專案根） | `docs/specs` |
| `ticket.tool` | 票務工具：`linear`、`github`、`jira` | 無（票務操作時必填：`ticket-ops` 及經它開票、改票的 skill，如 `ticket-create`、`ticket-reply`） |
| `ticket.team` | Linear 的 team 名稱或 key | 無（`linear` 時必填） |
| `ticket.repo` | GitHub Issues 的 `owner/repo` | 無（`github` 時必填） |
| `ticket.project` | GitHub Projects 看板：`owner`、`number`、`field`（預設 `Status`）、`options`（抽象階段 → 單選欄位的選項名）。設了 `ticket-ops` 建票時加進看板、改階段時同步改欄位 | 無（選填，只用於 `github`） |
| `ticket.states` | 抽象階段 → 工具的狀態名（Linear、Jira）或 label（GitHub）對照 | 無（票務操作時必填，`ticket-ops` 缺鍵時與 `ticket.tool` 一併詢問） |
| `publish-target` | 會議記錄等文件的發布位置，`file:<相對目錄>` 或 `hedgedoc:<url>` | 無（`meeting-minutes` 發布時必填；詢問時建議 `file:docs/meetings`） |
| `manual-brand` | 操作手冊封面的品牌文字（字串）。`--brand` 優先；留空或不設則封面不印品牌 | 無（選填） |
| `qa.environments` | `qa-verify` 可驗收的環境清單，每項 `{name, url, writable}`；`writable` 為 true 才允許建資料與送出 | 無（`qa-verify` 必填） |

`scale` 已在 3.0.0 移除：`config.py get scale` 固定回 `lean`；設定檔有這個鍵時 stderr 提示，可以刪掉。

抽象階段固定為 `backlog`、`todo`、`in-progress`、`in-review`、`done`、`canceled`；skill 只用這些名字，由 `ticket.states` 轉成工具上的實際名稱。

## 範例

規格目錄（巢狀寫法，不寫成 `spec.dir:`）：

```yaml
spec:
  dir: docs/design
```

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
  project:              # 選填：同步 GitHub Projects 看板
    owner: example-org
    number: 3
    field: Status
    options:
      backlog: Backlog
      todo: Todo
      in-progress: In Progress
      in-review: In Review
      done: Done
      canceled: Canceled
```

看板的選項要自己先在 Project 建好（名稱與 `options` 一致），並關掉 Project 內建的 workflow（Project → Workflows 的 Item closed、Item reopened、Auto-add 等），否則它會和 ticket-ops 搶著改 Status，把 not planned 關閉的票也改成 Done。gh token 要有 `project` scope（`gh auth refresh -s project`）。

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

lifecycle 的實機驗收、delivery 的操作手冊、PDF 轉檔等流程會叫用 `browser-docs` 的 skill 與 agent，`toolkit` 亦同。`plugin.json` 不宣告 `dependencies`：每個 plugin 都要能單獨安裝，叫用其他 plugin 一律可選，沒裝時照 `shared-preludes.md`「可選依賴」降級。

- 跨 plugin 叫用用命名空間 `browser-docs:<skill>`。
- `${CLAUDE_PLUGIN_ROOT}` 只指向擁有該檔的 plugin，不能用它讀 `browser-docs` 的檔案；因此 `harness-terms.md` 等共用素材在需要的 plugin 各放一份，由 repo 根 scripts/ci 的 validate.py 依 shared-copies.json 驗內容一致。
