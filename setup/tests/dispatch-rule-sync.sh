#!/usr/bin/env bash
# user 層 dispatch.md 的等級表要跟 agent-dispatch routing.json 的 claude 候選一致
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
python3 - "$root" <<'PY'
import json, sys, pathlib
root = pathlib.Path(sys.argv[1])
routing = json.loads((root / "plugins/toolkit/skills/agent-dispatch/references/routing.json").read_text())
rule = (root / "setup" / "home" / "rules" / "dispatch.md").read_text()
line = next(l for l in rule.splitlines() if "派工帶模型" in l)
pos = -1
for tier in ("top", "standard", "cheap"):
    c = next(x for x in routing["tiers"][tier] if x["cli"] == "claude")
    want = f"`{c['model']}`／`{c['effort']}`"
    i = line.find(want)
    assert i > pos, f"dispatch.md 缺少或順序不對：{tier} 應為 {want}"
    pos = i
print("OK dispatch-rule-sync")
PY
