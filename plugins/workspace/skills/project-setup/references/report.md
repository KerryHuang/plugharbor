# 交付清單格式

最後一則回報固定三區塊，繁體中文。每列一項，不寫沒裝的東西。

## 1. 已安裝與已寫

| 項目 | 對應需求 | 來源 | 授權 | 進不進 git | 移除方式 | 驗證結果 |
|---|---|---|---|---|---|---|

- 項目：plugin、skill、`AGENTS.md`、`CLAUDE.md` 逐項一列。
- 對應需求：寫出是使用者哪句話或哪個 `signals`；對不上的不該出現。
- 來源：`plugharbor`、`<owner/name>@<commit>`（外部）、`自寫`。
- 授權：外部填 SPDX 名稱；plugharbor 與自寫填「—」。
- 進不進 git：依 `git_mode` 與實際 exclude 結果寫「進」或「不進（exclude）」；pi、Codex、agy 的本機路徑部分一律「不進」。
- 移除方式：照 `flow.md` 的移除表。
- 驗證結果：實際跑過的寫結果；沒跑的寫「未驗證」。pi 的專案 skill 在 Task 6 查證前寫「未驗證」。

## 2. 待你決定

外部候選帶 hook／MCP／腳本或授權不符（附原因）、`claude_md: custom`、既有檔案想改動、被 `skipped` 的同名項目。每項一行：是什麼、為什麼沒處理、選了會怎樣。沒有就寫「無」。

## 3. 換機器要重跑的指令

`shared`／`init` 時列出 `install-project.sh --no-claude <root> <plugins>`（用實際值）；再列 Claude 端 project scope 在新機器第一次開專案時需信任。`local` 模式列 `install-project.sh <root> <plugins>`。外部與自寫的檔案隨 repo 走，不用重跑。
