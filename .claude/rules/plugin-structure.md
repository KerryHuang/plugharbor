---
description: Enforces plugin directory structure and file placement conventions
globs:
  - "plugins/**"
---

# Plugin Structure

- Skills MUST be placed in `skills/<skill-name>/SKILL.md` (plugin root, auto-discovered)
- Agents MUST be placed in `agents/<agent-name>.md` (plugin root, kebab-case, auto-discovered)
- 每個 plugin 必須能單獨安裝使用：`plugin.json` 不宣告 `dependencies`；叫用其他 plugin 一律是可選並寫明沒裝時的退路，必要的共用素材複製一份並加同步測試
- Plugins do NOT support `rules/` — embed conventions into SKILL.md or agent definitions instead
- Shared references at plugin root (e.g., `references/`, `templates/`) are NOT auto-discovered — skills reference them via `${CLAUDE_PLUGIN_ROOT}/`
