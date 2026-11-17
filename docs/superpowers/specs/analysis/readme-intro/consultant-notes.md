# README 第一段要不要更短：顧問紀錄

## 雙顧問討論 2026-11-17（README 文案，pane）

| # | 爭點 | 輪數 | 結局 | 結論 | 關鍵證據 |
|---|------|------|------|------|---------|
| D-1 | 開頭寫死的 plugin 數量 | 0 | 共識 | 拿掉「14 個」「其餘 10 個」，數量看外掛一覽表 | `git log -L3,6:README.md` 兩週改 4～5 次；validate.py:71-89、205-221 不檢查開頭 |
| D-2 | 第一段括號分類清單 | 0 | 共識 | 刪掉 | 與 README.md:48-61 重複；abe335d 只改數字沒改括號 |
| D-3 | 末句「Claude Code 走 marketplace，其他三個走 install.sh」 | 1 | 共識 | 保留分岔點，改按「要不要 user 層設定」分 | README.md:10、16；setup/install.sh:2 |
| D-4 | 第二段要不要列 user 層名單 | 1 | 交使用者 → 保留名單 | 保留名單，只拿掉數量 | bb7ff3a 名單有同步、漂的是數字；外掛一覽表沒有「層」欄 |
| D-5 | 定位句 | 1 | 共識 | 先講「公開的 Claude Code plugin marketplace」，保留「唯一來源」（AGENTS.md:3 原句） | AGENTS.md:3；GitHub repo description |

已落地：README.md 第一、二段，AGENTS.md:4、setup/README.md:12 拿掉寫死的數字（2026-11-17）。

### 備忘（未討論）
- README.md:38-40 新機器清單有兩個「8.」（未修）。

### 延後清單
- `.claude-plugin/marketplace.json` 的 `metadata.description` 沒反映多 CLI 定位。
- GitHub repo description 與 README 第一句對齊（repo 外，validate 查不到）。

完整紀錄：`analysis/readme-intro/advisor-discussion/20261117/`
