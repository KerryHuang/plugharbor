---
name: tower
description: 多 session 塔台：動工前登記目標與範圍、看別的 session 在做什麼、落地前核對，Use when 使用者說「塔台」「tower」「別的 session 在做什麼」「開工登記」，或同一 repo 有多個 session／worktree 並行時開工、收工。
---

# tower：多 session 塔台

同一 repo 的 session 與 worktree 互相看不到，容易重工、合併衝突。塔台提供一份共用登記表（航班）：動工前登記、看到重疊就提醒使用者、落地前核對實際改動、收工釋放。

登記表在 git common dir 的 `tower/`，同 repo 所有 worktree 共用，不進版控。以下 `tower.py` 一律指：

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/tower/scripts/tower.py
```

## 流程

### 1. 開工：takeoff

動工前先登記（SessionStart 的摘要寫「動工前先 takeoff 登記」就是這件事）：

```
tower.py takeoff --goal "<一句話目標>" --paths <預計會改的路徑或 glob>... \
  [--segment <段號>] [--feature <功能名>] [--ticket <票號>] [--mode unattended] [--cli claude]
```

- 有對應的段號、功能名、票號就一定帶；重疊判斷先比這三項，再比 `--paths`。
- `--paths` 寫預計範圍，寧可略寬；可重複給，目錄代表其下全部；範圍外的改動落地時會被 land-check 擋（退出碼 10）。
- 無人值守執行時加 `--mode unattended`。
- 此 worktree 已有航班時退出碼 2，stdout 印既有航班 id；沿用它，不重複登記。
- 主控替 Agent tool subagent 登記（subagent 不送心跳）：在該 worktree 內加 `--proxy`，航班不因沒心跳判 `lost`（radar 標 `flying*`，worktree 不在了才算 lost）；收尾由主控 `release --id <航班 id>`（id 看 takeoff 輸出或 radar），忘了釋放就會一直算活的。
- 輸出 JSON：`id`、`overlaps`（與他班的重疊）、`warnings`（如 feature.md 標 🚧 卻沒有活航班）。

### 2. 看到重疊：只提醒，由使用者選

`overlaps` 非空，或後續 hook／`beat` 回報撞檔時，把對方航班（id、目標、重疊的項目或檔案）告訴使用者，由使用者選：等對方、協作、照飛。不自己決定，也不自己去動對方的 worktree。

`tower.py radar`（加 `--json` 取完整欄位）列出全部航班與狀態：`flying`、`landed`、`lost`（30 分鐘沒心跳或 worktree 已不存在）。`lost` 的航班不算活的，不觸發撞檔提醒，但落地核對仍會列警告。

### 3. 範圍變了：amend

```
tower.py amend [--goal "<新目標>"] [--paths <新路徑>...]
```

`--paths` 是整份取代，不是追加。

### 4. 落地前：land-check

要 commit／merge／rebase 進預設分支、或 push 到預設分支之前：

```
tower.py land-check
```

輸出 JSON（`code`、`scope_extra`、`collisions`、`behind`、`warnings`），退出碼即 `code`：

- `0` 通過：照常落地；`warnings`（如 feature.md 還沒勾 `[x]`、失聯航班也碰過同檔）逐條看過再走。
- `10` 改了申報範圍外的檔：範圍該擴大就 `amend --paths`；確定是刻意的就 `tower.py override --kind scope --reason "<理由>"` 後重試。
- `11` 與他班實際改動撞檔：有人在場，告訴使用者撞了哪些檔、對方目標，請使用者確認再繼續；無人值守，不硬闖，進佇列，回報寫「排隊等航班 <id> 落地」，繼續做不衝突的工作。
- `12` 落後預設分支：先 rebase（或 merge）預設分支，解完衝突、重跑測試，再 land-check。

同時命中多項時優先序 11 → 12 → 10。共用跑道（預設的 `docs/feature.md`、`docs/roadmap.md`、`docs/todo.md`、`**/CHANGELOG.md` 等，加上專案設定）不算撞檔。

專案要加共用檔：寫 `.plugharbor/tower.yml`，格式固定為區塊式清單：

```yaml
shared:
  - README.md
  - plugins/*/.claude-plugin/plugin.json
```

### 5. 收工

- 落地後：`tower.py landed`。
- 全部做完、不再使用此航班：`tower.py release`（刪除登記）。
- 有票號且裝了 tickets plugin：經 `tickets:ticket-ops` 更新票（comment 與狀態），不直接呼叫票務 MCP 或 CLI；沒裝就在回報裡寫明票未更新。
- 有 `docs/feature.md` 的專案，把對應項目勾成 `[x]`（land-check 會提醒）。

## 子指令速查

| 指令 | 用途 |
|---|---|
| `takeoff [--proxy]` | 登記；退出碼 2 = 已有航班；`--proxy` 代管（無心跳也不 lost） |
| `amend` | 改目標或範圍 |
| `beat [--touched <檔>...]` | 手動心跳與記錄改動，輸出目前的重疊 |
| `radar [--json]` | 全部航班 |
| `override --kind scope --reason` | 記錄刻意越界的理由 |
| `land-check` | 落地核對 |
| `landed` / `release` | 標記已落地 / 刪除登記 |

從別的 worktree 操作某航班時，除 `takeoff`、`radar` 外都可加 `--id <航班 id>`。

## Claude Code 的 hook

toolkit 在 Claude Code 自動配合，不必手動：

- `tower-context.py`（SessionStart）：repo 有在飛航班就印一行摘要。
- `tower-track.py`：PreToolUse／UserPromptSubmit 更新心跳；PostToolUse（Edit、Write、MultiEdit）記錄改動，該檔首次與他班重疊時提醒。
- `tower-landing.py`（PreToolUse Bash）：預設分支上的 commit／merge／rebase，或 push 目標是預設分支前跑 land-check。10、12 直接 deny 並寫明解法；11 有人在場 ask、無人值守（航班 `mode=unattended` 或環境變數 `AGENT_DISPATCH_UNATTENDED=1`）deny 並要求排隊。

此 worktree 沒有 flying 航班、非 git repo、或任何例外，hook 一律靜默放行（fail-open）。

## 其他 CLI（Codex、agy、pi）

沒有這三支 hook：**不會自動追蹤改動、不會硬擋落地**。開工自己跑 `takeoff`，落地前自己跑 `land-check` 並照上表處理，回報寫明「此 CLI 沒有自動追蹤、沒有硬擋」。

## 已知限制

- `tower.yml` 只認頂層區塊式 `shared:` 清單；行內清單（`[a, b]`）與行尾註解不支援。
- `tower-landing.py` 的指令解析是字串近似：引號內的 `git commit` 字樣會誤判；`env`、`sudo`、`bash -c "..."`、`xargs` 包裝、`git pull`（會 merge）、`git cherry-pick` 不涵蓋。
- 在預設分支上以本 worktree 航班 merge／rebase 時，只有不指定 ref 或目標是 `origin/<預設>`、`<預設>`、`FETCH_HEAD`、`@{u}` 才視為同步（不擋「落後」「超出範圍」）；併入其他本地分支視為落地，連帶比對該分支帶進來的檔。
- 沒有 origin 的本地 repo 在預設分支上，已 commit 的改動不計入核對（只看工作區）。
- 以他班分支為目標落地時，該班 worktree 未 commit 的檔也計入，merge 實際帶不進來的檔可能造成誤擋，用 `override` 放行。
- 不核對：`git push --all`／`--mirror`、從 feature 分支裸 `git push`（upstream 設為 main）。
- 子 shell 內的 `cd` 會外洩到後續指令（不還原目錄），偏向多檢查。
- Codex 可能經 plugin 的 `hooks.json` 載入這些 hook，但未驗證。
- `beat`、改動追蹤的寫入沒有加鎖；同一航班被並行寫入時，後寫者可能蓋掉前者的 `touched`。
- 只管單機；跨機器、跨人的登記與 git 層硬擋不在範圍。
- 航班與 override 只記在本機登記表；land-check 內部出錯時只留警告、不擋落地。
