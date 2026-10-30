# CR 更新流程（調整模式共用邏輯）

所有 `--change` 模式 skill 均引用此 reference 的對應步驟。

---

## Step 0：Ticket 守門

解析 `$ARGUMENTS` 是否包含 ticket 編號（格式：`[A-Z]+-\d+`，例如 `ENG-132`、`PROJ-321`）：

**無 ticket 編號** → 以 `AskUserQuestion` 詢問：

> 偵測到 CR 模式但未提供 ticket 編號。
>
> 1. 是，協助我建立（呼叫 `sa-flow:linear-create`）
> 2. 我已有票號，讓我補上
> 3. 取消

- 選 1 → 派發 `sa-flow:linear-create`，建票完成後從回傳結果取得 ticket 編號，繼續 CR 流程
- 選 2 → 等待使用者輸入票號後繼續
- 選 3 → 終止

**有 ticket 編號** → 直接進入 Step 1。

---

## Step 1：主文件查找

依文件類型搜尋主文件（排除含 `_PM-`、`_功能調整` 的舊 CR 檔案）：

| 文件類型 | 搜尋模式 |
|---------|---------|
| FRD | `{docs-root}/**/{功能名稱}*_需求文件.md` |
| BFS | `{docs-root}/**/{功能名稱}*_後端功能規格書.md` |
| FFS | `{docs-root}/**/{功能名稱}*_前端功能規格書.md` |

**找到主文件** → 進入 Step 2。

**找不到主文件** → 從 codebase 反推（告知使用者後執行）：

| 文件類型 | 掃描範圍 |
|---------|---------|
| FRD | 舊版 CR 文件（`*功能調整需求文件*.md`）、git log、domain entity |
| BFS | API 路由／Controller、處理邏輯層（Handler／Service）、DB schema |
| FFS | 頁面元件、router config、API 呼叫點 |

掃描完成後，依對應 template（`frd.md` / `bfs.md` / `ffs.md`）撰寫 **v1.0 主文件**，changelog 第一列備註「從 codebase 反推建立」。寫完後繼續套用 CR 變更（v1.1）。

---

## Step 2：分析影響範圍

讀取主文件，對照 CR 描述，列出將被修改的段落（以 `§N 標題` 標示）。

- **小改動（≤ 2 個段落）** → 直接進入 Step 3 更新
- **大改動（> 2 個段落）** → **必須**使用 `AskUserQuestion`（不可用純文字 y/n prompt 模擬）：

  - **question**：「將修改以下段落，是否確認更新？\n- §X 章節名稱：說明\n- §Y 章節名稱：說明」
  - **header**：「確認更新」
  - **multiSelect**：false
  - **options**：
    1. `確認更新`
    2. `取消，不修改`

  選 `確認更新` 繼續；選 `取消` 則終止。

---

## Step 3：更新主文件

1. 使用 Edit 工具 in-place 修改對應段落（不刪除或重建檔案）。**取代不追加**：被本次異動取代的舊敘述必刪，不得在舊敘述旁追加新版本；回寫後正文淨增 >10% 要在功能目錄 `decisions.md` 記一列理由（規則見 `shared-preludes.md`「決策回寫的掃描義務」第 4 條）
2. 在 changelog 表格**最上方**（緊接 `<!-- CHANGELOG -->` 之後）插入一列：

   ```
   | v{X.Y} | [{ticket}](linear://{ticket}) | {today_date} | {修改摘要} |
   ```

   版本號規則：取現有最高版本號，次版本號 +1（如 v1.2 → v1.3）
3. Git commit（在所有文件更新完成後統一 commit）：
   ```
   docs({ticket}): 更新{功能名稱}{文件類型} - {修改摘要}
   ```

---

## Step 4：更新 Linear 票

使用 `mcp__linear__save_issue` 更新票的 description，寫入：

```markdown
## 本次規格變更

**修改摘要**：{摘要}

**主文件連結**：`{相對路徑}`（版本 v{X.Y}）

---

{本次 CR 影響的段落完整內容，依文件類型貼上對應章節}
```

---

## Changelog 區塊格式（主文件檔尾）

所有主文件（FRD/BFS/FFS）必須有此區塊；範本放在**檔尾**（附錄之後），舊文件仍在檔頭——工具一律靠 `<!-- CHANGELOG -->` 標記定位，不靠位置：

```markdown
<!-- CHANGELOG -->
| 版本 | Ticket | 日期 | 修改摘要 |
|------|--------|------|---------|
| v1.0 | 初版 | {建立日期} | 建立文件 |
<!-- /CHANGELOG -->

```

新增一列時插入在 `v1.0` 列**之上**（最新在最上方）。
