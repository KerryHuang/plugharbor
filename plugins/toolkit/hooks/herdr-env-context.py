#!/usr/bin/env python3
"""SessionStart hook：在 herdr 內就告訴 agent，免得它為了確認能否開 pane 多跑一次檢查、還講給使用者聽。

不在 herdr 內時不輸出；沒有這支 hook 的 CLI 仍照 dispatch 規則自行檢查 HERDR_ENV。
"""
import json
import os
import sys

MSG = ("[toolkit] 本 session 在 herdr 內（HERDR_ENV=1），不必再檢查能否開 pane，也不必向使用者提這件事。"
       "這只代表「能開」；該不該開仍照派工判準，長任務照判準表開 pane。")


def record_session_id():
    """hc 下把 hook 輸入的 session_id 記到 hc-sessions/<HC_TERMINAL_ID>（供 mux.py session 讀）。任何失敗都略過。"""
    term = os.environ.get("HC_TERMINAL_ID", "")
    if not term or "/" in term or "\\" in term or term.startswith("."):
        return
    try:
        sid = json.loads(sys.stdin.buffer.read().decode("utf-8")).get("session_id")
        if not isinstance(sid, str) or not sid.strip():
            return
        base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
        d = os.path.join(base, "plugharbor", "hc-sessions")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, term), "w", encoding="utf-8") as f:
            f.write(sid.strip() + "\n")
    except Exception:
        pass


def main():
    record_session_id()
    if os.environ.get("HERDR_ENV") != "1":
        return 0
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": MSG}},
                     ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
