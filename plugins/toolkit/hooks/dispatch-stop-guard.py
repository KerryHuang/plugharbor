#!/usr/bin/env python3
"""Stop hook：被 agent-dispatch 派出的 worker 沒寫結果檔就想結束時擋下來。

只在環境變數 AGENT_DISPATCH_RESULT 有設時作用（bg.mjs 與 herdr pane 會設），一般 session 不受影響。
AGENT_DISPATCH_INTERACTIVE=1 表示 worker 可能停下來等人（herdr pane）：提示改成「還沒做完就別寫檔」，
免得等人回答時寫出「待決」的結果檔被當成完成。
stop_hook_active 為 true 代表已經擋過一次，放行避免無限迴圈。fail-open：任何例外都放行。
"""
import json
import os
import sys


def main() -> None:
    result = os.environ.get("AGENT_DISPATCH_RESULT")
    if not result:
        return
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return
    if payload.get("stop_hook_active") or os.path.exists(result):
        return
    if os.environ.get("AGENT_DISPATCH_INTERACTIVE") == "1":
        reason = (f"你是被派出的 worker，結果檔 {result} 還沒寫。任務做完了：寫結果檔，再照 prompt 回報派工者。"
                  "任務還沒做完（在等人回答，或照指示先停）：不要寫結果檔，直接再結束一次。")
    else:
        reason = f"你是被派出的 worker，結果檔 {result} 還沒寫。寫完結果檔（完成／失敗／待決、做了什麼、要清的路徑）再結束。"
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail-open：hook 壞掉不能卡住 worker
        print(f"[dispatch-stop-guard] {e}", file=sys.stderr)
    sys.exit(0)
