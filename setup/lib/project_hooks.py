#!/usr/bin/env python3
"""install-project.sh --shared 的 lifecycle 專案層接點。

用法：project_hooks.py <專案根> <段落檔> <check|apply>
- AGENTS.md：標記內放段落檔；標記外 bytes 不動（二進位讀寫，保留 CRLF）。標記不成對就不寫。
- CLAUDE.md：已存在且 fence 外沒有獨立行 @AGENTS.md 引用才補一行；不存在不建。
- 寫入一律先寫同目錄暫存檔再 os.replace（對 symlink 指向的實體檔、保留權限）；讀寫失敗印 `FAIL: <檔> <原因>` 後繼續下一個檔。
- .claude/settings.json：enabledPlugins 合併 superpowers 宣告；已設 false 尊重，壞檔不動。
輸出前綴同 install-project.sh；exit 0 正常、1 有 FAIL。--check 的 MISSING／DIFF 由呼叫端計數。
"""
import json
import errno
import os
import re
import shutil
import sys
import tempfile

SP = "superpowers@claude-plugins-official"
BEGIN = b"<!-- plugharbor-lifecycle begin -->"
END = b"<!-- plugharbor-lifecycle end -->"
failed = False


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def write(path, data):
    real = os.path.realpath(path)  # symlink 不換成一般檔，寫到它指向的實體檔
    d = os.path.dirname(real) or "."
    os.makedirs(d, exist_ok=True)
    exists = os.path.exists(real)
    if exists and not os.access(real, os.W_OK):
        raise PermissionError(errno.EACCES, "唯讀，不改")
    if exists and os.stat(real).st_nlink > 1:
        # hardlink（如 CLAUDE.md 與 AGENTS.md 同 inode）：os.replace 會換掉 inode、斷開連結，改就地寫入。
        # 取捨：這條路徑不是原子的，中途失敗可能留下截斷檔。
        with open(real, "wb") as f:
            f.write(data)
        return
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".ph-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        if exists:
            shutil.copymode(real, tmp)
        else:
            um = os.umask(0); os.umask(um)
            os.chmod(tmp, 0o666 & ~um)
        os.replace(tmp, real)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def eol_of(data):
    return b"\r\n" if data and b"\r\n" in data else b"\n"


def fail(msg):
    global failed
    failed = True
    print("FAIL: " + msg)


def agents_md(root, sec_file, check):
    label = "AGENTS.md lifecycle 段落"
    path = os.path.join(root, "AGENTS.md")
    sec = read(sec_file).replace(b"\r\n", b"\n").rstrip(b"\n")
    cur = read(path)
    if cur is None:
        if check:
            print("MISSING: " + label)
        else:
            write(path, sec + b"\n"); print("OK:   " + label)
        return
    eol = eol_of(cur)
    block = sec.replace(b"\n", eol)
    nb, ne = cur.count(BEGIN), cur.count(END)
    if nb == 0 and ne == 0:
        if check:
            print("MISSING: " + label); return
        sep = b"" if cur.endswith(b"\n") else eol
        new = cur + sep + (eol if cur else b"") + block + eol
    elif nb == 1 and ne == 1 and cur.index(BEGIN) < cur.index(END):
        s, e = cur.index(BEGIN), cur.index(END) + len(END)
        if cur[s:e].replace(b"\r\n", b"\n") == sec:
            print("UP-TO-DATE: " + label); return
        if check:
            print("DIFF: " + label); return
        new = cur[:s] + block + cur[e:]
    else:
        fail("AGENTS.md lifecycle 標記不成對"); return
    write(path, new); print("OK:   " + label)


def has_ref(data):
    """fence 外有獨立行 @AGENTS.md／@./AGENTS.md（檔首 BOM 不影響）。"""
    ref = re.compile(rb"^@(\./)?AGENTS\.md[ \t]*\r?$")
    fence_re = re.compile(rb"^ {0,3}(`{3,}|~{3,})(.*)$")
    state = None  # 開啟中的 (字元, 長度)；CommonMark：同字元、長度 >= 開啟、其後只有空白才關閉
    for i, ln in enumerate(data.split(b"\n")):
        if i == 0 and ln.startswith(b"\xef\xbb\xbf"):
            ln = ln[3:]
        m = fence_re.match(ln.rstrip(b"\r"))
        if m:
            mark, rest = m.group(1), m.group(2)
            if state is None:
                if not (mark[:1] == b"`" and b"`" in rest):
                    state = (mark[:1], len(mark))
            elif mark[:1] == state[0] and len(mark) >= state[1] and not rest.strip():
                state = None
            continue
        if state is None and ref.match(ln):
            return True
    return False


def claude_md(root, check):
    label = "CLAUDE.md 引用 @AGENTS.md"
    path = os.path.join(root, "CLAUDE.md")
    cur = read(path)
    if cur is None:
        return
    agents = os.path.join(root, "AGENTS.md")
    if os.path.exists(agents) and os.path.samefile(path, agents):  # CLAUDE.md 是 AGENTS.md 的 symlink／hardlink：本身就是同一份
        print("UP-TO-DATE: " + label); return
    if has_ref(cur):
        print("UP-TO-DATE: " + label); return
    if check:
        print("MISSING: " + label); return
    eol = eol_of(cur)
    write(path, cur + (b"" if not cur or cur.endswith(b"\n") else eol) + b"@AGENTS.md" + eol)
    print("OK:   " + label)


def settings(root, check):
    label = "superpowers 宣告（.claude/settings.json）"
    path = os.path.join(root, ".claude", "settings.json")
    raw = read(path)
    if raw is None:
        d = {}
    else:
        try:
            d = json.loads(raw.decode("utf-8-sig"))
        except Exception as e:
            fail(f"讀不了 {path}：{e}"); return
        if not isinstance(d, dict) or not isinstance(d.get("enabledPlugins", {}), dict):
            fail(f"{path} 不是預期結構（根或 enabledPlugins 不是物件），不改"); return
    ep = d.get("enabledPlugins", {})
    if ep.get(SP) is False:
        print("SKIP: superpowers 已在專案停用"); return
    if SP in ep:
        print("UP-TO-DATE: " + label); return
    if check:
        print("MISSING: " + label); return
    d.setdefault("enabledPlugins", ep)[SP] = True
    out = (json.dumps(d, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if raw is not None and eol_of(raw) == b"\r\n":
        out = out.replace(b"\n", b"\r\n")
    write(path, out); print("OK:   " + label)


root, sec_file, mode = sys.argv[1:4]
check = mode == "check"
for name, fn, args in (("AGENTS.md", agents_md, (root, sec_file, check)),
                       ("CLAUDE.md", claude_md, (root, check)),
                       (".claude/settings.json", settings, (root, check))):
    try:
        fn(*args)
    except OSError as e:
        fail(f"{name} {e.strerror or e}")
sys.exit(1 if failed else 0)
