---
name: audit-skills
description: Use when reviewing skill quality across plugins, checking for duplicate or malformed skills, or preparing for a refactoring pass.
context: fork
---

# Audit Skills

Cross-plugin skill quality analysis with actionable refactoring suggestions.

## Input

```
$ARGUMENTS
```

- `audit-skills` — audit all plugins
- `audit-skills <plugin-name>` — audit specific plugin only
- `audit-skills --fix` — auto-fix safe issues (missing frontmatter fields, naming)

## Steps

### 1. Discover Skills

Scan `plugins/*/skills/*/SKILL.md` to build inventory:
- Plugin name
- Skill name
- SKILL.md path

### 2. Check Each Skill

For each SKILL.md, check:

| Check | Rule | Severity |
|-------|------|----------|
| Frontmatter has `name` | Required | CRITICAL |
| Frontmatter has `description` | Required | CRITICAL |
| Line count < 300 | Skill conventions rule | WARNING |
| Directory name is kebab-case | Naming convention | WARNING |
| References in `references/` subdirectory | Skill conventions rule | INFO |
| No hardcoded absolute paths | Portability | WARNING |

### 3. Cross-Plugin Analysis

- **Duplicate detection**: Compare skill names and descriptions across plugins for potential overlap
- **Naming consistency**: Check all skill names follow the same pattern
- **Coverage gaps**: Note plugins with no skills or no agents

### 4. Generate Report

```markdown
# Skill Audit Report

**Date**: YYYY-MM-DD
**Plugins scanned**: N
**Skills found**: N

## Summary

| Plugin | Skills | Issues |
|--------|--------|--------|

## Issues

### CRITICAL
- [list]

### WARNING
- [list]

### INFO
- [list]

## Cross-Plugin Findings
- [duplicates, gaps, inconsistencies]

## Refactoring Suggestions
- [actionable recommendations]
```

### 5. Present Results

Display report to user. If `--fix` flag provided, offer to auto-fix safe issues (missing frontmatter fields, naming).
