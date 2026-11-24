# claude-api 派工路由 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** agent-dispatch 多一個派工對象 `claude-api`（同一支 claude、以 API key 計費），依用途排序，額度用完或 key 失效自動退回訂閱。

**Architecture:** 計費差異集中在 `clis.mjs` 兩個新函式：`cliEnv` 決定子程序環境（取 key／清 key），`blockInfo` 決定要不要封鎖。路由表只調順序。ask.mjs、bg.mjs、mesh.mjs 改用這兩個函式；mux.py 把 claude-api 當 claude 開。

**Tech Stack:** Node.js ESM（`node --test`）、Python 3（pytest）。

**Spec:** `docs/superpowers/specs/2026-11-24-claude-api-billing-route-design.md`

## Global Constraints

- key 來源環境變數名：`AGENT_DISPATCH_CLAUDE_API_KEY_CMD`（shell 指令，stdout 印 key）。
- 沒設該變數：所有行為、輸出、測試結果與改動前相同；環境原有的 `ANTHROPIC_API_KEY`／`ANTHROPIC_AUTH_TOKEN` 原樣傳給 claude。
- key 只進子程序環境的 `ANTHROPIC_API_KEY`；不寫檔、不進 argv、不印出、不進錯誤訊息。
- 額度不足與 claude-api 認證失敗：封鎖 24 小時。
- 公開 repo：不得出現個人路徑、鑰匙圈服務名的真實值、email；範例一律用 `<服務名>`。
- 每個 commit 前跑 `python3 scripts/ci/validate.py`；改 skills/references 的 commit 要同步版號（最後一個 task 統一 bump，toolkit 0.37.1 → 0.38.0）。

## Review Focus

1. key 指令輸出帶結尾換行或空白 → 應 trim；只有空白 → 視為取 key 失敗（Task 1 測試）。
2. key 指令卡住 → 數秒逾時、視為失敗、不拖住派工（Task 1 測試，用 `sleep 30`）。
3. 主 session 本身環境帶 `ANTHROPIC_API_KEY`、又設了 key 來源 → 派 `claude`（ask／bg／pane）必須清掉，否則退回訂閱是假的（Task 1、Task 4 測試）。
4. 輸出前段的 prompt／log 提到「Invalid API key」但實際成功（exit 0）→ 不封鎖（Task 1 測試：`blockInfo` 只在非零 exit 由呼叫端呼叫，且只看尾段）。
5. `--to claude-api` 指定對象但沒設 key 來源 → exit 127 並說明「未設定 AGENT_DISPATCH_CLAUDE_API_KEY_CMD」，不是含糊的「不在 PATH 上」（Task 3 測試）。

---

### Task 1: clis.mjs 核心——claude-api 的執行檔、環境、封鎖判定

**Files:**
- Modify: `plugins/toolkit/skills/agent-mesh-check/scripts/clis.mjs`
- Test: `plugins/toolkit/skills/agent-dispatch/dispatch.test.mjs`（既有 quotaInfo／buildArgs 測試所在）

**Interfaces:**
- Produces:
  - `CLIS = ['claude', 'claude-api', 'codex', 'agy', 'pi']`
  - `resolveBin('claude-api', env)`：`env.AGENT_DISPATCH_CLAUDE_API_KEY_CMD` 沒設或空 → `null`；否則回 `resolveBin('claude', env, platform)`。
  - `buildArgs('claude-api', …)` ≡ `buildArgs('claude', …)`。
  - `cliEnv(name: string, env: object, { timeoutMs = 10_000 } = {}) => object | null`：先 `scrubEnv(env)`；
    `claude-api` → 跑 key 指令（shell、逾時）、trim，成功則設 `ANTHROPIC_API_KEY` 並刪 `ANTHROPIC_AUTH_TOKEN`，失敗或空回 `null`；
    `claude` 且有設 key 來源 → 刪 `ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN`；其他情況等同 `scrubEnv(env)`。
    結果物件不含 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD`（子程序不需要）。
  - `blockInfo(cli: string, out: string, now = Date.now()) => { resetAt: number } | null`：先 `quotaInfo(out, now)`；為 null 且 `cli === 'claude-api'` 且尾段（同 quotaInfo 的尾 20 行規則）符合 `/invalid api key|authentication_error|api key.*(revoked|disabled)/i` → `{ resetAt: now + 24h }`。
  - `NEEDS_TOPUP` 加入 `credit balance is too low`。

- [ ] **Step 1: 寫失敗的測試**（加在 dispatch.test.mjs）
  - `resolveBin claude-api：沒設 key 來源回 null`
  - `resolveBin claude-api：有設時回 claude 的路徑`（用暫存目錄放假 `claude` 可執行檔並設 PATH）
  - `cliEnv claude-api：key 指令輸出 "sk-test\n" → ANTHROPIC_API_KEY === 'sk-test'，且無 ANTHROPIC_AUTH_TOKEN、無 AGENT_DISPATCH_CLAUDE_API_KEY_CMD`
  - `cliEnv claude-api：指令 exit 1、只印空白、或 sleep 30（timeoutMs: 500）都回 null`
  - `cliEnv claude：有設 key 來源時刪掉繼承的 ANTHROPIC_API_KEY 與 ANTHROPIC_AUTH_TOKEN`
  - `cliEnv claude：沒設 key 來源時保留 ANTHROPIC_API_KEY`
  - `blockInfo：claude-api 尾段 "Invalid API key · Fix external API key" → 24 小時`
  - `blockInfo：claude 同樣輸出 → null`
  - `blockInfo：Invalid API key 只出現在前段、尾 20 行沒有 → null`
  - `quotaInfo："API Error: 400 Your credit balance is too low to access the Anthropic API" → 24 小時`
  - `buildArgs claude-api 與 claude 相同`

- [ ] **Step 2: 跑測試確認失敗**
  Run: `node --test plugins/toolkit/skills/agent-dispatch/dispatch.test.mjs`
  Expected: 上列新測試 FAIL（`cliEnv`／`blockInfo` 未匯出等）

- [ ] **Step 3: 實作 clis.mjs 的上述介面**
  key 指令用 `child_process.execSync(cmd, { shell: true, timeout, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] })`，例外一律回 null，錯誤訊息不得含 key。`buildArgs` 的 `case 'claude-api':` 落到 claude 分支。

- [ ] **Step 4: 跑測試確認通過**
  Run: `node --test plugins/toolkit/skills/agent-dispatch/dispatch.test.mjs plugins/toolkit/skills/agent-mesh-check/agent-mesh.test.mjs`
  Expected: 全 PASS

- [ ] **Step 5: Commit**（`feat(toolkit): clis 支援 claude-api 的取 key 與封鎖判定`）

### Task 2: routing.json 依用途排序

**Files:**
- Modify: `plugins/toolkit/skills/agent-dispatch/references/routing.json`
- Test: `plugins/toolkit/skills/agent-dispatch/dispatch.test.mjs`

**Interfaces:**
- Consumes: `candidates()`（route.mjs，不改）
- Produces: tiers 內 claude-api 位置——standard、cheap 在 claude 正前方；top 在 claude 正後方；model／effort 同該級 claude 那列。`family["claude-api"] = "anthropic"`。

- [ ] **Step 1: 寫失敗的測試**（讀真實 routing.json）
  - `routing：standard 與 cheap 的 claude-api 緊接在 claude 之前，model/effort 相同`
  - `routing：top 的 claude-api 緊接在 claude 之後`
  - `reviewer('claude-api') 不挑 claude 或 pi（同家族）`
- [ ] **Step 2: 跑測試確認失敗**（同 Task 1 指令）
- [ ] **Step 3: 改 routing.json**
- [ ] **Step 4: 跑測試確認通過**
- [ ] **Step 5: Commit**（`feat(toolkit): 路由加入 claude-api，規劃類訂閱優先`）

### Task 3: ask.mjs、bg.mjs 改用 cliEnv／blockInfo

**Files:**
- Modify: `plugins/toolkit/skills/agent-dispatch/scripts/ask.mjs`、`plugins/toolkit/skills/agent-dispatch/scripts/bg.mjs`
- Test: `plugins/toolkit/skills/agent-dispatch/dispatch.test.mjs`

**Interfaces:**
- Consumes: Task 1 的 `cliEnv`、`blockInfo`、`resolveBin`
- Produces: 行為——
  - ask.mjs 迴圈內：`const env = cliEnv(c.cli, process.env)`；`null` → stderr「claude-api 取 key 失敗，略過」並 `continue`（`--to` 時 return 127）。`q` 改用 `blockInfo(c.cli, r.out)`；封鎖理由 claude-api 認證失敗寫 `'auth'`，其餘 `'quota'`。
  - `--to claude-api` 而 `resolveBin` 為 null → 訊息「未設定 AGENT_DISPATCH_CLAUDE_API_KEY_CMD」、exit 127。
  - bg.mjs：`workerEnv` 以 `cliEnv(job.cli, env)` 取代 `scrubEnv(env)`；`null` → status 寫 `failed`、`tail` 寫「取 key 失敗」；supervise 的 `quotaInfo` 改 `blockInfo(job.cli, r.out)`。其餘（不中途改派）不動。

- [ ] **Step 1: 寫失敗的測試**：在暫存目錄放假 `claude` 腳本（讀環境：有 `ANTHROPIC_API_KEY=sk-bad` 時印 `Invalid API key` 並 exit 1；沒有時印 `ok` exit 0），設 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD='echo sk-bad'`、獨立 state 檔路徑，跑 `ask.mjs --type docs`（routing 可用測試用 fixture 或 `--tier cheap` 加 `AGENT_DISPATCH_*` 既有的路徑覆寫方式；照檔內既有測試做法）。
  - 斷言 stdout 有「交給 claude」、stderr 有「改派 claude」、state 檔 `blocks['claude-api'].reason === 'auth'`。
  - `ask.mjs --to claude-api` 沒設 key 來源 → exit 127，stderr 含 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD`。
  - `workerEnv`：設了 key 來源、job.cli 為 claude 時結果無 `ANTHROPIC_API_KEY`。
- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試確認通過**（Task 1 指令）
- [ ] **Step 5: Commit**（`feat(toolkit): ask 與背景 worker 用 claude-api 時取 key、失效改派`）

### Task 4: mux.py——claude-api 以 claude 開互動 pane

**Files:**
- Modify: `plugins/toolkit/skills/agent-dispatch/scripts/mux.py`
- Test: `plugins/toolkit/skills/agent-dispatch/scripts/test_mux.py`

**Interfaces:**
- Produces: `spawn --kind claude-api` 被接受並等同 `--kind claude`，回傳 JSON 多 `"note": "pane 為互動模式，改用訂閱"`；呼叫者環境有 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD` 時，kind 為 claude／claude-api 的 pane 的 unset 清單加上 `ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN`（`clean_env_prefix` 的 POSIX 與 Windows 兩條路徑都要）。

- [ ] **Step 1: 寫失敗的測試**（test_mux.py 既有風格）
  - kind 正規化：`claude-api` → `claude`，note 存在
  - 有設 key 來源：`clean_env_prefix` 產生的 argv 含 `-u ANTHROPIC_API_KEY`（POSIX）／Windows 版 unset 清單含它
  - 沒設：兩者都不含
- [ ] **Step 2: 跑測試確認失敗**：`python3 -m pytest plugins/toolkit/skills/agent-dispatch/scripts/test_mux.py -v`
- [ ] **Step 3: 實作**（`KINDS` 加 `claude-api` 或在解析處正規化，擇一；unset 清單以參數傳入 `clean_env_prefix`，不改全域 `POLLUTED_VARS`）
- [ ] **Step 4: 跑測試確認通過**
- [ ] **Step 5: Commit**（`feat(toolkit): mux 把 claude-api 當 claude 開 pane 並清 key`）

### Task 5: mesh-check、文件、版號、實機驗收

**Files:**
- Modify: `plugins/toolkit/skills/agent-mesh-check/scripts/mesh.mjs`、`plugins/toolkit/skills/agent-mesh-check/agent-mesh.test.mjs`
- Modify: `plugins/toolkit/skills/agent-dispatch/SKILL.md`、`plugins/toolkit/skills/agent-mesh-check/references/cli-notes.md`
- Modify: `plugins/toolkit/CHANGELOG.md`、`plugins/toolkit/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、根 `README.md`（版本欄）

**Interfaces:**
- Consumes: Task 1 全部
- Produces:
  - `MARKERS['claude-api'] = []`（不從環境偵測為「自己」）。
  - mesh 第 2 層（自己回話）：沒設 key 來源 → claude-api 不列入已安裝（resolveBin 為 null，現有邏輯自然略過，輸出不多一列失敗）；有設 → 以 `cliEnv('claude-api', …)` 的環境跑 probe。所有 `env: scrubEnv(process.env)` 的 run 呼叫改成 `cliEnv(name, process.env)`，null 時該列記 `fail`、note「取 key 失敗」。
  - SKILL.md「1. 選對象」加兩行（不改 description）：claude-api 是什麼、規劃類訂閱優先其餘 API 優先、設定 `AGENT_DISPATCH_CLAUDE_API_KEY_CMD`（範例 `security find-generic-password -s <服務名> -w`）、key 要用沒開自動儲值的 org、需要 claude.ai connector 用 `--to claude`、pane 一律訂閱。
  - cli-notes.md 加 claude-api 一節：實測（2026-11-24）設了 `ANTHROPIC_API_KEY` 的 `claude -p` 一定用 key（假 key 回 `Invalid API key`、exit 1）；本機 MCP 照常載入；claude.ai connectors 會印 disabled 警告。
  - CHANGELOG `## [0.38.0] - 2026-11-24`，起因照 spec「起因與目的」。

- [ ] **Step 1: 寫失敗的測試**（agent-mesh.test.mjs）：`detectAll` 不因 claude-api 拋錯；有設 key 來源時 installed 含 claude-api。
- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作 mesh.mjs、補文件、bump 版號**（可用 repo 的 `release-plugin` skill 同步三處版號）
- [ ] **Step 4: 全套驗證**
  Run: `node --test $(git ls-files 'plugins/**/*.test.mjs') && python3 -m pytest plugins/toolkit/skills/agent-dispatch/scripts/test_mux.py && python3 scripts/ci/validate.py`
  Expected: 全 PASS、validate 無錯
- [ ] **Step 5: 實機驗收（需本機已設 key 來源）**
  - `node plugins/toolkit/skills/agent-dispatch/scripts/route.mjs pick implement`：claude-api 在 claude 前；`pick plan`：在 claude 後。
  - 寫一個一句話 prompt 檔，`node …/ask.mjs --type docs <檔>`：第一行「交給 claude-api」或（agy 排第一時）用 `--to claude-api` 驗。
  - `node plugins/toolkit/skills/agent-mesh-check/scripts/mesh.mjs`：claude-api 一列 pass。
  - `claude --plugin-dir plugins/toolkit` 開一次確認 skill 載入正常。
- [ ] **Step 6: Commit**（`feat(toolkit): mesh-check 支援 claude-api；文件與版號 0.38.0`）。**不 push**，push 前問使用者。
