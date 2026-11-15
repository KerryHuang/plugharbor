# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.0] - 2026-11-15

起因：lifecycle 22 個 skill 兩週內實際只用到 7 個；只想要操作手冊或示範影片的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，delivery 是第三個拆出來的（tickets、discovery 之後）。

- 自 lifecycle 3.0.0 搬入：skills `operation-manual`、`demo-video`；agents `manual-explorer`、`manual-reviewer`、`manual-writer`；references `annotate-spec.md`、`anonymize-before-capture.md`；scripts `annotate.py`、`anonymize-page.js`、`build-deck.sh`、`build-manual-docx.sh`、`build-manual-pdf.py`、`check-deck-overflow.py`、`check-inventory-rects.py`、`ensure-tools.sh`、`make-docx-reference.py`、`manual_brand.py`、`manual-print.css`、`manual-reference.docx`、`prep-docx-cover.py`、`text-image-ratio.py` 與 `test_manual_brand.py`、`test_check_inventory_rects.py`。叫用名由 `lifecycle:<名稱>` 改為 `delivery:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。
- `annotate-spec.md`、`anonymize-before-capture.md`、`annotate.py`、`anonymize-page.js` 的 canonical 改為 delivery，browser-docs 的副本照舊。
