---
name: release-plugin
description: Use when bumping a plugin version, releasing a new plugin version, or syncing version numbers across plugin.json, marketplace.json, README.md, and CHANGELOG.md.
---

# Release Plugin

Sync version numbers across all four locations when releasing a plugin update.

## Input

```
$ARGUMENTS
```

- `release-plugin <name> <bump>` — release with specified bump (patch/minor/major)
- `release-plugin <name>` — prompt for bump type
- `release-plugin` — prompt for plugin and bump type

## Steps

### 1. Select Plugin

If not specified, list available plugins from `.claude-plugin/marketplace.json` and ask user to choose.

### 2. Read Current Version

Read `plugins/<name>/.claude-plugin/plugin.json` → extract current `version`.

### 3. Calculate New Version

| Bump | Example |
|------|---------|
| patch | 1.2.0 → 1.2.1 (bug fixes) |
| minor | 1.2.0 → 1.3.0 (new skills/features) |
| major | 1.2.0 → 2.0.0 (breaking changes) |

Confirm with user: "版本 `<current>` → `<new>`，確認？"

### 4. Update All Four Locations

1. `plugins/<name>/.claude-plugin/plugin.json` → update `version`
2. `.claude-plugin/marketplace.json` → update matching plugin `version`
3. `README.md` → update version in plugin table row
4. `plugins/<name>/CHANGELOG.md` → add `## [<new>] - <yyyy-mm-dd>` at the top (正體中文, list what changed)

### 5. Verify Consistency

Run `python3 scripts/ci/validate.py` — it checks all four locations plus frontmatter, cross-references and the README catalog. Fix every reported issue before committing.

### 6. Summary

List all files modified and the version change:

```
<name>: <old> → <new>
  - plugins/<name>/.claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - README.md
  - plugins/<name>/CHANGELOG.md
```
