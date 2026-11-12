#!/usr/bin/env python3
"""SessionStart（compact）hook：context 壓縮後提醒 agent 沿用使用者指示的語言與格式。

壓縮摘要與 harness 續接提示常是英文，會把回覆語言帶偏（2026-11-11 壓縮後連續多輪改用英文）。
文字規則擋不住，所以在壓縮後主動注入一次。
"""
import json
import sys

MSG = ("[toolkit] context 剛壓縮。回覆語言、回合結尾格式、提問方式一律照使用者的 CLAUDE.md 與 rules；"
       "壓縮摘要與續接提示用什麼語言，不代表要換語言。")


def main():
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": MSG}},
                     ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
