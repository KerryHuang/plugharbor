## Domain Advisor（business-flow）— 爭點提案
核心結論：第一段該縮短，但最該砍的是寫死的數量和括號裡的分類清單，不是句子長度。這兩處已經跟不上 repo 了，數量甚至在別的檔案錯了。共 5 個爭點、6 條備忘。

| # | 爭點 | 我的立場 | 等級 | 證據 | 校準條 |
|---|------|---------|------|------|-------|
| P-1 | 第一段的「14 個」和第二段的「其餘 10 個」是寫死的 plugin 數量 | **縮短**：兩段都拿掉數字，要看數量去「外掛一覽」表。除非改成讓 validate.py 檢查這個數字 | Confirmed | `git log -L1,6:README.md`：這兩個數字兩週內改了 5 次（abe335d、bb7ff3a、6abae47、73bfca3、110853a），每次拆或併 plugin 都得手改。`setup/README.md:12` 還寫「其餘 7 個」，已經和 `README.md:6` 的 10 個對不上。`scripts/ci/validate.py:71-89`、`:205-221` 只檢查版本欄和「skills 與 agents」表，沒檢查開頭的數字 | 1 |
| P-2 | 括號裡的分類（工作流、職責＋技術棧附錄、hooks、guard、reviewer、寫作、研究、UI 規範） | **刪掉括號**：跟 `README.md:44-61`「外掛一覽」重複，而且 abe335d 拆出票務、需求會議、交付三個 plugin 時只改了數字，分類沒跟著更新 | 重複：Confirmed／過時：Likely | abe335d 的 diff 只把 11 改成 14，括號一字沒動。「票務、需求、交付」要不要算進「工作流」，看讀者怎麼理解，所以「過時」只給到 Likely | 1 |
| P-3 | 第一句沒說這個 repo「是什麼」。公開的訪客先讀到的是「所有 AI 工作模式的唯一來源」這種自用說法 | **改寫**，改成先講身分再講用途。例如：「公開的 Claude Code plugin marketplace，也是 Claude Code、Codex、pi、agy 共用的 AI 工作模式來源：plugin 加上 user 層設定（`setup/`）。」 | Likely | `AGENTS.md:3` 自述的第一句就是「公開的 Claude Code plugin marketplace」，README 沒有這句。我假設 README 的主要讀者是外部訪客、AGENTS.md 是給 agent 看的，這個假設要使用者確認 | 2 |
| P-4 | 第一段最後一句「Claude Code 直接走 marketplace，其他三個由 `setup/install.sh` 註冊與同步」 | **保留，可以縮成半句**。這句是讀者選哪條安裝路線的分岔點，跟 `README.md:10`、`:16` 的兩條安裝路徑一一對應，刪了讀者到安裝章節才知道要選哪條 | Confirmed | `README.md:10-22`；`docs/agent-parity.md:9-12` 的「更新方式」欄 | 2 |
| P-5 | 第二段（user 層和專案層分層） | **保留，只拿掉「10 個」**。後面的安裝指令都靠這個分層才看得懂：`--scope local` 在 `README.md:21`，專案層安裝在 `:33`。刪掉的話，讀者不知道為什麼 workspace 和 lifecycle 裝法不同 | Confirmed | `README.md:20-21`、`:33`；`setup/README.md:9-12` | 3 |

### 備忘（不討論）
- `README.md:39-40` 新機器清單有兩個「8.」，編號重複，跟這次的議題無關。
- `setup/README.md:12` 的「其餘 7 個」本身就是錯的，不論 README 縮不縮都要修。這屬於另一個視角（data-boundary，管數量由哪裡說了算）的問題，我只提一行。
- `AGENTS.md:4` 也寫死「14 個 plugin」。第一段如果拿掉數字，這裡要一起拿或一起留（AGENTS.md「副本一起改」那條）。
- 「典型動線」（`README.md:82-88`）已經涵蓋各 plugin 的分工，P-2 刪掉括號不會讓讀者少了資訊。
- 改 README 不碰 `skills/` 等目錄，不需要 bump 版號。validate.py 只檢查表格，改開頭兩段不會讓它失敗。
- 這幾點都不涉及偏離舊系統的通用預設。

### 需使用者裁決
- **README 主要給誰看**：外部訪客（第一句先講「公開 marketplace」，P-3 成立），還是自己和 agent（維持「唯一來源」的自用說法，P-3 撤回）。證據回答不了這個取捨。
- **數字要拿掉還是讓 CI 檢查**：拿掉最省事（P-1 的建議）。如果認為數量對讀者有價值，就要在 validate.py 加一條檢查，比對 README、AGENTS.md、setup/README 三處的數量和 marketplace.json。這要寫程式，依 AGENTS.md「要有起因」那條，`setup/README.md:12` 數字對不上可以當起因。