# 回饋佇列轉交的三項 plugin 摩擦（2026-11-23）

**結論**：上一版 7 條待驗指標都還沒到期；這次有 3 個根因，其中 P0 一項、P1 一項、P2 一項；新增 3 條待驗指標。

來源：`/feedback-review` 2026-11-23 轉交，使用者已核准交給本 skill。三條在跨單位搜尋裡都只出現 1 次（只查本機佇列歸檔 86 筆、記憶、CHANGELOG、formwright 帳本）。無量化數據。

## Step 0 上一版驗證

M-20261113-01／02（到期日 11-27）、M-20261117-01／02（12-08）、M-20261123-01～03（12-14）都還沒到期，各追加一筆 not-due。

## 根因

### R1｜P0｜unattended 第 7 步自相矛盾（skill 內容）

- 證據：佇列 20261119063549-c5e92a（formwright）。主控 rebase 已經 push 過的功能分支之後，用 `--force-with-lease` 推了上去，違反 git-safety。
- 根因：`workspace/skills/unattended/SKILL.md:47` 同時要求「落後就先 rebase」與「不 force push」，但沒寫 rebase 之後要推到哪裡。已推過的分支一旦落後，只能二選一違規。
- 為什麼一次就改：這是文字本身的矛盾，不是偶發失誤，只要已推過的分支落後就一定會再犯。而且違規的是破壞性操作。
- 改法（改寫既有句，不新增）：rebase 後只用 fast-forward 推預設分支；rebase 過的功能分支不推回同名遠端分支。

### R2｜P1｜hc spawn 的 worker 拿不到 MCP 設定要用的環境變數（流程）

- 證據：佇列 20261120090428-e08e5f（公司專案）。`.mcp.json` 引用的 `${TOOL_MCP}` 只寫在 `~/.zshenv`。`hc run` 用的是 core 的環境，不是呼叫者的，所以 worker 啟動 MCP 時 ENOENT：一張票的檢查靜默略過，另一張停下。
- 根因：`toolkit/skills/agent-dispatch/scripts/mux.py` 的 `spawn` 只會清掉污染變數，不會補上 cwd 的 `.mcp.json` 需要的變數。
- 為什麼一次就改：凡是 `.mcp.json` 用 `${VAR}`、變數又只寫在 shell rc 的專案，每次派 worker 都會壞，而且會靜默略過檢查。
- 改法：`dispatch()` 的 spawn 讀 `<cwd>/.mcp.json`，裡面引用的 `${VAR}` 若存在於呼叫者環境、又沒有用 `--env` 指定，就自動帶過去。hc 與 herdr 兩個後端都適用。另補 1 個測試。

### R3｜P2｜派設計初稿漏附已確認的答案（流程）

- 證據：佇列 20261121132525-526508（formwright）。初稿有 5 題跟已確認的答案相反、9 處漏寫，被 domain-advisor 分流攔下。
- 判斷：user 層 `dispatch.md` 已經寫了「派工 prompt 自帶已拍板決定」，安全網也有作用；只發生 1 次，屬偶發。**這次不改 plugin**，先觀察；再發生一次就改寫 unattended 第 0 步，讓派初稿時指名附上答案檔。

## 轉交

無。三項都屬 plugin，R3 暫不動。

## 本次的待驗指標

| id | 指標 | 判準 | 到期 |
|---|---|---|---|
| M-20261123-04 | unattended 不再 force push | R1 上線後，佇列出現 unattended 對功能分支 force push，或「rebase 與不 force push 衝突」的筆數＝0 | 2026-12-21 |
| M-20261123-05 | worker 的 MCP 環境變數 | R2 發版後，佇列出現 mux spawn 的 worker 缺環境變數、MCP ENOENT 的筆數＝0 | 2026-12-21 |
| M-20261123-06 | 派工附上已確認的答案 | 佇列出現「派工漏附已確認決定，產出與答案相反」的筆數＝0 | 2026-12-21 |
