#!/usr/bin/env python3
"""Windows 專用：把 agy 已安裝 plugin 的 hook 指令改成 shell 絕對路徑。

`agy plugin install` 轉換 hooks.json 時丟掉 `commandWindows`，只留 `sh "./hooks/run-py.sh" …`；
agy 在 Windows 用 cmd 跑 hook，PATH 常沒有 sh，於是每個 hook 都失敗。PreToolUse 有 matcher `.*`，
等於每次工具呼叫都失敗、agy 完全不能用（2026-11-23 實測）。

用法：agy_hooks.py <agy plugins 目錄> <shell bin 目錄> <check|apply> <plugin…>
- 只改 `sh|bash "./<相對路徑>"` 開頭的指令，改成 `"<bin>/sh.exe" "<plugin 根>/<相對路徑>"`；已是絕對路徑的不動（冪等）。
- check：要改的印 `DIFF: agy hooks <p>（N 條…）`；apply：改寫並印 `OK:   agy hooks <p>（改寫 N 條）`。
- 沒有 hooks.json 的 plugin 略過；讀寫或 JSON 錯誤印 `FAIL: …`，exit 1。
"""
import json
import os
import re
import sys
import tempfile

REL = re.compile(r'^(sh|bash) "\./([^"]+)"(.*)$', re.S)


def rewrite(obj, root, bindir):
    n = 0
    if isinstance(obj, dict):
        cmd = obj.get("command")
        if isinstance(cmd, str):
            m = REL.match(cmd)
            if m:
                obj["command"] = f'"{bindir}/{m.group(1)}.exe" "{root}/{m.group(2)}"{m.group(3)}'
                n += 1
        for v in obj.values():
            n += rewrite(v, root, bindir)
    elif isinstance(obj, list):
        for v in obj:
            n += rewrite(v, root, bindir)
    return n


def main(argv):
    if len(argv) < 4 or argv[2] not in ("check", "apply"):
        print("用法：agy_hooks.py <agy plugins 目錄> <shell bin 目錄> <check|apply> <plugin…>", file=sys.stderr)
        return 2
    plugins_dir, bindir, mode, names = argv[0], argv[1].rstrip("/\\"), argv[2], argv[3:]
    failed = False
    for p in names:
        root = os.path.join(plugins_dir, p).replace("\\", "/")
        path = os.path.join(plugins_dir, p, "hooks.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            print(f"FAIL: agy hooks {p}：{e}")
            failed = True
            continue
        n = rewrite(data, root, bindir)
        if n == 0:
            continue
        if mode == "check":
            print(f"DIFF: agy hooks {p}（{n} 條用相對路徑呼叫 sh，Windows 上會失敗；install 會改成絕對路徑）")
            continue
        try:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except OSError as e:
            print(f"FAIL: agy hooks {p}：{e}")
            failed = True
            continue
        print(f"OK:   agy hooks {p}（改寫 {n} 條為絕對路徑）")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
