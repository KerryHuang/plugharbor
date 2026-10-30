# 落地與 git 流程

## HTML 放 docs，不放筆記服務

**多數筆記／Wiki 服務預設過濾 `<script>`**——可點數字的抽屜會整個失效，
而那正是這份簡報一半的價值。要它能跑得關掉整站的 sanitize，為一份報表不值得。

HTML 放進專案 docs 可行，需先確認：

| 事實 | 確認方式 |
|------|----------|
| docs 站台是否把非 markdown 檔原樣複製進產出 | 看站台設定（如 MkDocs 的 `docs_dir`）與既有的 `*.html` 先例 |
| 是否有 CI 自動部署 | 看 CI 設定；有則 push 到主分支即部署 |
| 分支流程 | 依專案慣例（docs 常直接在主分支改） |

## 路徑與導覽

```
{docs-root}/{週會簡報目錄}/{週會日}.html
```

`{docs-root}` 取自專案 CLAUDE.md 的 `sdlc-docs-path`，**不要硬編 `docs/`**。
`{週會簡報目錄}` 取自專案 docs 既有的第一階目錄，**禁止自創**；沒有適合的就問使用者。
命名用**會議日**，與兩份 Linear 文件同一套，三邊對得起來。

- **不要加進站台導覽清單**——不列的目錄通常仍會 build、網址打得開，
  只是不出現在左側導覽。週報因此可以連、但不混進規格樹。
- **不要用站台的 `exclude` 類設定排除**——那是把檔案排出 build，排掉就沒網址。

## 知識圖譜工具界線

若專案用知識圖譜工具（如 Graphify）掃 docs：這類工具通常只吃 `.md`／`.txt`／`.pdf`／圖片，
`.html` 天生不進圖譜。**週會簡報目錄只放 `.html`**——放任何 `.md` 都會被吸進圖譜，
且多半沒有可事後補救的 ignore 機制。依專案的 docs 慣例規則檔為準。

## 發布前必驗

1. **數字↔清單一致性**（見 SKILL.md Step 6），不一致不得發布
2. **站台收錄驗證**（僅在 docs 有靜態站台建置時）：本地 build 後確認
   - 產出中簡報 `.html` 存在
   - 與來源 `cmp` 位元相同（確認 JS 與內嵌資料沒被處理掉）
   - 首頁導覽未出現該目錄（沒誤入導覽）

## git

- **docs 是獨立 repo 時**：`git -C <docs>` 逐檔指名 add → `git status` 複驗 staged 只含本次檔案 → commit → push
- **docs 是 submodule 時，主 repo**：只 commit submodule pointer bump。
  ⚠ 若設了 `submodule.<name>.ignore = all`，`git status` **看不到 pointer 漂移**，
  要用 `git status --ignore-submodules=none` 或比對
  `git ls-tree HEAD <docs>` vs `git -C <docs> rev-parse HEAD`
- 多 agent 並行時，**其他 submodule 的漂移不要包進自己的 commit**
- push 主 repo 前先取得使用者同意
