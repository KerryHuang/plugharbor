#!/usr/bin/env python3
"""UserPromptSubmit hook：套用 skill 建議的 session 標題。

一般 session 交給 Claude Code 內建的 ai-title（以開場內容命名，含票號／功能代碼，品質夠用）；
本 hook 只在上一回合 assistant 給了「建議 session 標題…：/rename <標題>」（如 sdlc:linear-triage
報告末尾）時，於下一次送出輸出 sessionTitle 套用——model 無法自己執行 /rename。
使用者手動 /rename 的（nameSource="user"）不覆寫。
assistant 還在跑時送出的 prompt 會排隊，Claude Code 在送出當下就跑本 hook、讀不到之後才寫出的建議行；
這種 prompt（sentAtMs 早於建議行）不算回合邊界，下一次送出時補套用。

使用者訊息提到標題／改名／rename 時，另以 additionalContext 注入目前標題與各來源，
讓 agent 不必猜（曾拿 ~/.claude/sessions 的 derived 名稱當證據，誤判改名沒生效）。

註：曾自己用 haiku 產標題，但寫入的 custom-title 會蓋掉內建 ai-title，實測幾乎都比內建差，已移除。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 只認行首（可帶縮排、引言、清單或粗體符號）的建議行；句中引用這個句型（如說明機制時）不算
SUGGEST_RE = re.compile(r"^[ \t>*\-]*建議[^\n]{0,10}session 標題[^\n]*?/rename\s+([^\n`]+)", re.M)
TAIL_BYTES = 256 * 1024
MAX_TITLE = 80
ASK_RE = re.compile(r"標題|改名|rename", re.I)


def current_name(sid):
    """回傳 (nameSource, name)；找不到這個 session 回 ("", "")。
    名稱寫在 ~/.claude/sessions/<pid>.json，以 sessionId 比對。"""
    d = Path(os.path.expanduser("~/.claude")) / "sessions"
    try:
        files = list(d.glob("*.json"))
    except OSError:
        return "", ""
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rec.get("sessionId") == sid:
            return rec.get("nameSource") or "", (rec.get("name") or "").strip()
    return "", ""


def suggested_title(transcript):
    """從 transcript 尾端找上一回合 assistant 文字裡的建議標題；沒有回空字串。
    往回掃到真正的使用者 prompt（非 tool_result）為止；當輪 prompt 若已寫入就先跳過。"""
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - TAIL_BYTES))
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    seen_assistant = False
    cutoff = None  # 排隊送出的 prompt 的送出時間（ms）：比它晚寫出的 assistant 文字，當時的 hook 看不到
    for line in reversed(tail.splitlines()):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        content = (rec.get("message") or {}).get("content")
        if rec.get("type") == "user":
            is_prompt = isinstance(content, str) or (
                isinstance(content, list)
                and any(isinstance(b, dict) and b.get("type") != "tool_result" for b in content)
            )
            if rec.get("promptSource") == "system":
                continue  # task-notification 等系統訊息不是使用者送出的
            if is_prompt and seen_assistant:
                if cutoff is not None or not isinstance(rec.get("sentAtMs"), (int, float)):
                    return ""
                cutoff = rec["sentAtMs"]
            continue
        if rec.get("type") != "assistant" or not isinstance(content, list):
            continue
        if cutoff is not None and _ms(rec.get("timestamp")) <= cutoff:
            return ""  # 排隊的 prompt 送出前就寫好的回合，當時已處理過
        seen_assistant = True
        text = "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
        hits = SUGGEST_RE.findall(text)
        if hits:
            title = hits[-1].strip(" *`「」\"'")
            return title if 0 < len(title) <= MAX_TITLE else ""
    return ""


def _ms(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return 0


def transcript_titles(transcript):
    """整份 transcript 最後一筆 ai-title、custom-title（custom-title 只在改名時寫一次，不能只看尾段）。"""
    found = {}
    try:
        with open(transcript, "rb") as fh:
            for line in fh:
                if b"-title" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") == "ai-title" and rec.get("aiTitle"):
                    found["ai"] = rec["aiTitle"]
                elif rec.get("type") == "custom-title" and rec.get("customTitle"):
                    found["custom"] = rec["customTitle"]
    except OSError:
        pass
    return found


def _run_json(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=3, encoding="utf-8")
        return json.loads(p.stdout) if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def herdr_titles():
    """在 Herdr.app 內：terminal title（hc get）與分頁名（herdr-app ls）；不在或失敗回 {}。"""
    term = os.environ.get("HC_TERMINAL_ID")
    info = _run_json(["hc", "get", "--json", term]) if term else None
    if not isinstance(info, dict):
        return {}
    out = {"terminal": (info.get("title") or "").strip()}
    tab_id = (info.get("labels") or {}).get("herdr.tab")
    ls = _run_json(["herdr-app", "ls"]) if tab_id else None
    for space in (ls or {}).get("spaces") or []:
        for tab in space.get("tabs") or []:
            if tab.get("id") == tab_id:
                out["tab"] = (tab.get("name") or "").strip()
    return out


def title_context(sid, transcript, applying):
    t = transcript_titles(transcript)
    source, name = current_name(sid)
    lines = ["目前 session 標題（auto-session-title hook 實查，回答標題問題以此為準，不要自己推測）："]
    lines.append(f"- 內建 ai-title：{t.get('ai') or 'transcript 沒有紀錄'}")
    lines.append(f"- custom-title（/rename 或本 hook 套用，有的話畫面顯示它）：{t.get('custom') or 'transcript 沒有紀錄'}")
    if applying:
        lines.append(f"- 本次送出正在套用建議標題：{applying}")
    if name:
        note = "自動衍生的識別名，不是標題" if source == "derived" else f"nameSource={source or '未知'}"
        lines.append(f"- ~/.claude/sessions 的 name：{name}（{note}）")
    h = herdr_titles()
    if h:
        lines.append(f"- Herdr terminal title（hc get）：{h.get('terminal') or '空'}；分頁名：{h.get('tab') or '查不到'}")
    return "\n".join(lines)


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    sid = data.get("session_id")
    transcript = data.get("transcript_path")
    if not sid or not transcript:
        return
    title = suggested_title(transcript)
    if title:
        source, name = current_name(sid)
        if source == "user" or name == title:
            title = ""
    out = {"hookEventName": "UserPromptSubmit"}
    if title:
        out["sessionTitle"] = title
    if ASK_RE.search(data.get("prompt") or ""):
        out["additionalContext"] = title_context(sid, transcript, title)
    if len(out) > 1:
        sys.stdout.write(json.dumps({"hookSpecificOutput": out}, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    main()
