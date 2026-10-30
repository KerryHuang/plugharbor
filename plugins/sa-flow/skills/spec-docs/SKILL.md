---
name: spec-docs
description: "Use when a task reads, searches, or edits an SDLC spec document (FRD, SAD, BFS, FFS, CR variants, FoxPro analysis reports, decisions) in the docs repository, or when another sa-flow skill or agent needs a spec section."
---

# Spec Docs — Read and Write Spec Documents

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

Spec documents are read by **section**, never whole. A BFS runs 60–150 KB; loading one to check a single rule is the largest avoidable token cost in the pipeline. Reads locate sections with the SPEC-INDEX and `grep`, then `Read` with `offset`/`limit`; writes go through the file editing tools.

**Pick the path first.** If the `codebase-memory-mcp` tools (`list_projects`, `search_code`, `get_file_outline`) are not in your tool list, use the **Grep path** below and skip Steps 1.2–1.3, the MCP calls in Steps 2–3, and the reindex in Step 4.6. This is the common case. Steps 1–4 describe the optional MCP-accelerated path.

## Terms

- **Docs root** — the documentation repository root, resolved from the project `CLAUDE.md` key `sdlc-docs-path` (default `docs/`). Every path below is relative to it.
- **Docs project** — the codebase-memory-mcp project whose `root_path` equals the docs root.
- **Section** — one Markdown heading and the body up to the next heading of the same or higher level. The graph stores each heading as a `Section` node whose `start_line` is the heading line; the body is not part of the node.
- **SPEC-INDEX** — the `<!-- SPEC-INDEX v1 -->` block that lists every chapter of a spec. Format rules: [references/spec-index-format.md](references/spec-index-format.md).

## Step 1 — Sync and resolve the docs project

1. Run the docs sync in `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` Step 0.5 so the working tree reflects the remote before reading or writing.
2. Call `list_projects` and pick the entry whose `root_path` is the docs root.
3. When the sync step pulled new commits, call `index_repository(repo_path=<docs root>, name=<docs project>, mode="fast")`; `name` refreshes that project, and a call without it creates a second project named from the path. When no entry matches, make the same call without `name` once and use the project name it returns.

**Complete when:** a docs project name is in hand and its index postdates the last pull.

## Step 2 — Locate

Pick the entry point by what is known:

| Known | Call |
|---|---|
| A literal (rule ID `BL-006`, table `ORDER_ITEM`, field `OK_FLAG`, a phrase) | `search_code(project, pattern, file_pattern="*.md", mode="compact")` — returns files and matching lines |
| A heading topic (`訂單狀態流程圖`, `變體版對照`) | `search_graph(project, label="Section", name_pattern=".*<topic>.*")` — `query` (BM25) misses CJK headings |
| A file path | `get_file_outline(project, file_path)` — every Section with its `start_line`, in document order |

For a spec with a SPEC-INDEX, read the index block first (Step 3) to learn which chapter holds the answer, then outline the file to get that chapter's line.

When a cited file is missing from results, run `check_index_coverage(project, paths=[...])`; a `not_tracked` path is reindexed (Step 1.3) or read with the Grep path below.

**Complete when:** each target is pinned to a file and a Section `start_line`.

## Step 3 — Read

- **Section body:** from the outline, `start` is the target Section's `start_line` and `end` is the next Section's `start_line` at the same or higher level (or end of file). Call `Read(file_path=<docs root>/<file>, offset=start, limit=end-start)`.
- **Match neighbourhood:** `search_code(..., mode="full", context=<lines>)` returns bounded source around each match — enough to quote a table row or rule without a section read.
- **One-page summary:** `§0` sits before the SPEC-INDEX; read it for a human overview only.

`get_code_snippet` on a Section returns the heading line alone; use `Read` for the body.

- **Large behavioural specs with a dedicated line index** (a sibling `*-index.md`, e.g. `01-behavioral-spec-index.md`): read the index first, then `Read` only the line range it points to.

Read a whole file only when it is under 20 KB or the task rewrites the entire document (a `specify-*` CR in-place update).

**Complete when:** every claim the task relies on is backed by a section read or a match excerpt, cited as `<file> §<section>`.

## Step 4 — Write

Writes change files in the docs root working tree with the file tools. codebase-memory-mcp is read-only.

1. **Pin the target** with Steps 2–3 on the latest working tree.
2. **Edit in place** with `Edit`: `old_string` anchors on the Section heading plus enough body to be unique; `new_string` carries the full replacement section. One `Edit` per section keeps diffs reviewable.
3. **Create or rewrite** with `Write` only for a new document or a whole-document rewrite; start new documents from the matching `${CLAUDE_PLUGIN_ROOT}/templates/` file.
4. **Keep the SPEC-INDEX current** in the same batch: any added, removed, renamed, or renumbered chapter, and any changed US／BR／VR／IF／TC range, updates its index line per [spec-index-format.md](references/spec-index-format.md).
5. **Verify the index** with the rule-6 check in that reference; its `diff` prints nothing.
6. **Reindex**: `index_repository(repo_path=<docs root>, name=<docs project>, mode="fast")`, then `get_file_outline` on each written file shows the intended headings.
7. **Hand off the commit**: report every written path to the user. The user commits and pushes the docs repository.

**Complete when:** every written file passes the rule-6 check, its outline shows the intended headings, and the written paths are reported.

## Grep path (default)

Used whenever codebase-memory-mcp tools are absent, which includes every subagent restricted to `Read`/`Grep`/`Bash`:

1. Locate the index: `grep -n 'SPEC-INDEX v1' <spec>`, then `Read(offset=<line>, limit=40)`.
2. Locate chapters: `grep -n "^## " <spec>` (sub-sections: `grep -n "^### 6\." <spec>`).
3. `Read` with `offset`/`limit` for the target chapter.

Writes follow Step 4 without the reindex. When the MCP path is in use, the calling session reindexes once the agent returns.

## Related

- [spec-index-format.md](references/spec-index-format.md) — SPEC-INDEX format, rule-6 check, CR variant, `linear-create` source sections.
- `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` Step 0.5 — docs remote sync.
