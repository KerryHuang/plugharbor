# Changelog

格式：每次改動 `skills/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.2.0] - 2026-11-18

- feat(blog-capture)：新增第 5 步「交給寫文章的 session」：存好素材包後，用 `skills/blog-capture/scripts/find_blog_project.py` 從 Claude Code 記錄過的專案中，找出有 `.claude/rules/posts.md` 的寫文章專案（不寫死路徑）；有 toolkit 而且在 herdr／Herdr.app 內時，用 `toolkit:agent-dispatch` 在那裡開 claude worker 並送出交接 prompt；條件不符就照舊提醒。附 `test_find_blog_project.py`。frontmatter description 不變。起因：使用者 2026-11-18 收完素材後要求直接接到寫文章的專案開新 session，並說「未來要自動化，不要每次都要提醒一次」。
- chore：blog 改裝在 user 層（`setup/lib.sh` 的 `PH_USER_PLUGINS`），任何專案都能叫用 blog-capture。原本個人版 blog-capture 從 claude.ai 同步、每個專案都會載入；改成 user 層後，要停用 claude.ai 那份，常駐 description 才不會重複。

## [0.1.0] - 2026-10-30

- feat: 初版——`blog-capture`（收 blog 素材包到 Google Drive `blog-inbox/`）、`write-post`（定題、白話初稿、檢查、交稿）、`publish-check`（上線前檢查與驗證）。
- chore: 站台名稱、網址、目錄、frontmatter、作者標示與部署方式一律改為讀專案自己的規則，不內建任何站台資訊。
