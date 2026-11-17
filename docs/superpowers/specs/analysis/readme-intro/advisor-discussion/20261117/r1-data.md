## Domain Advisor（data-boundary）— 第 1 輪回應

🔑 這一輪我在 D-4 讓步。D-3 和 D-5 部分讓步，各補一條新證據。我判斷三個爭點都能收斂：保留分歧點但照實際邊界重寫，分層名單保留，定位句的語序照 flow 視角的寫法，但「唯一來源」四個字要留著。

| 爭點 | 回應 | 我的現行立場 | 等級 | 新證據 |
|------|------|-------------|------|--------|
| D-3 末句「Claude Code 直接走 marketplace，其他三個由 install.sh 註冊與同步」 | **讓步，但補證據反駁原句的寫法**。我接受 flow 視角說的「這裡是選安裝路線的分歧點，該留在第一段」，但原句切錯了邊界，不能原樣縮成半句 | 保留成一句分歧點，照 README 自己的兩條路線改寫：「只要 Claude Code 的 plugin → marketplace；要 user 層設定或用其他 CLI → `setup/install.sh`」 | Confirmed | `README.md:10` 寫 bootstrap 會跑 install.sh 並「自動偵測有裝的 CLI」，Claude Code 也包含在內。`README.md:16` 另一條路寫的是「只想用 Claude Code 的 plugin、不要 user 層設定」。可見實際的分界是「要不要 user 層設定」，不是「Claude Code 還是其他三個 CLI」。原句會讓 Claude Code 使用者以為不用跑 install.sh，跟 `README.md:10`、`:16` 衝突（校準第 3 條） |
| D-4 第二段分層 | **讓步** | 保留分層說明和 user 層名單，只拿掉「其餘 10 個」。不加「細節見 setup/README.md」也可以 | Confirmed | `README.md:46-61` 的外掛一覽表沒有「層」這一欄，名單拿掉後讀者就查不到 workspace 為什麼是 user 層（`README.md:20`）。名單本身漂得比數字慢：`git show bb7ff3a -- README.md` 移除 dev-flow 時名單有跟著改，壞掉的都是數字（`setup/README.md:12` 寫「其餘 7 個」）。所以真正該處理的副本風險是數字，名單可以留 |
| D-5 定位句 | **部分讓步** | 語序照 flow 視角，先講「公開的 Claude Code plugin marketplace」。「唯一來源」要留在同一句：它說明了 Source of Truth 的邊界，是其他 CLI 為什麼從這裡同步的依據（`docs/agent-parity.md:10-12`，三者都是從本 repo 快照安裝） | 語序：Confirmed／讀者是誰：Likely | GitHub repo description 是「AI agent 工作模式的 plugin marketplace：Claude Code、Codex、pi、agy 共用」（`gh repo view`），對外門面本來就把 marketplace 放最前面，支持 flow 視角的語序。另一方面，stars 0、forks 0，commit 幾乎都出自同一位作者（`git log` 303 筆），所以「主要讀者是外部訪客」只到 Likely。我原本給的 Confirmed（AGENTS.md:3-4）只證明自述裡有這個說法，證明不了它是價值主張，降為 Likely |

### 延後（不展開）
- `setup/README.md:12` 的「其餘 7 個」要改成不寫數字，跟 D-1 一起處理。這條已在議程備忘裡。
- GitHub repo description 跟 README 第一句應該保持一致。它不在 repo 內，validate 檢查不到，等落地時順手對齊。

### 需使用者裁決
- 主讀者是外部訪客，還是自己和 agent？證據只到 Likely：0 star、作者只有一位。這會決定第一句要不要再把「唯一來源」往後放。我上面的草稿是兩者兼顧的折衷寫法。

### 我可接受的第一段草稿

> 公開的 Claude Code plugin marketplace，也是 Claude Code、Codex、pi、agy 共用的 AI 工作模式唯一來源：plugin 加上 user 層設定（`setup/`）。只要 Claude Code 的 plugin 就走 marketplace；要 user 層設定或用其他 CLI，跑 `setup/install.sh`（各 CLI 差異見 [docs/agent-parity.md](./docs/agent-parity.md)）。
>
> plugin 分兩層：工具類（toolkit、research、browser-docs、workspace）裝在 user 層，每個專案都有；其餘是專案層，用 `setup/install-project.sh` 依專案安裝。

這一輪沒有改任何檔案。
已完成：D-3、D-4、D-5 都已回應，附上草稿。
下一步：主持人比對兩邊的回應，判斷要結案還是進第 2 輪。
待決：主讀者是誰，交使用者裁決。

⏳ 等主持人進行下一輪。