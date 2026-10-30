# 設定分層：規則、skill、知識該落哪一層

每個 session 無條件進 context 的設定越多，越早觸發 context 劣化；放錯層則是「該讀的沒讀到」或「別人拿不到」。新增 skill／agent／rule 前先過這兩張表。

## 1. 落哪一層

| 這東西… | 落點 |
|---|---|
| 換到任何 repo 都成立，不提特定專案的結構、服務、連線 | **user 層**（`~/.claude/`），並放進可攜的版控來源 |
| 提到這個 repo 的目錄、子模組、環境、文件規範 | **專案層**（repo 的 `.claude/`） |
| 團隊其他人也要用 | **plugin**（marketplace） |

- 判準：**工具在 user，該 repo 怎麼用它在專案**。例：某個圖譜查詢 skill 在 user 層；本 repo 的圖譜檔在哪，由專案 rule 說。
- user 層的東西若只直接建在 `~/.claude`，等於只有這台機器有——要有版控來源與同步方式。
- 專案層若是私人 repo 或私人備份，團隊看不到；**團隊共用的慣例權威要放 plugin**，專案層只留一行指路。

## 2. 規則放哪裡

Claude Code 的 `rules/` 裡**沒有 `paths:` frontmatter 的檔每個 session 整份載入**（鏡像到其他工具時也一樣內嵌），所以：

| 這條規則 | 放哪 |
|---|---|
| 只在某個目錄下成立 | `rules/` ＋ `paths:` frontmatter（動到該路徑才載入） |
| 任何地方都可能觸發、不讀就出事（DDL、git、刪除、正式環境） | `rules/` 無 frontmatter，**只寫紅線** |
| 怎麼做、對照表、指令細節、事故史 | `refs/`（或 skill 的 `references/`），rule 留一行指路 |

- **不要把紅線只寫在 refs**：那裡沒人保證會被讀到。紅線一句話留在 rule，理由與細節放 refs。
- 事故史放 refs 而不是 rule：「為什麼」對判斷邊界有用，但不必每個 session 都付費載入。
- 定期量測無條件載入的總量（CLAUDE.md＋無 paths rules＋memory 索引＋skill description），超過就把程序與事故搬去 refs。

## 3. 權威只放一處

- 同一條規則只有一份權威文字，其他地方指路，不複製。複製的那份一定會在下次修改時漂移，而讀者不知道哪份是新的。
- 權威放在「需要它的人都拿得到」的那一層：團隊規則在 plugin、個人習慣在 user、repo 事實在專案。
- 發現兩處寫法衝突時，不默默挑一邊照做：指出衝突、問清楚，裁決後修掉錯的那一邊。
- 多工具（如 Claude Code 與 Codex）共用時，來源只有一份、其餘由腳本產生，見 `dual-tool-mirror`。
