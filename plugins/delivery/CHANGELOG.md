# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.1.0] - 2026-11-16

起因：demo-video 第一次實戰（兩支影片）的摩擦集中在起站與重置、選擇器試錯、操作超時三處。設計見 `docs/superpowers/specs/2026-11-16-demo-video-optimization-design.md`。

- 錄影環境配方 `video/env.mjs`：引擎自動 build、reset、自選空埠、驗證聽埠的程序是自己起的才算就緒、只關自己的程序（POSIX 用 process group）；新增 `env-check` 指令；預設目錄由 `.tmp/demo-video/` 改為進版控的 `video/`；`ensure-tools.sh` 檢查 gitignore；有配方時先拿鎖再配音，同一支影片同時 build 第二個直接被拒；引擎崩潰或收到 SIGHUP 也會收掉 detached 的 server 與鎖檔。
- 新增 `dry-run`（不配音不錄影，印每段語音估計與操作秒數；失敗印可互動元素清單）與配音快取（`video/.tts-cache/`；`--base` 模式在 `video/<名稱>/.tts-cache/`）。
- 操作員新增 `a.upload`、`a.select`、`a.as`；每段可寫 `expect`；contact sheet 改抓操作完成那一刻；`base` 改為選填。
- 回報分開寫成片長度與製作時間；配音來源與授權寫進 MP4 metadata，未確認授權時提醒對外發布前要確認。
- 範例 `examples/leave-request` 的 `run.sh` 改為 `examples/env.mjs`＋`serve.mjs`；SKILL 與 references 同步更新。

## [1.0.1] - 2026-11-16

起因：lifecycle 4.1.0 把設計文件改成新章節格式（設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第三批），本 plugin 的共用 references 副本跟著改讀新章節。

**改動**

- `references/` 共用副本（config、shared-preludes、shared-preludes-details、analysis-rigor、consultant-desk、legacy-parity）改讀新章節，舊章節以「（舊範本 §n）」括號別名保留。

## [1.0.0] - 2026-11-15

起因：lifecycle 22 個 skill 兩週內實際只用到 7 個；只想要操作手冊或示範影片的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，delivery 是第三個拆出來的（tickets、discovery 之後）。

- 自 lifecycle 3.0.0 搬入：skills `operation-manual`、`demo-video`；agents `manual-explorer`、`manual-reviewer`、`manual-writer`；references `annotate-spec.md`、`anonymize-before-capture.md`；scripts `annotate.py`、`anonymize-page.js`、`build-deck.sh`、`build-manual-docx.sh`、`build-manual-pdf.py`、`check-deck-overflow.py`、`check-inventory-rects.py`、`ensure-tools.sh`、`make-docx-reference.py`、`manual_brand.py`、`manual-print.css`、`manual-reference.docx`、`prep-docx-cover.py`、`text-image-ratio.py` 與 `test_manual_brand.py`、`test_check_inventory_rects.py`。叫用名由 `lifecycle:<名稱>` 改為 `delivery:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。
- `annotate-spec.md`、`anonymize-before-capture.md`、`annotate.py`、`anonymize-page.js` 的 canonical 改為 delivery，browser-docs 的副本照舊。
