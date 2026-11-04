# SPEC-INDEX Format

Applies to FRD, SAD, BFS, FFS, their CR variants, and `_附錄_*.md` appendix files.
Writers produce the index from these rules; `verifying-specs` checks it.

## Full index

Place it after `§0 一頁摘要` and before `## 文件資訊`:

```markdown
<!-- SPEC-INDEX v1 -->
> **章節索引**（定向讀取用；章節異動時同批更新）
> - §0 一頁摘要 — 總覽圖、讀者導覽、關聯文件
> - §1 需求概述 — 功能目的、範圍、涉及 8 張表
> - §2 業務邏輯 — BR-001~019；核心＝子階展開與同批去重；§2.5 匯流圖與算例
> - §5 資料模型 — ORDER_HEAD／ORDER_LINE 等 8 表；Entity 定義在 §5.5
> - §6 API — 21 端點；報價單載入見 §6.15c、BOM 樹見 §6.14；明細見附錄檔 `_附錄_API契約明細.md`
> - §7 驗證規則 — VR-001~031（錯誤字串事實來源）
> - §D 決策紀錄 — 本階段 D-004~D-007（完整紀錄見 decisions.md）
```

Rules:

1. One chapter per line, formatted `§<number> <title> — <what the chapter holds>`.
   The title matches the `^## ` heading verbatim, including any parenthetical suffix: `## 3. 既有架構盤點（Codebase Snapshot）` indexes as `§3 既有架構盤點（Codebase Snapshot）`.
2. A chapter with a numbered series (US／BR／VR／IF／TC) states its number range.
3. A frequently queried sub-section gets a pointer at the end of its chapter line (`見 §6.15c`); a chapter split into an appendix file notes `明細見附錄檔`.
4. The index carries no line numbers; readers take lines from the outline or `grep -n`.
5. Adding or removing a chapter, or changing a number range, updates the index in the same batch.
6. After the document is written, run the chapter-number check below.
   Chapters added late (`## D. 決策紀錄`, `## M. Migration 規格`, `## 附錄`, `## 待澄清事項`) are the ones that miss the index.
   The check compares chapter numbers, because titles are polluted by sub-section pointers and combined lines, and counts can cancel out.

```bash
F=<spec file>
diff <(sed -n '/SPEC-INDEX/,/^---$/p' "$F" | sed -n 's/^> *- *§\([0-9A-Za-z]*\).*/\1/p' | sort -u) \
     <(grep -E '^## [^#]' "$F" | sed -E 's/^## +//' | sed -n 's/^\([0-9A-Za-z]\{1,\}\)\..*/\1/p' | sort -u)
grep -E '^## [^#]' "$F" | grep -vE '^## [0-9A-Za-z]+\.'   # unnumbered chapters
```

- The `diff` prints nothing.
  `<` is an indexed chapter that does not exist; `>` is a chapter missing from the index or merged into another line (`§12 … ｜ §13 …`), which breaks rule 1.
- The second command lists unnumbered chapters.
  Only these scaffolding headings stay out of the index: `文件資訊`／`版本資訊`／`文件歷程`／`CHANGELOG`／`變更紀錄`／`撰寫指南`.
  A content chapter such as `## 附錄` is indexed as `§附錄`.

## CR variant

CR-FRD／CR-BFS／CR-FFS documents are delta-only and usually under 20 KB, so they carry a one-line change summary under the same marker:

```markdown
<!-- SPEC-INDEX v1 -->
> **異動摘要**：{票號} — 影響 §{章節清單}；CVR-{起}~{迄}／CBR-{起}~{迄}
```

Tell the two shapes apart by the first `>` line after the marker:

- `> **章節索引**` — full index; the rule-6 check applies.
- `> **異動摘要**` — CR variant; the check is a subset match: every `§` listed in the summary exists as a `^## ` chapter.

A document carries exactly one shape; CR documents carry only the variant.

## Missing index

A spec without a SPEC-INDEX is read from its outline (or `grep -n "^## "`), choosing the chapter by heading.
The task report names the file as missing its SPEC-INDEX.

## Full-mode verification

`verifying-specs` in full mode reads chapter by chapter against the template's matching chapter (`sed -n '/^## 6\./,/^## /p' templates/bfs.md`); a whole-document comparison goes to a subagent that returns the gap list.

## `linear-create` source sections

Each ticket type reads only these chapters:

| Ticket type | Read |
|---|---|
| PM | FRD §0, §1, §2, §4 |
| SA | FRD §0; SAD §0, §1 |
| QA | FRD §2 (US and AC) |
| Dev backend | BFS §0, §5, §6, §7, §8 |
| Dev frontend | FFS §2, §3, §6 + BFS §6 endpoint overview |

`linear-ticket-defaults.md` has its own chapter index; read the index, then `sed -n '/^## {ticket type}/,/^## /p'` for that ticket type's template section.
