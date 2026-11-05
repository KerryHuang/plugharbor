#!/usr/bin/env python3
"""plugin-harvest 的確定性工具：網址拆解、鎖定檔（harvest-lock.json）寫入與上游檢查。

  harvest.py parse-url <url>
  harvest.py lock add <lock檔> --url U --clone DIR --version V --license L --target P:S [--date D]
  harvest.py lock check <lock檔>      # 全 SAME exit 0；有變動或連不到 exit 3

只用標準庫與 git CLI。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path

LICENSE_RE = re.compile(r"(license|licence|copying|unlicense)([-.].*)?", re.I)
TIMEOUT = 60


@dataclass
class Source:
    clone_url: str
    ref: str
    subpath: str
    key: str


class UrlError(ValueError):
    pass


def parse_url(url: str) -> Source:
    url = url.strip()
    if re.match(r"^(/|~|\.{1,2}[\\/]|[A-Za-z]:[\\/])", url):
        p = str(Path(os.path.expanduser(url)).resolve())
        return Source(p, "", "", p.replace("\\", "/").lower())
    ssh = re.fullmatch(r"[\w.-]+@([\w.-]+):(.+)", url)
    if ssh:
        url = f"https://{ssh.group(1)}/{ssh.group(2)}"
    elif "://" not in url and re.match(r"^[\w-]+(\.[\w-]+)+/", url):
        url = "https://" + url
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.netloc or re.search(r"\s", url):
        raise UrlError(f"無法解析的網址：{url}")
    host = u.netloc.lower().removeprefix("www.")
    path = u.path.strip("/")
    ref = subpath = ""
    t = re.search(r"/(?:-/)?(tree|blob)/", path)
    if t:
        path, rest = path[:t.start()], path[t.end():].strip("/")
        ref, _, subpath = rest.partition("/")
        if t.group(1) == "blob":
            subpath = subpath.rpartition("/")[0]
    if path.endswith(".git"):
        path = path[:-4]
    if len(path.split("/")) < 2:
        raise UrlError(f"網址缺 owner/repo：{url}")
    key = "/".join(x for x in (path, subpath) if x).lower()
    if host != "github.com":
        key = f"{host}/{key}"
    return Source(f"https://{host}/{path}.git", ref, subpath, key)


def git(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=TIMEOUT, env=env)


def license_info(clone: str) -> tuple[str | None, str | None]:
    """HEAD 根目錄的授權檔（可能多個，如雙授權）：回傳 ("A, B", "blobA,blobB")，沒有就 (None, None)。"""
    r = git("ls-tree", "HEAD", cwd=clone)
    if r.returncode != 0:
        raise RuntimeError(f"git ls-tree 失敗：{r.stderr.strip()}")
    found = []
    for line in r.stdout.splitlines():
        meta, _, name = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob" and LICENSE_RE.fullmatch(name):
            found.append((name, parts[2]))
    if not found:
        return None, None
    found.sort()
    return ", ".join(n for n, _ in found), ",".join(b for _, b in found)


class LockError(ValueError):
    pass


def load(lock: Path) -> dict:
    if not lock.exists():
        return {"entries": []}
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
        for e in data["entries"]:
            for k in ("key", "clone_url", "ref", "commit"):
                e[k]
    except (ValueError, KeyError, TypeError) as ex:
        raise LockError(f"鎖定檔格式壞了：{lock}（{type(ex).__name__}: {ex}）") from ex
    return data


def save(lock: Path, data: dict) -> None:
    data["entries"].sort(key=lambda e: e["key"])
    lock.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lock_add(a: argparse.Namespace) -> int:
    src = parse_url(a.url)
    r = git("rev-parse", "HEAD", cwd=a.clone)
    if r.returncode != 0:
        print(f"讀不到 {a.clone} 的 HEAD：{r.stderr.strip()}", file=sys.stderr)
        return 1
    lf, lb = license_info(a.clone)
    lock = Path(a.lock)
    data = load(lock)
    fields = {**asdict(src), "version": a.version, "commit": r.stdout.strip(), "license": a.license,
              "license_file": lf, "license_blob": lb,
              "adopted": a.date or datetime.date.today().isoformat()}
    old = next((e for e in data["entries"] if e["key"] == src.key), None)
    if old:
        old.update(fields)
        old["targets"] = sorted(set(old.get("targets", [])) | {a.target})
        print(f"UPDATED {src.key}")
    else:
        data["entries"].append({**fields, "targets": [a.target]})
        print(f"ADDED {src.key}")
    save(lock, data)
    return 0


def remote_sha(e: dict) -> str | None:
    want = e["ref"] or "HEAD"
    try:
        r = git("ls-remote", e["clone_url"], want, want + "^{}")
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    refs = dict(reversed(line.split("\t", 1)) for line in r.stdout.splitlines() if "\t" in line)
    for name in (want, f"refs/heads/{want}", f"refs/tags/{want}^{{}}", f"refs/tags/{want}"):
        if name in refs:
            return refs[name]
    return None


def remote_license(e: dict) -> tuple[str | None, str | None] | None:
    d = tempfile.mkdtemp(prefix="harvest-")
    try:
        args = ["clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout"] + \
            (["--branch", e["ref"]] if e["ref"] else [])
        r = git(*args, e["clone_url"], os.path.join(d, "repo"))
        if r.returncode != 0:
            return None
        return license_info(os.path.join(d, "repo"))
    except (subprocess.TimeoutExpired, RuntimeError):
        return None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def lock_check(a: argparse.Namespace) -> int:
    lock = Path(a.lock)
    if not lock.exists():
        print("NO-LOCK")
        return 0
    changed = False
    for e in load(lock)["entries"]:
        if re.fullmatch(r"[0-9a-f]{7,40}", e["ref"]) and e["commit"].startswith(e["ref"]):
            print(f"PINNED {e['key']} {e['ref'][:7]}")
            continue
        sha = remote_sha(e)
        if sha is None:
            print(f"UNREACHABLE {e['key']} {e['clone_url']}")
            changed = True
            continue
        if sha == e["commit"]:
            print(f"SAME {e['key']}")
            continue
        changed = True
        move = f"{e['commit'][:7]} -> {sha[:7]}"
        lic = remote_license(e)
        if lic is None:
            print(f"UPDATED {e['key']} {move}（授權檔無法取得：clone 失敗）")
        elif lic != (e.get("license_file"), e.get("license_blob")):
            print(f"LICENSE-CHANGED {e['key']} {e.get('license_file') or '無'} -> {lic[0] or '無'}（commit {move}）")
        else:
            print(f"UPDATED {e['key']} {move}")
    return 3 if changed else 0


def main(argv: list[str]) -> int:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="harvest.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse-url").add_argument("url")
    lk = sub.add_parser("lock").add_subparsers(dest="lcmd", required=True)
    ad = lk.add_parser("add")
    ad.add_argument("lock")
    for f in ("--url", "--clone", "--version", "--license", "--target"):
        ad.add_argument(f, required=True)
    ad.add_argument("--date")
    lk.add_parser("check").add_argument("lock")
    a = p.parse_args(argv)
    try:
        if a.cmd == "parse-url":
            print(json.dumps(asdict(parse_url(a.url)), ensure_ascii=False))
            return 0
        return lock_add(a) if a.lcmd == "add" else lock_check(a)
    except (UrlError, LockError) as ex:
        print(ex, file=sys.stderr)
        return 2
    except RuntimeError as ex:
        print(ex, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
