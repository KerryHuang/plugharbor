#!/usr/bin/env python3
"""SessionStart hook：在 herdr 內就告訴 agent，免得它為了確認能否開 pane 多跑一次檢查、還講給使用者聽。

不在 herdr 內時不輸出；沒有這支 hook 的 CLI 仍照 dispatch 規則自行檢查 HERDR_ENV。
"""
import json
import os
import sys

MSG = ("[toolkit] 本 session 在 herdr 內（HERDR_ENV=1），不必再檢查能否開 pane，也不必向使用者提這件事。"
       "這只代表「能開」；該不該開仍照派工判準，能用 subagent 就不開 pane。")


def main():
    if os.environ.get("HERDR_ENV") != "1":
        return 0
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": MSG}},
                     ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
