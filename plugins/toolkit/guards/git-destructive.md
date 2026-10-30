---
tool: Bash
pattern: '(?:^|[;&|(])\s*git\s+(?:push\b[^;&|\n]*\s(?:-f|--force(?:-with-lease)?)(?=\s|$)|reset\b[^;&|\n]*\s--hard\b|clean\b[^;&|\n]*\s-[a-zA-Z]*f)'
action: ask
evidence: force push、reset --hard、clean -fd 會丟掉別人或自己的工作，一律先經使用者確認
---
這是破壞性 git 操作：先列出確切指令與影響範圍，取得使用者同意；不確定就先 `git stash` 或備份。
