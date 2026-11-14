#!/usr/bin/env python3
"""票務工具層中不需要 MCP 的純函式：抽象階段轉工具原生值、GitHub 附圖計畫、送出前外洩檢查。

用法：
  python3 ticket_backend.py stage <stage>   （讀目前目錄的 .plugharbor/lifecycle.yml，輸出 JSON）
    缺設定或階段不合法：退出碼 2，stderr 一行說明。
  python3 ticket_backend.py project-option <stage>   （有設 ticket.project 時印看板對照 JSON，沒設印 null）
  python3 ticket_backend.py leak <檔案>     （用目前目錄 repo 的 .leak-denylist 掃內文）
    0 無命中；4 有命中（stdout 每行 `L<行號> <命中>`）；5 找不到 denylist。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from config import ConfigMissing, load_config, require  # noqa: E402

STAGES = ("backlog", "todo", "in-progress", "in-review", "done", "canceled")
CLOSING = {"done": "completed", "canceled": "not planned"}
ASSET_DIR = ".github/ticket-assets"


def stage_to_native(cfg: dict, stage: str) -> dict:
    name = stage.replace("_", "-")
    if name not in STAGES:
        raise ValueError(f"未知階段 {stage!r}，合法值：{', '.join(STAGES)}")
    tool = require(cfg, "ticket.tool")
    states = require(cfg, "ticket.states")
    if tool in ("linear", "jira"):
        return {"state": require(cfg, f"ticket.states.{name}")}
    if tool == "github":
        close = name in CLOSING
        target = require(cfg, f"ticket.states.{name}")
        # done、canceled 以 closed 表示，對照值不是 label
        labels = {s: states[s] for s in STAGES if s not in CLOSING and states.get(s)}
        result = {
            "labels_add": [] if close else [target],
            "labels_remove": [v for s, v in labels.items() if s != name],
            "close": close,
        }
        if close:
            result["reason"] = CLOSING[name]
        return result
    raise ValueError(f"不支援的 ticket.tool：{tool}（linear、github；jira 僅有設定範例）")


def project_option(cfg: dict, stage: str):
    """GitHub Projects 看板的 Status 選項名；沒設 ticket.project 回 None。"""
    name = stage.replace("_", "-")
    if name not in STAGES:
        raise ValueError(f"未知階段 {stage!r}，合法值：{', '.join(STAGES)}")
    proj = (cfg.get("ticket") or {}).get("project")
    if not proj:
        return None
    opt = (proj.get("options") or {}).get(name)
    if not opt:
        raise ValueError(f"ticket.project.options 缺階段 {name}（要對照到看板 {proj.get('field', 'Status')} 欄位的選項名）")
    return opt


def github_attach_plan(repo: str, image_path: str) -> dict:
    """GitHub 沒有官方圖片上傳 API：圖存進 repo 的 ASSET_DIR，以 markdown 連結內嵌。
    連結只有在檔案 push 到預設分支後才有效。"""
    name = Path(image_path).name.replace(" ", "-")
    location = f"{ASSET_DIR}/{name}"
    url = f"https://github.com/{repo}/blob/HEAD/{quote(location)}?raw=true"
    return {"method": "commit", "location": location, "markdown": f"![{name}]({url})"}


def _main_checkout(root: Path):
    git = root / ".git"
    if not git.is_file():
        return None
    m = re.match(r"gitdir:\s*(.+)", git.read_text(encoding="utf-8").strip())
    return Path(m.group(1)).resolve().parents[2] if m else None


def load_denylist(root: Path):
    """讀 root/.leak-denylist（worktree 裡沒有就讀主 checkout 那份）；都沒有回 None。
    解析規則與 plugharbor repo 的 CI 外洩檢查相同（由測試比對）。"""
    f = root / ".leak-denylist"
    if not f.exists() and (main := _main_checkout(root)):
        f = main / ".leak-denylist"
    if not f.exists():
        return None
    pats = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(re.compile(line[6:] if line.startswith("regex:") else re.escape(line), re.I))
    return pats


def scan_leaks(text: str, patterns) -> list:
    return [(n, m.group(0)) for n, line in enumerate(text.split("\n"), 1)
            for p in patterns for m in p.finditer(line)]


def leak_main(path: str) -> int:
    pats = load_denylist(Path.cwd())
    if pats is None:
        print("找不到 .leak-denylist（repo 根目錄或主 checkout）", file=sys.stderr)
        return 5
    hits = scan_leaks(Path(path).read_text(encoding="utf-8"), pats)
    for n, s in hits:
        print(f"L{n} {s}")
    return 4 if hits else 0


def main(argv):
    if len(argv) == 3 and argv[1] == "leak":
        return leak_main(argv[2])
    if len(argv) != 3 or argv[1] not in ("stage", "project-option"):
        print("用法：ticket_backend.py stage <stage>｜project-option <stage>｜leak <檔案>", file=sys.stderr)
        return 2
    if argv[1] == "project-option":
        try:
            cfg = load_config(Path.cwd(), "ticket.states")
            opt = project_option(cfg, argv[2])
        except (ConfigMissing, ValueError) as e:
            print(e.hint if isinstance(e, ConfigMissing) else e, file=sys.stderr)
            return 3 if isinstance(e, ConfigMissing) and e.key == "(rename)" else 2
        proj = cfg["ticket"].get("project") or {}
        print(json.dumps(opt and {"owner": proj["owner"], "number": proj["number"],
                                  "field": proj.get("field", "Status"), "option": opt}, ensure_ascii=False))
        return 0
    try:
        print(json.dumps(stage_to_native(load_config(Path.cwd(), "ticket.states"), argv[2]), ensure_ascii=False))
    except (ConfigMissing, ValueError) as e:
        print(e.hint if isinstance(e, ConfigMissing) else e, file=sys.stderr)
        return 3 if isinstance(e, ConfigMissing) and e.key == "(rename)" else 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
