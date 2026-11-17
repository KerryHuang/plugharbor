## Domain Advisor（data-boundary）— 爭點提案

🔑 我主張縮短第一段，理由是資料的權威來源不在這裡，跟篇幅本身無關。第一段手抄了三份事實：plugin 數量、分類清單、各 CLI 由誰安裝。這些事實的權威來源都在別處，也沒有任何機械檢查。過去兩週 plugin 數量改了 4 次，每次都靠人工同步，而且已經有一份副本漂掉了。

一共 5 個爭點、4 條備忘。

| # | 爭點 | 我的立場 | 等級 | 證據 | 校準條 |
|---|------|---------|------|------|-------|
| P-1 | 第 1～6 行的數量「14 個」「其餘 10 個」是手抄副本，沒有檢查擋著 | **縮短**：第一段拿掉數字，改指向「外掛一覽」表。表的版本欄有 validate 檢查，表格本身就是清單 | Confirmed | 權威來源是 `.claude-plugin/marketplace.json`（14 筆）。`validate.py:71-89` 只比對版本表，`validate.py:205-221` 只比對「skills 與 agents」表，都不檢查開頭的數字。`git log -L3,6:README.md` 顯示 6abae47 → bb7ff3a → abe335d 依序是 14→13→11→14，每次重構都得手改 | 1（有證據會再出錯） |
| P-2 | 第一段括號裡的分類（工作流、職責＋技術棧附錄、hooks、guard、reviewer、寫作、研究、UI 規範）已經和實際 plugin 對不上 | **刪掉括號**，或換成一句不會跟著增減 plugin 而過期的定位。目前沒有涵蓋到的有：workspace（git 與工作區）、delivery（交付文件）、browser-docs（瀏覽器與轉檔） | Confirmed | `README.md:3` 對照 `README.md:48-61` 外掛一覽。abe335d 拆出 tickets、discovery、delivery 時只改了數字，沒改括號（`git show abe335d -- README.md`） | 1 |
| P-3 | 「Claude Code 直接走 marketplace，其他三個由 install.sh 註冊與同步」把責任邊界講得太簡化 | **改寫或移走**：install.sh 也負責 Claude Code 的 user 層設定（複製 CLAUDE.md、shared、rules），還會自動執行 marketplace update。這句的細節本來就由 `docs/agent-parity.md` 負責，開頭只要一句連結 | Confirmed | `docs/agent-parity.md:9`（Claude Code 一列寫著「install.sh 複製」「install.sh 版號不同時自動做」） | 3（和既有行為衝突） |
| P-4 | 第二段的 user 層清單是第 4 份副本 | **縮短**：第二段只保留「分 user 層與專案層，細節見 setup/README.md」，不再列名單和數量 | Confirmed | 權威來源是 `setup/lib.sh:33`（`PH_USER_PLUGINS`）。副本還有 `setup/README.md:11`、`docs/agent-parity.md:87`、`README.md:6`、`README.md:32`（「4 個」）。其中 setup/README 有標明出處（lib.sh），可以保留當唯一說明處 | 1 |
| P-5 | 「唯一來源」的定位句和 `AGENTS.md:3-4` 重複，AGENTS.md 另外也寫了「14 個 plugin」 | **維持**定位句，它是給讀者的價值主張，這段應該留。但數字一旦從 README 拿掉，AGENTS.md:4 的「14 個」也要一起處理（AGENTS.md「副本一起改」） | Confirmed | `AGENTS.md:3-4`、`AGENTS.md`「改動原則・副本一起改」 | 1 |

### 備忘（不展開討論）
- `README.md` 新機器清單有兩個「8.」，Codex 和開發機兩項的編號重複了（大約在第 38～40 行）。這和議題無關，順手提出來。
- 如果決定保留數字，替代做法是在 validate.py 加一條檢查，比對開頭數字和 marketplace.json 的筆數。這比縮短多一份維護成本，所以不推薦。
- 開頭段落適不適合新讀者、資訊順序怎麼排，屬於 business-flow 視角，我這裡不判斷。
- 第 3 行「hooks、guard、reviewer」三個詞其實都指 toolkit 一個 plugin，分類的粒度不一致。這點併入 P-2 處理。

### 需使用者裁決
- 第一段拿掉數字和分類之後，這個 repo 的定位要強調什麼：「多 CLI 共用」還是「marketplace」？兩者都有依據（`AGENTS.md:3` 兩個都寫了），用證據決定不了，屬於品牌取捨。

已完成：照 data-boundary 視角蒐證，交出 5 個爭點，沒有改任何檔案。
下一步：等主持人把這份和 business-flow 視角的提案合併，進入 discuss-reply 第 1 輪。
待決：上面那題定位取捨，交給使用者裁決。

⏳ 現在等主持人進行下一輪雙顧問討論。