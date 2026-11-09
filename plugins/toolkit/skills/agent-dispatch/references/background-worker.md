# 沒有 herdr 時的長任務：Ghostty 分割與背景 worker

`scripts/bg.mjs` 負責這兩層。偵測順序見 SKILL.md「長任務」：herdr → Ghostty 分割 → 背景 worker。

## Ghostty 分割（看得見、可互動）

條件：macOS、目前在 Ghostty 裡（`TERM_PROGRAM=ghostty`），Ghostty 1.4 以上（有 AppleScript 字典）。
第一次執行時 macOS 會問要不要允許終端機控制 Ghostty（自動化權限），要同意。

```bash
# 開分割：在 <cwd> 執行 <指令>，印出新分割的 id
node "${CLAUDE_SKILL_DIR}/scripts/bg.mjs" ghostty-split --cwd "<cwd>" "<指令>"
# 收工：用 id 關掉（指令結束後分割不會自己關）
node "${CLAUDE_SKILL_DIR}/scripts/bg.mjs" ghostty-close <id>
```

- `<指令>` 用該 CLI 的互動模式帶初始 prompt，例如 `claude "$(cat <prompt 檔>)"`，讓使用者看得到、必要時能直接在分割裡回答。
- 分割內不設 `AGENT_DISPATCH_RESULT`：互動 worker 有人在場，Stop hook 若在它每次想問人時擋下，它可能寫出「待決」的結果檔被當成完成。
- 完成的證據是結果檔存在。主控不輪詢：Claude worker 寫完結果檔後用 SendMessage 回報；其他 CLI 的 worker 由使用者看到分割結束後告知，或主控用阻塞方式等結果檔。

### Spike 結論（2026-11-04，macOS，Ghostty 1.4.0）

- `ghostty` CLI 的 `+new-window` 在 macOS 不支援，keybind action（`new_split`）也不能從外部觸發。
- Ghostty 的 AppleScript 字典（`Ghostty.app/Contents/Resources/Ghostty.sdef`）有 `split` 指令，可以帶 `surface configuration`，裡面可設 `command`、`initial working directory`、`environment variables`。實測：
  - 在目前視窗開出右側分割。
  - 指令在指定目錄執行，環境變數（含空白的路徑）有正確傳進去。
  - 用 `close (first terminal … whose id is …)` 可以關掉。
- `wait after command` 設 false 時，指令結束後分割仍然留著，所以收工一定要明確關閉。
- 結論：可行，保留這一層。只支援 macOS；Linux 與 Windows 直接跳到背景 worker。

## 背景 worker（看不見、不能中途問人）

只在下面條件都成立時才用：

- 工作不需要中途問人。遇到要決策就停下來，寫進結果檔。
- 只在獨立 git worktree 裡改檔，不改主線、不 push。
- 主控合併前由使用者審過。

```bash
node "${CLAUDE_SKILL_DIR}/scripts/bg.mjs" start --repo <repo> --name <短名> --to <cli> \
  [--model <模型>] [--effort <等級>] [--timeout <秒，預設 3600>] --ws <工作目錄> <prompt 檔>
node "${CLAUDE_SKILL_DIR}/scripts/bg.mjs" status --ws <工作目錄>   # 只讀，不等待
node "${CLAUDE_SKILL_DIR}/scripts/bg.mjs" wait --ws <工作目錄> [--timeout <秒>]   # 阻塞到結束；done→0、逾時→124、其他→1
```

- `--ws` 是這個 worker 專用的工作目錄。多個 worker 放在同一個上層目錄下，並行上限以那一層計算；放在不同上層目錄的 worker 互相不計。`start` 用那一層的 `.agent-dispatch.lock` 目錄當鎖，避免同時 start 都通過上限檢查；鎖超過 60 秒沒釋放視為過期。
- `--timeout` 要是正數；參數或 prompt 檔有問題時在建 worktree 之前就報錯，不留孤兒分支。
- 工作目錄內容：
  - `wt/`：worktree，分支 `dispatch/<短名>`。
  - `job.json`：派工設定。
  - `status.json`：狀態，`running`／`done`／`failed`／`quota`。監督程序已不在卻仍寫 running 時，`status`／`wait` 顯示 `failed`（`note: supervisor gone`）；超過 `startedAt`＋timeout＋60 秒仍是 running（pid 被重用）也顯示 `failed`（`note: stale…`）。
  - `result.md`：worker 寫的結果。
  - `log.txt`：CLI 的完整輸出。
- 並行上限：
  - 預設 4（`routing.json` 的 `maxParallel`）。
  - 遇到額度用盡或逾時就降 1，最低 1，寫進狀態檔（`maxParallel`、`parallelResetAt`）。
  - 1 小時後自動恢復成路由表的值；要提早恢復就刪掉狀態檔裡這兩個欄位。
- 結束時：
  - 結果檔在 → `done`（不論輸出內容）。
  - 沒寫結果檔、輸出尾段是額度錯誤 → `quota`，同時封鎖該家。
  - 其他 → `failed`，並附輸出最後 2000 字元；監督程序本身出錯也寫 `failed` 與 `error`。
  - 最終狀態先寫，再改共用狀態檔（封鎖、降並行）；後者失敗只在 `status.json` 加 `stateError`，不改變最終狀態。
- CLI 參數用 `worker` 模式：claude `--permission-mode acceptEdits --allowedTools Bash`、pi `--tools read,bash,edit,write`，codex／agy 同 driver。
- **信任模型、不是沙箱**：上面的權限讓 worker 能跑任意 shell，「只改 worktree、不 push、不動主線」主要靠 prompt。腳本另有兩道防線，都只對 worker 程序生效、不寫進 repo 設定：
  - 不傳推送用 token：`GH_TOKEN`、`GITHUB_TOKEN`、`GH_ENTERPRISE_TOKEN`、`GITHUB_ENTERPRISE_TOKEN`、`GITLAB_TOKEN`、`GLAB_TOKEN`。確定要傳就設 `AGENT_DISPATCH_KEEP_ENV=名1,名2`。
  - 用 `GIT_CONFIG_COUNT`／`KEY`／`VALUE` 設 `protocol.allow=never`（含 file、git、ssh、http、https、ext 各自的 `protocol.<名>.allow`）：git 的 push 與 fetch 都會失敗，remote 明設 `pushurl` 也一樣。worker 需要 fetch 的工作不要用背景 worker。
  - 擋不住的：worker 自己清掉這些環境變數，或繞過 git 推送（如 `gh` 用 keychain 裡的登入、`curl` 打 API）。需要硬隔離就改用容器或另一個帳號。
- macOS 會跳桌面通知。其他平台沒有通知，主控用 `bg.mjs wait` 阻塞等結束。
- 收工：
  1. 使用者審 `wt/` 的改動。
  2. 由主控合併。
  3. `git worktree remove <ws>/wt`，刪除分支 `dispatch/<短名>`。
  4. 刪除工作目錄。
- Windows（Git Bash）：用 node 的 detached spawn，不依賴 shell 背景工作。實機驗證見 CHANGELOG。

## macOS 防睡眠（herdr pane 與背景 worker 都適用）

- 長任務期間不要蓋上螢幕。蓋上會進 Clamshell Sleep，`caffeinate` 用什麼旗標都擋不住；它只擋閒置睡眠（`-i`），`-s` 也只在接電源時有效。
- 一定要蓋螢幕，就接電源並接外接螢幕（closed-display mode）。
- `sudo pmset disablesleep 1` 是系統設定，由使用者自己決定要不要開，agent 不代為執行。
- 懷疑睡過頭：`pmset -g log | grep -iE "sleep|wake"` 看睡眠原因（Clamshell、Idle、Low Power）。
