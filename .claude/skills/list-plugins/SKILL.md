---
name: list-plugins
description: Use when needing a quick overview of marketplace plugins, finding which plugin contains a specific skill, or checking current plugin versions.
model: haiku
---

# List Plugins

Display a global index of all marketplace plugins and their components.

## Input

```
$ARGUMENTS
```

- `list-plugins` — show full index
- `list-plugins <query>` — filter by plugin or skill name

## Steps

### 1. Scan Marketplace

Read `.claude-plugin/marketplace.json` for plugin list with versions.

### 2. Scan Each Plugin

For each plugin, discover:
- Skills: `plugins/<name>/skills/*/SKILL.md`
- Agents: `plugins/<name>/agents/*.md`
- Rules: `plugins/<name>/rules/*.md`

### 3. Display Index

```markdown
## Marketplace Index

### <plugin-name> v<version>
<description>

**Skills:**
- <skill-name> — <description from frontmatter>

**Agents:**
- <agent-name>

**Rules:**
- <rule-name>

---
(repeat for each plugin)
```

### 4. Filter (if query provided)

If user provided a search query, filter the index to show only matching plugins or skills (case-insensitive partial match on name or description).

### 5. Summary Stats

```
Total: N plugins, N skills, N agents, N rules
```
