---
tool: Bash
pattern: '(?:^|[;&|(])\s*git\s+add\s+(?:[^;&|\n]*\s)?(?:-A|--all|\.)(?=\s|$|[;&|)])'
action: deny
evidence: 多 agent／多工並行時，全量 add 會把別人 pre-staged 的檔案誤包進自己的 commit
---
從 `git status --short` 清單逐檔指名 `git add <檔>`，commit 前再看一次 staged。
