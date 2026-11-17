# 議程：README 第一段要不要更短（2026-11-17）

## 已結案（共識）
- D-1 第 1～6 行寫死的 plugin 數量（「14 個」「其餘 10 個」）→ 拿掉，數量看「外掛一覽」表。兩方 Confirmed（git log -L 兩週內改 4～5 次；validate.py:71-89、205-221 不檢查開頭）。
- D-2 第一段括號分類清單 → 刪掉。兩方 Confirmed（與 README.md:48-61 重複；abe335d 只改數字沒改括號）。

## 討論中
- D-3 第一段末句「Claude Code 直接走 marketplace，其他三個由 setup/install.sh 註冊與同步」
  - flow：保留，可縮成半句；是讀者選安裝路線的分岔點（README.md:10-22、agent-parity.md:9-12）。Confirmed
  - data：改寫或移走；過度簡化，install.sh 也管 Claude Code 的 user 層與 marketplace update（agent-parity.md:9）。Confirmed
- D-4 第二段（user 層／專案層分層）
  - flow：保留分層說明，只拿掉「10 個」；安裝指令靠這個分層才看得懂（README.md:20-21、33）。Confirmed
  - data：只留一句「分 user 層與專案層，細節見 setup/README.md」，不列名單；名單是第 4 份副本，權威在 setup/lib.sh:33。Confirmed
- D-5 定位句
  - flow：改寫，先講「公開的 Claude Code plugin marketplace」（AGENTS.md:3）；假設 README 主讀者是外部訪客。Likely
  - data：維持「唯一來源」定位句，它是價值主張。Confirmed（AGENTS.md:3-4）

## 備忘（不討論）
- README.md:38-40 新機器清單兩個「8.」。
- setup/README.md:12「其餘 7 個」已錯。
- AGENTS.md:4 也寫死「14 個 plugin」，D-1 落地時一起處理。
