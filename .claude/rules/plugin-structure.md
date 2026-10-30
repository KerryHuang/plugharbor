---
description: Enforces plugin directory structure and file placement conventions
globs:
  - "plugins/**"
---

# Plugin Structure

- Skills MUST be placed in `skills/<skill-name>/SKILL.md` (plugin root, auto-discovered)
- Agents MUST be placed in `agents/<agent-name>.md` (plugin root, kebab-case, auto-discovered)
- Plugins do NOT support `rules/` — embed conventions into SKILL.md or agent definitions instead
- Shared references at plugin root (e.g., `references/`, `templates/`) are NOT auto-discovered — skills reference them via `${CLAUDE_PLUGIN_ROOT}/`
