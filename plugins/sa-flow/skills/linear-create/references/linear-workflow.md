# Linear 工作流程

## 團隊與識別碼

| 團隊 | 識別碼前綴 | 角色 |
|------|-----------|------|
| `{PM_team}` | PRD- | 產品管理、需求規劃 |
| `{SA_team}` | SPC- | 系統分析、規格制定（SAD/BFS/FFS） |
| `{QA_team}` | QAT- | 測試驗證、Bug 管理 |
| `{Dev_team}` | DEV- | 後端/前端開發 |

> 識別碼前綴為示意（範例用 PRD／SPC／QAT／DEV），實際依各 team 的 key。

> SA 與 PM 並存：PM 負責**需求面**（FRD），SA 負責**系統面**（SAD/BFS/FFS）。

## 工作流程類型

### 類型一：Feature / 外部 Issue / 外部 Bug

**票層級結構**：
```
PRD-XXX 【需求】... (需求文件 FRD)
  ├── SPC-XXX 【規格】... (規格制定 SAD/BFS/FFS)
  └── QAT-XXX 【測試】... (測試文件)
        ├── DEV-XXX 【後端】... (後端開發)
        └── DEV-YYY 【前端】... (前端開發) ← Blocked by 後端
```

**流程（兩階段開票）**：

1. **PM 開票階段**：PM 建立需求票 → 同步建立 SA 子票 → @mention SA
2. **SA 規格制定**：SA 開票後 Todo → In Progress → 產出 SAD/BFS/FFS → 通過 `verifying-specs` → Done
3. **SA Done 觸發開下游票**：SA 完成後建立 QA 子票 + Dev Dev 子票（或將既有 Backlog 票轉 Todo）；一次建齊模式則由 `第一個 Dev 票 blocked by SA` 的 unblock 自動通知
4. **Dev 實作**：第一個 Dev 票先行（後端優先，無後端則前端）→ 前端依賴的後端票都完成後前端解鎖（In Progress → In Review → Done）
5. **DoD 翻轉**：**最後一個 Dev 票** Done → QA 轉 Testing；QA Done → PM 轉 Testing；PM Done → 全案完成

### 類型二：內部 Bug

**票層級結構**：
```
QAT-XXX 【Bug】... (問題描述/測試)
  ├── DEV-XXX 【後端】... (後端問題描述/解決方案)
  └── DEV-YYY 【前端】... (前端問題描述/解決方案) ← Blocked by 後端（若有）
```

**流程**：
1. **QA** 建立問題描述 → 建立 Dev 子票
2. **Dev** 後端先行（若有），前端被後端 Blocked

## 狀態流轉

### 規劃階段

所有相關票 → **Backlog**

### 實作階段（Feature / 外部 Issue / 外部 Bug）

| 階段 | 執行者 | 狀態變化 | 交接動作 |
|------|--------|----------|----------|
| 需求提出 | PM | 單開 **Backlog** | 尚未分析；決定開 SA 分析時 → In Refinement |
| 需求分析 | PM | Backlog → **In Refinement** | 開 SA 子票（SA 狀態 **Todo**）；PM 分析中 |
| 規格制定 | SA | **Todo** → **In Progress** → **Done** | SA Done → 分析完成，開 QA + Dev 子票並將 PM 更新為 **In Progress** |
| 分析完成 | PM | In Refinement → **In Progress** | 由 SA Done（或分析在 PM 內完成）觸發；Dev 可進行 |
| 後端開發 | Dev | **Todo**（分析完成即可開工；未分析時為 Backlog）→ **In Progress** → **In Review** → **Done** | 前端解鎖 |
| 前端開發 | Dev | **Blocked By BE**（依賴未完成的後端票，見 SKILL.md Step 8.5）/ **Todo**（無）→ **In Progress** → **In Review** → **Done** | DoD checklist → QA 狀態改 **Testing** |
| 測試驗證 | QA | Testing → **Done** | DoD checklist → PM 狀態改 **Testing** |
| PM 確認 | PM | Testing → **Done** ✅ | 全案完成（子票 2/2） |

### 實作階段（內部 Bug）

| 階段 | 執行者 | 狀態變化 | 交接動作 |
|------|--------|----------|----------|
| 後端開發 | Dev | Backlog → **Todo** → **In Progress** → **Done** | 前端開始（若有） |
| 前端開發 | Dev | **Blocked By BE** → **Todo** → **In Progress** → **Done** | QA 狀態改 **Testing** |
| 測試驗證 | QA | Testing → **Done** | 完成 |

## 狀態對照表

| 狀態 | 類型 | 說明 | 適用團隊 |
|------|------|------|---------|
| Backlog | backlog | 規劃中 / 上游未啟動 | 全部 |
| In Refinement | backlog | 需求釐清中（PM 開票後） | PM |
| Todo | unstarted | 待開始 | 全部 |
| In Progress | started | 開發/分析中 | SA、Dev |
| In Review | started | 程式審查中 | Dev |
| Testing | started | 測試中 | QA、PM |
| Blocked By BE | unstarted / 自訂 | 前端待後端完成（前端依賴未完成後端票時的初始狀態；Dev team 自訂 state，無則以 Todo 代之） | Dev（前端票） |
| Done | completed | 已完成 | 全部 |
| Canceled | canceled | 已取消 | 全部 |

## DoD Checklist 翻轉機制（Feature）

下游票完成時，**必須**透過 DoD checklist 翻轉上游票狀態，避免狀態錯位：

| 觸發時機 | 動作 |
|---------|------|
| SA 票 Done | 開立 QA + Dev 子票（或將既有 Backlog 票 → Todo）；一次建齊由 `第一個 Dev 票 blocked by SA` 自動 unblock |
| 前端的所有 blocker 都 Done／Canceled | 前端 Blocked By BE → Todo（只完成其中一張不轉） |
| **最後一個 Dev 票** Done | QA 票 → **Testing** + @QA（最後 = 有前端即前端，只有後端即後端） |
| QA Done | PM 票 → **Testing** + @PM |
| PM Done | 全案完成 ✅ |

## 交接操作

### SA Done → 開立 QA + Dev 子票

> SA Done = 分析完成，故此時建立的 Dev 樹為**可開工**狀態（QA/BE `Todo`、FE `Blocked By BE`），並將 PM 更新為 `In Progress`。

```
# 更新 SA 票為 Done
Linear MCP update_issue(id: "SPC-XXX", state: "Done")

# 分析完成 → 更新 PM 票為 In Progress
Linear MCP update_issue(id: "PRD-XXX", state: "In Progress")

# 建立 QA 子票（parent = PM 票）——分析完成，可開工 → Todo
Linear MCP save_issue(team: "{QA_team}", parent: "PRD-XXX", title: "【測試】...", state: "Todo")

# 建立 Dev 後端票（parent = QA 票）——分析完成，可開工 → Todo
Linear MCP save_issue(team: "{Dev_team}", parent: "QAT-XXX", title: "【後端】...", state: "Todo")

# 建立 Dev 前端票（parent = QA 票，blockedBy = 後端）——有後端 → Blocked By BE（無此 state 則 Todo）
Linear MCP save_issue(team: "{Dev_team}", parent: "QAT-XXX", title: "【前端】...", blockedBy: ["DEV-XXX-backend"], state: "Blocked By BE")
```

> 若採「一次建齊・未分析」模式，QA/Dev 建立時為 `Backlog`（parked），SA Done 時再批次轉 Todo、PM 轉 In Progress，不重複建票；且建票時**第一個 Dev 票**（後端優先，無後端則前端）已掛 `blocked by SA`，SA Done 會自動 unblock 通知，不需人工 @。

### 後端完成 → 交接前端

```
# 更新後端票為 Done
Linear MCP update_issue(id: "DEV-XXX", state: "Done")

# 留言說明完成內容
Linear MCP create_comment(issueId: "DEV-XXX", body: "完成報告...")
```

### 最後一個 Dev 票完成 → 交接 QA

> 「最後一個 Dev 票」= 後端、前端都有時為前端；只有後端時即後端。

```
# 更新最後一個 Dev 票為 Done
Linear MCP update_issue(id: "DEV-YYY", state: "Done")

# 更新 QA 票為 Testing 並 @mention QA 負責人
Linear MCP update_issue(id: "QAT-XXX", state: "Testing")
Linear MCP create_comment(issueId: "QAT-XXX", body: "Dev 完工，QA 可開始測試 @{QA_assignee}")
```

### QA 驗證完成 → 交接 PM（Feature / 外部流程）

```
# 更新 QA 票為 Done
Linear MCP update_issue(id: "QAT-XXX", state: "Done")

# 更新 PM 票為 Testing 並 @mention PM
Linear MCP update_issue(id: "PRD-XXX", state: "Testing")
Linear MCP create_comment(issueId: "PRD-XXX", body: "QA 驗證通過，請確認 @{PM_assignee}")
```

## Blocked 關係

規則以 SKILL.md Step 8.5 為準；以下是兩種常見關係的寫法。

**1. `前端 blocked by 後端`（前端依賴同批新建或未完成的既有後端票時）：**

```
Linear MCP create_issue(
  title: "【前端】...",
  team: "{Dev_team}",
  state: "{Dev_team_blocked_by_be_id}",  # Blocked By BE；無此 state 則用 {Dev_team_todo_id}
  blockedBy: ["DEV-XXX"]  # 後端票 ID
)
```

> state 與 blockedBy 並存：state 供看板一眼識別，blockedBy 供 unblock 推播。

**2. `第一個 Dev 票 blocked by SA`（僅「一次建齊」模式）：**

第一個 Dev 票 = 後端優先，無後端則前端。取代「QA/Dev 待 SA Done」的 Backlog 口頭約定，SA Done 自動 unblock 通知該 Dev：

```
Linear MCP create_issue(
  title: "【後端】...",   # 或【前端】（只有前端時）
  team: "{Dev_team}",
  blockedBy: ["SPC-XXX"]   # SA 票 ID
)
```

> 分階段模式不掛此條——下游票 SA Done 後才建立，建立+指派即 gate，blockedBy 會一出生即解除無意義。

## Git 分支命名

- Feature: `feature/<ticket-id>` (例: `feature/abc-123`)
- Bug: `bugfix/<ticket-id>`
- Hotfix: `hotfix/<ticket-id>`

## 完成報告範本

```markdown
## 實作完成報告

### Commit
- **Hash**: `xxxxxxxx`
- **訊息**: `feat(scope): 描述`

### 變更檔案
| 檔案 | 說明 |
|------|------|
| path/to/fileA | 新增 |
| path/to/fileB | 修改 |

### 修復問題（如有）
- 問題描述
- 解決方案
```

## 注意事項

- 所有留言使用**繁體中文**
- **Feature 必經 SA 階段**；Bug 直接 QA → Dev 不開 SA
- 前端依賴後端票（同批或既有）時，後端完成前前端不可開始（Blocked 狀態）；沒有被依賴的後端票時無此限制
- 交接時主動更新下游票的狀態，並 @mention 下一關負責人（unblock/指派通知可能被通知偏好吃掉，@mention 一定推播）
- DoD checklist 觸發上游狀態翻轉（**最後一個 Dev 票** Done → QA Testing；QA Done → PM Testing）
- 完成報告需包含可追溯的 commit hash
