# Formwright 試用 tickets 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formwright 裝上 tickets 跑真實工作，問題經 plugharbor issue 回饋、由常駐 worker 修正發版。

**Architecture:** 不改任何 plugin 程式。plugharbor 端：建 label、開一個常駐 herdr worker 照下方 prompt 處理 `from:formwright` 票。Formwright 端：由它自己的主控 session 在段與段之間套用設定（避免和正在跑的自動駕駛搶同一個 checkout），本 session 只派工與查證。

**Tech Stack:** tickets 1.3.0（GitHub Issues＋Projects）、`gh`、herdr（`toolkit:agent-dispatch` 的 `mux.py`）、`setup/install-project.sh`。

**Spec:** `docs/superpowers/specs/2026-11-20-formwright-tickets-trial-design.md`

## Global Constraints

- roadmap.md 與 todo.md「近期可開工」不得因試用改動內容（只改 todo.md 區塊說明）。
- plugharbor skill 行為、規則、description 的改動一律加 `needs-decision` 等使用者裁決，worker 不自行 push。
- 發版：`blocker` 修完立刻 patch；其餘每天合併一版；CHANGELOG「起因」寫 issue 號。push 前跑 `python3 scripts/ci/validate.py` 與 `claude -p --plugin-dir plugins/tickets` 本地 e2e。
- 跨 session 訊息只在「blocker 發版」與「Formwright 開 blocker」時傳。
- 兩個 repo 都公開：issue 內文不得含個人路徑、內網 IP、公司名（plugharbor 外洩規則）。
- git：逐檔 `git add`、不用 `--no-verify`。

## Review Focus

- Formwright 自動駕駛正在跑時改它的 checkout → 由它自己在段收尾套用（Task 3），不從外部改檔。
- worker 輪詢撞上 Formwright 同一則回報重複開票 → worker 開工前 `gh issue list --search` 查重，重複的關為 duplicate（Task 2 prompt）。
- Formwright 段開工更新 plugin 失敗（網路、marketplace 衝突）→ 照舊版繼續跑並記進回來報告，不停產線（Task 3 交辦內容）。
- 看板內建 workflow 沒關，關票時 Status 被改錯 → Task 3 驗收時檢查一張 not planned 票的 Status 是 Canceled。
- worker 修到一半 context 爆掉或卡住 → 草稿分支先 push，票上留進度（Task 2 prompt）。

---

### Task 1：plugharbor 建 label

**Files:** 無（GitHub 設定）

- [ ] **Step 1：建四個 label**

```bash
gh label create from:formwright -R KerryHuang/plugharbor --color 5319E7 --description "Formwright 試用回饋"
gh label create plugin:tickets  -R KerryHuang/plugharbor --color 0E8A16 --description "tickets plugin"
gh label create blocker         -R KerryHuang/plugharbor --color B60205 --description "擋住試用場產線，修完立刻發版"
gh label create needs-decision  -R KerryHuang/plugharbor --color FBCA04 --description "改動 skill 行為，等使用者裁決"
```

- [ ] **Step 2：驗證** `gh label list -R KerryHuang/plugharbor | grep -E "from:formwright|plugin:tickets|blocker|needs-decision"` 出現四行。

### Task 2：plugharbor 常駐 worker

**Files:** 無（herdr pane；prompt 存在本計畫，不進 plugin）

- [ ] **Step 1：用 `toolkit:agent-dispatch` 長任務模式開 pane**（cwd plugharbor、claude、sonnet-medium；碰 skill 行為的方案由使用者裁決，不需升級），prompt：

> 你是 plugharbor 的 tickets 回饋 worker。每 30 分鐘（或收到「有 blocker」訊息時立刻）跑 `gh issue list -R KerryHuang/plugharbor --label from:formwright --state open`。每張新票：
> 1. 查重（`gh issue list --search` 同關鍵字），重複就留言連結並以 duplicate 關閉。
> 2. 用 `tickets:triage` 分流並在票上留結論。
> 3. bug、文件錯、測試缺口：開分支修＋測試（`python3 scripts/ci/validate.py`、tickets 腳本測試、`claude -p --plugin-dir plugins/tickets` 在 scratchpad fixture 重現），合回 main。
> 4. 改 skill 行為、規則、description：草稿分支 push，票上寫方案與理由，加 `needs-decision`，不合併。
> 5. 發版：`blocker` 修完立刻用 `release-plugin` 發 patch 並 push，傳一則訊息給 Formwright 主控「tickets x.y.z 已發，修 #N」；其餘累積，每天 21:00 後合併發一版，不通知。
> 6. 修到一半要中斷：分支先 push、票上留進度。
> 遵守 plugharbor AGENTS.md（版號同步、外洩規則、逐檔 git add）。只在發版或卡住時傳訊，不報進度。

- [ ] **Step 2：驗證** pane 存在且第一次輪詢跑完（pane 輸出含 `gh issue list` 結果，沒有票時回報「無新票」後等待）。

### Task 3：Formwright 端套用（交辦給它的主控）

**Files（由 Formwright session 改）：** `.plugharbor/lifecycle.yml`（新增 `ticket:`）、`docs/todo.md`、`AGENTS.md`

- [ ] **Step 1：找 Formwright 主控**：`ListAgents` 或 `tower.py radar` 找 cwd 為 Formwright 主 repo 的 session；找不到就照 agent-dispatch 在 Formwright 主 repo 開新 pane 接手。
- [ ] **Step 2：傳一則交辦**（下一段收尾、開新段前做），內容：
  1. `setup/install-project.sh <Formwright 根> tickets`（plugharbor 本機路徑附上）。
  2. `.plugharbor/lifecycle.yml` 加 `ticket:`：`tool: github`、`repo: KerryHuang/formwright`、`states` 與 `project` 照 plugharbor 的同名區塊（看板新建於 KerryHuang 帳號、號碼填實際值，關掉 Project 內建 workflow，`gh auth refresh -s project`）。
  3. todo.md「其他」逐項 ticket-create 成 backlog 票，刪除該區；區塊說明「從下方『其他』挑」改成「從 backlog 票挑，升上來的項目寫票號」。
  4. AGENTS.md 加三行：新發現開票不寫 todo；票隨工作改階段、合併後關票留 commit；用 tickets 遇到問題在 `KerryHuang/plugharbor` 開 issue（`from:formwright`、`plugin:tickets`，擋產線的加 `blocker` 並傳訊叫醒 plugharbor worker），開完續做別的。
  5. AGENTS.md 加一行：段開工前 `claude plugin marketplace update plugharbor && claude plugin update tickets@plugharbor --scope project` 後 `/reload-plugins`；失敗照舊版跑、記進回來報告。
  6. 完成後回一則訊息附 commit SHA。
- [ ] **Step 3：查證回報**（不照單全收）：`git -C <Formwright> show <SHA> --stat` 只動上述三檔；`gh issue list -R KerryHuang/formwright --label stage:backlog` 張數＝原「其他」項數；roadmap.md 無 diff；隨機關一張 not planned 測試票，看板 Status 為 Canceled。

### Task 4：ticket-report daily 排程

- [ ] **Step 1：** 在 Formwright 主 repo 建每日 08:30 的 launchd 工作，跑 `claude -p "/tickets:ticket-report daily"`，輸出到該專案慣用報表目錄；先手動跑一次確認 skill 可由 `-p` 斜線叫用（`disable-model-invocation` 只擋模型自叫）。
- [ ] **Step 2：驗證** 手動跑產出當日報表檔；`launchctl list | grep ticket-report` 有該工作。

### Task 5：一週後驗收（2026-11-27）

- [ ] 寫一則 project 記憶追蹤試用（取代時再刪），屆時檢查：Formwright 至少 5 張票 backlog→done（`gh issue list -R KerryHuang/formwright --state closed`）；至少一則 `from:formwright` 走完修正→發版→Formwright 載入新版（Formwright transcript 的 tickets Base directory 版本）；roadmap.md 試用期間沒有非段狀態的改動。
- [ ] 結果寫回本計畫末尾，決定第二階段（ticket-reply、待決上票）要不要做。
