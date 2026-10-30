# graphify 特殊模式（--update / --cluster-only / --watch / git hook / claude install）與疑難排解

## For --update (incremental re-extraction)

Use when you've added or modified files since the last run. Only re-extracts changed files - saves tokens and time.

```bash
${GRAPHIFY_PYTHON:-python} -c "
import sys, json
from graphify.detect import detect_incremental, save_manifest
from pathlib import Path

result = detect_incremental(Path('INPUT_PATH'))
new_total = result.get('new_total', 0)
print(json.dumps(result, indent=2))
Path('.graphify_incremental.json').write_text(json.dumps(result))
if new_total == 0:
    print('No files changed since last run. Nothing to update.')
    raise SystemExit(0)
print(f'{new_total} new/changed file(s) to re-extract.')
"
```

If new files exist, first check whether all changed files are code files:

```bash
${GRAPHIFY_PYTHON:-python} -c "
import json
from pathlib import Path

result = json.loads(open('.graphify_incremental.json').read()) if Path('.graphify_incremental.json').exists() else {}
code_exts = {'.py','.ts','.js','.go','.rs','.java','.cpp','.c','.rb','.swift','.kt','.cs','.scala','.php','.cc','.cxx','.hpp','.h','.kts','.lua','.toc'}
new_files = result.get('new_files', {})
all_changed = [f for files in new_files.values() for f in files]
code_only = all(Path(f).suffix.lower() in code_exts for f in all_changed)
print('code_only:', code_only)
"
```

If `code_only` is True: print `[graphify update] Code-only changes detected - skipping semantic extraction (no LLM needed)`, run only Step 3A (AST) on the changed files, skip Step 3B entirely (no subagents), then go straight to merge and Steps 4–8.

If `code_only` is False (any changed file is a doc/paper/image): run the full Steps 3A–3C pipeline as normal.

Then:

```bash
${GRAPHIFY_PYTHON:-python} -c "
import sys, json
from graphify.build import build_from_json
from graphify.export import to_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

# Load existing graph
existing_data = json.loads(Path('graphify-out/graph.json').read_text())
G_existing = json_graph.node_link_graph(existing_data, edges='links')

# Load new extraction
new_extraction = json.loads(Path('.graphify_extract.json').read_text())
G_new = build_from_json(new_extraction)

# Merge: new nodes/edges into existing graph
G_existing.update(G_new)
print(f'Merged: {G_existing.number_of_nodes()} nodes, {G_existing.number_of_edges()} edges')
" 
```

Then run Steps 4–8 on the merged graph as normal.

After Step 4, show the graph diff:

```bash
${GRAPHIFY_PYTHON:-python} -c "
import json
from graphify.analyze import graph_diff
from graphify.build import build_from_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

# Load old graph (before update) from backup written before merge
old_data = json.loads(Path('.graphify_old.json').read_text()) if Path('.graphify_old.json').exists() else None
new_extract = json.loads(Path('.graphify_extract.json').read_text())
G_new = build_from_json(new_extract)

if old_data:
    G_old = json_graph.node_link_graph(old_data, edges='links')
    diff = graph_diff(G_old, G_new)
    print(diff['summary'])
    if diff['new_nodes']:
        print('New nodes:', ', '.join(n['label'] for n in diff['new_nodes'][:5]))
    if diff['new_edges']:
        print('New edges:', len(diff['new_edges']))
"
```

Before the merge step, save the old graph: `Copy-Item graphify-out/graph.json .graphify_old.json`
Clean up after: `rm -f .graphify_old.json`

---

## For --cluster-only

Skip Steps 1–3. Load the existing graph from `graphify-out/graph.json` and re-run clustering:

```bash
${GRAPHIFY_PYTHON:-python} -c "
import sys, json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections
from graphify.report import generate
from graphify.export import to_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')

detection = {'total_files': 0, 'total_words': 99999, 'needs_graph': True, 'warning': None,
             'files': {'code': [], 'document': [], 'paper': []}}
tokens = {'input': 0, 'output': 0}

communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: 'Community ' + str(cid) for cid in communities}

report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, '.')
Path('graphify-out/GRAPH_REPORT.md').write_text(report)
to_json(G, communities, 'graphify-out/graph.json')

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
}
Path('.graphify_analysis.json').write_text(json.dumps(analysis, indent=2))
print(f'Re-clustered: {len(communities)} communities')
"
```

Then run Steps 5–9 as normal (label communities, generate viz, benchmark, clean up, report).
## For --watch

Start a background watcher that monitors a folder and auto-updates the graph when files change.

```bash
${GRAPHIFY_PYTHON:-python} -m graphify.watch INPUT_PATH --debounce 3
```

Replace INPUT_PATH with the folder to watch. Behavior depends on what changed:

- **Code files only (.py, .ts, .go, etc.):** re-runs AST extraction + rebuild + cluster immediately, no LLM needed. `graph.json` and `GRAPH_REPORT.md` are updated automatically.
- **Docs, papers, or images:** writes a `graphify-out/needs_update` flag and prints a notification to run `/graphify --update` (LLM semantic re-extraction required).

Debounce (default 3s): waits until file activity stops before triggering, so a wave of parallel agent writes doesn't trigger a rebuild per file.

Press Ctrl+C to stop.

For agentic workflows: run `--watch` in a background terminal. Code changes from agent waves are picked up automatically between waves. If agents are also writing docs or notes, you'll need a manual `/graphify --update` after those waves.

---

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
graphify hook install    # install
graphify hook uninstall  # remove
graphify hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook - run `/graphify --update` manually for those.

If a post-commit hook already exists, graphify appends to it rather than replacing it.

---

## For native CLAUDE.md integration

Run once per project to make graphify always-on in Claude Code sessions:

```bash
graphify claude install
```

This writes a `## graphify` section to the local `CLAUDE.md` that instructs Claude to check the graph before answering codebase questions and rebuild it after code changes. No manual `/graphify` needed in future sessions.

```bash
graphify claude uninstall  # remove the section
```

---

## Troubleshooting

### PowerShell 5.1: Vertical scrolling stops working

If vertical scrolling breaks in PowerShell after running graphify, this is caused by ANSI escape sequences from the `graspologic` library. Graphify v0.3.10+ suppresses this output, but if you still see the issue:

1. **Upgrade graphify**: `pip install --upgrade graphifyy`
2. **Use Windows Terminal** instead of the legacy PowerShell console — Windows Terminal handles ANSI codes correctly
3. **Reset your terminal**: close and reopen PowerShell
4. **Skip graspologic**: uninstall it (`pip uninstall graspologic`) and graphify will fall back to NetworkX's built-in Louvain algorithm, which produces no ANSI output
