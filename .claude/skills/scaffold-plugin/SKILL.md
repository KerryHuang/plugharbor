---
name: scaffold-plugin
description: Use when adding a new plugin to the marketplace, creating plugin boilerplate, or bootstrapping a plugin directory with standard structure.
---

# Scaffold Plugin

Create a new plugin with the standard marketplace structure.

## Input

```
$ARGUMENTS
```

- `scaffold-plugin <name>` — create plugin with given name
- `scaffold-plugin` — prompt for name and details interactively

## Steps

### 1. Collect Plugin Metadata

Ask user (one question at a time) if not provided in arguments:
- **name**: kebab-case plugin name (e.g., `my-plugin`)
- **description**: one-line description in Chinese or English
- **author**: author name (default: `KerryHuang`)

### 2. Validate Name

- MUST be kebab-case (`^[a-z][a-z0-9-]*$`)
- MUST NOT conflict with existing plugin directories under `plugins/`
- Check: `ls plugins/` for conflicts

### 3. Create Directory Structure

```
plugins/<name>/
  .claude-plugin/
    plugin.json
  skills/
  agents/
  README.md
```

### 4. Generate plugin.json

```json
{
  "name": "<name>",
  "version": "0.1.0",
  "description": "<description>",
  "author": {
    "name": "<author>"
  },
  "license": "MIT"
}
```

### 5. Update Marketplace Registry

Add entry to `.claude-plugin/marketplace.json` `plugins` array:

```json
{
  "name": "<name>",
  "source": "./plugins/<name>",
  "description": "<description>",
  "version": "0.1.0"
}
```

### 6. Update README.md

Add row to the plugin table in root `README.md`:

```markdown
| <name> | 0.1.0 | <description> |
```

### 7. Verify

- [ ] `plugins/<name>/.claude-plugin/plugin.json` exists with name, version, description, author, license
- [ ] `.claude-plugin/marketplace.json` contains new plugin entry
- [ ] `README.md` plugin table includes new row
- [ ] All three versions match (`0.1.0`)

Report: "Plugin `<name>` v0.1.0 已建立。"
