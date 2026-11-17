## Domain Advisor（business-flow）— 第 1 輪回應

🔑 三個爭點我都讓步並修正了立場，沒有硬撐的。D-3、D-4 是對方的證據成立；D-5 改成兩句並存，用 `AGENTS.md:3` 的原句就能化解。

| 爭點 | 回應 | 我的現行立場 | 等級 | 新證據 |
|------|------|-------------|------|--------|
| D-3 末句「Claude Code 直接走 marketplace，其他三個由 install.sh 註冊與同步」 | 讓步 | 對方說得對，這句把責任邊界講錯了：install.sh 也會處理 Claude Code。不過讀者確實要在這裡選路線，所以我主張**改寫**，不搬走。改寫後的分岔點是「只要 Claude Code 的 plugin」對「整套」，不再按 CLI 分。如果對方堅持搬到「安裝」章節，我也可以接受，因為那一章第一屏就把兩條路都列了 | Confirmed | `setup/install.sh:2`：install.sh 負責「四個 CLI 的 plugin 註冊」，Claude Code 也在內。`README.md:10`（「自動偵測有裝的 CLI」）對照 `README.md:16`（「只想用 Claude Code 的 plugin、不要 user 層設定」）：讀者真正的分岔就是這兩條 |
| D-4 第二段的分層說明 | 讓步 | 我原本以為名單是讀懂安裝指令的前提，這個理由不成立。現在的立場是：保留分層的**規則**，因為這是業務規則；拿掉名單和數量，名單改連到 setup/README.md | Confirmed | `README.md:20-21`：兩行安裝指令行尾已經自帶「# user 層」「# 專案層」註解，讀者不需要名單也看得懂。`setup/lib.sh:32` 的註解本身就是這條規則（「工具類裝 user 層（每個專案都有），其餘是專案層，由 setup/install-project.sh 依專案安裝」），README 改寫這條規則，不再抄 `:33` 的名單 |
| D-5 定位句 | 讓步 | 不再要求拿掉「唯一來源」。改成要求在前面加上 marketplace 身分，也就是直接用 `AGENTS.md:3` 的原句：「公開的 Claude Code plugin marketplace，也是……唯一來源」。對方說的價值主張和我說的外部讀者身分都保住了，也不用新造一句再多一份副本 | 外部讀者存在：Confirmed／誰是主要讀者：仍是 Unknown | `README.md:16-22` 專門為外部的 Claude Code 使用者設計了一條「不要 user 層設定」的安裝路線；`LICENSE:1` 是 MIT，開放外部重用。這兩點證明外部讀者是設計中的場景，不再只是我的假設。但外部讀者和自用哪個是**主要**讀者，證據還是判斷不了 |

### 延後（不展開）
- `.claude-plugin/marketplace.json` 的 `metadata.description` 寫的是「KerryHuang Claude Code plugins」，沒有反映多 CLI 共用的定位，跟這次的 README 議題無關。
- 第二段改成連到 setup/README.md 之後，讀者第一個會讀到的就是 `setup/README.md:12` 寫錯的「其餘 7 個」。D-1 落地時要一起修，不然等於把讀者帶到錯的地方。

### 需使用者裁決
- 主要讀者是外部訪客還是自用：用 `AGENTS.md:3` 的原句可以兩邊都照顧，這題不一定要裁。只有在想把第一句再砍短、二者擇一時才需要決定。

### 我可接受的第一段草稿

> 公開的 Claude Code plugin marketplace，也是 Claude Code、Codex、pi、agy 共用的 AI 工作模式唯一來源：plugin 加上 user 層設定（`setup/`）。只要 Claude Code 的 plugin 就走 marketplace；要整套（含 user 層設定與其他 CLI）就跑 `setup/install.sh`。
>
> plugin 分兩層：工具類裝在 user 層，每個專案都有；其餘依專案用 `setup/install-project.sh` 安裝。名單見 [setup/README.md](./setup/README.md)。

這份草稿沒有數字、沒有分類清單、沒有名單（落實 D-1、D-2、D-4），各 CLI 怎麼安裝也沒寫錯（D-3）。這一輪沒有改任何檔案。

⏳ 等主持人整理第 1 輪，再交給 data 視角回應。