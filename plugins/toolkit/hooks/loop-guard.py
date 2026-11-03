#!/usr/bin/env python3
"""失敗迴圈 hook：同一輪內同一失敗指紋出現 3 次，提示停下重估。

把「連續失敗時停下重估」從文字規則變成 hook 強制；不呼叫模型、零額外 token。
一支腳本吃兩種 payload：
- Claude Code：PostToolUseFailure（錯誤在 `error`）；UserPromptSubmit 重置主 session。
- Codex：PostToolUse（沒有失敗事件；`tool_response` 只是輸出，成敗查 `transcript_path`
  裡同 `tool_use_id` 的 item_completed `status`）；`turn_id` 換了就重置。
主 session 與 subagent（`agent_id`）各自計數；Claude 的 subagent 整個生命週期算一輪。
第 THRESHOLD 次注入轉向提示進 context，之後同指紋再犯只給使用者 systemMessage。
任何例外吞掉、exit 0（fail-open：判不出失敗就不計數，不擋工具）。
"""
import json
import os
import re
import sys
import time
from pathlib import Path

THRESHOLD = 3
TAIL_BYTES = 512 * 1024
PRUNE_AGE = 7 * 86400
EXIT_LINE = re.compile(r"^exit code:? -?\d+$", re.I)


def fingerprint(tool, text):
    """工具名＋錯誤第一個有意義的行，去數字／十六進位位址／路徑（借自 TokenEconomizer loopguard）。"""
    lines = [l.strip() for l in str(text).splitlines() if l.strip()]
    first = next((l for l in lines if not EXIT_LINE.match(l)), lines[0] if lines else "")
    sig = " ".join(re.sub(r"0x[0-9a-f]+|\d+|/\S+", "", first[:300], flags=re.I).split())
    # 整行只有數字／路徑時正規化後是空的，退回原文，免得不同失敗全併成同一個指紋
    return "%s|%s" % (tool, sig or first[:120]), first[:120]


def codex_failed(payload):
    """Codex：從 rollout transcript 尾端找這筆呼叫的完成紀錄；找不到就當成功（不計數）。"""
    tid = payload.get("tool_use_id") or ""
    path = payload.get("transcript_path") or ""
    if not tid or not os.path.isfile(path):
        return False
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - TAIL_BYTES))
        data = f.read()
    if tid.encode("utf-8") not in data:   # Codex 每次工具呼叫都跑，先用 bytes 篩掉多數情況
        return False
    for line in reversed(data.decode("utf-8", "ignore").splitlines()):
        if tid not in line or "item_completed" not in line:
            continue
        try:
            item = json.loads(line)["payload"]["item"]
        except (ValueError, KeyError, TypeError):
            continue
        if item.get("id") == tid:
            return item.get("status") == "failed" or item.get("exit_code") not in (None, 0)
    return False


def safe(name):
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(name))[:80] or "_"


def prune(root):
    """清掉 7 天沒寫入的狀態檔與空目錄；看檔案 mtime（覆寫不會更新目錄 mtime），逐項容錯。"""
    if not root.is_dir():
        return
    cutoff = time.time() - PRUNE_AGE
    for d in root.iterdir():
        try:
            for f in d.iterdir():
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
            d.rmdir()   # 還有檔案（活躍 session）就 OSError，跳過
        except OSError:
            pass


def advice(tool, line, n):
    return ("loop-guard：同一失敗（%s：%s）本輪已出現 %d 次。停下重估，不要再用同一方向重試："
            "1) 重讀錯誤，列出已排除的假設；2) 換方向前先落檔失敗原因；"
            "3) 若是被規則／文件／記憶帶偏，或該有規則卻沒寫，用 toolkit:feedback-review 的 friction 子命令記下。"
            ) % (tool, line, n)


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        return
    event = payload.get("hook_event_name")
    sid = payload.get("session_id")
    if not sid:
        return
    codex = "turn_id" in payload
    root = Path(os.path.expanduser("~/.codex" if codex else "~/.claude")) / "loop-guard"
    sdir = root / safe(sid)
    key = safe(payload.get("agent_id") or "main")

    if event == "UserPromptSubmit":
        (sdir / "main.json").unlink(missing_ok=True)
        prune(root)
        return

    tool = payload.get("tool_name") or "?"
    if event == "PostToolUseFailure" and not codex:
        text = payload.get("error")
        if not text or payload.get("is_interrupt"):
            return
    elif event == "PostToolUse" and codex:
        if not codex_failed(payload):
            return
        text = payload.get("tool_response")
        text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    else:
        return

    fp, line = fingerprint(tool, text)
    state_file = sdir / (key + ".json")
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if codex and state.get("turn") != payload.get("turn_id"):
        state = {}
    state["turn"] = payload.get("turn_id")
    counts = state.setdefault("counts", {})
    counts[fp] = n = counts.get(fp, 0) + 1
    sdir.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_name("%s.%d.tmp" % (state_file.name, os.getpid()))
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, state_file)   # 原子替換：並行讀到的不會是半截檔（同 key 並行寫仍可能少算，可接受）
    if n < THRESHOLD:
        return
    out = {"systemMessage": "loop-guard：%s 本輪同一失敗第 %d 次（%s）。想打斷可按 Esc。" % (tool, n, line)}
    if n == THRESHOLD:   # 只在第一次觸發進 context，之後再犯只提醒使用者
        out["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": advice(tool, line, n)}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
