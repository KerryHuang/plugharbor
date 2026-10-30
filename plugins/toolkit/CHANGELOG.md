# Changelog

格式：每次改動 `hooks/`、`guards/`、`skills/`、`agents/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.1.0] - 2026-10-30

- feat: 初版 hooks——`guard.py`（PreToolUse，分層 guard）、`agent-model-guard.py`、`ask-question-guard.py`、`auto-session-title.py`、`feedback-capture.py`、`feedback-reminder.py`、`context-size-reminder.py`、`notification.sh`（macOS 播系統 Glass 音，不附音效檔）。
- feat: 分層 guard——讀取順序 `plugin/guards` → `~/.claude/guards` → `<專案>/.claude/guards`，同名檔由後讀的覆寫；規則檔 CRLF 也能解析。內建 `git-add-all`、`git-destructive` 兩條。
- feat: `hooks.json` 以 `${CLAUDE_PLUGIN_ROOT}` 註冊，保留「找得到能跑的 python 才執行，否則 exit 0」外殼。
- feat: 7 個 skill——`config-doctor`（設定健檢）、`context-diet`（context 瘦身）、`tidy-memory`（整理 auto-memory）、`feedback-review`（回顧糾正佇列，含 `friction` 子命令說明）、`handoff`（交接）、`agent-dispatch`（派工給其他 agent CLI）、`agent-mesh-check`（驗證 agent CLI 互叫）。
- feat: 5 支 reviewer agent——`claudemd-reviewer`、`hook-reviewer`、`rule-reviewer`、`skill-reviewer`、`subagent-reviewer`（取自 Reflexive-Claude-Code，MIT，見 `agents/NOTICE.txt`）。
- test: `feedback_queue.py` 單元測試（`test_feedback_queue.py`）、`agent-mesh.test.mjs`（node --test）。
- test: `hooks/tests/test_guard.py` 與四支 shell 測試（ask-question-guard、auto-session-title、context-reminder、feedback-hooks）。
