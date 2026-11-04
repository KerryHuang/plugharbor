#!/usr/bin/env python3
"""票務工具層中不需要 MCP 的純函式：抽象階段轉工具原生值、GitHub 附圖計畫。

用法：python3 ticket_backend.py stage <stage>   （讀目前目錄的 .plugharbor/lifecycle.yml，輸出 JSON）
缺設定或階段不合法：退出碼 2，stderr 一行說明。
"""
import json
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


def github_attach_plan(repo: str, image_path: str) -> dict:
    """GitHub 沒有官方圖片上傳 API：圖存進 repo 的 ASSET_DIR，以 markdown 連結內嵌。
    連結只有在檔案 push 到預設分支後才有效。"""
    name = Path(image_path).name.replace(" ", "-")
    location = f"{ASSET_DIR}/{name}"
    url = f"https://github.com/{repo}/blob/HEAD/{quote(location)}?raw=true"
    return {"method": "commit", "location": location, "markdown": f"![{name}]({url})"}


def main(argv):
    if len(argv) != 3 or argv[1] != "stage":
        print("用法：ticket_backend.py stage <stage>", file=sys.stderr)
        return 2
    try:
        print(json.dumps(stage_to_native(load_config(Path.cwd(), "ticket.states"), argv[2]), ensure_ascii=False))
    except (ConfigMissing, ValueError) as e:
        print(e.hint if isinstance(e, ConfigMissing) else e, file=sys.stderr)
        return 3 if isinstance(e, ConfigMissing) and e.key == "(rename)" else 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
