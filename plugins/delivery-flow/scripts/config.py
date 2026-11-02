#!/usr/bin/env python3
"""讀 delivery-flow 的專案設定 `.plugharbor/delivery-flow.yml`。

用法：python3 config.py get <key>   （key 用點號，例如 ticket.tool；以目前目錄為專案根）
缺檔或缺鍵：退出碼 2，stderr 一行建檔指引。
"""
import json
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(".plugharbor") / "delivery-flow.yml"
HINT = "請在專案根建立 .plugharbor/delivery-flow.yml 並補上 {key}（範例見 references/config.md）"


class ConfigMissing(Exception):
    def __init__(self, key, hint):
        super().__init__(f"{key}: {hint}")
        self.key = key
        self.hint = hint


def load_config(root: Path) -> dict:
    path = Path(root) / CONFIG_PATH
    if not path.is_file():
        raise ConfigMissing("(file)", HINT.format(key="ticket.tool"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def require(cfg: dict, key: str):
    node = cfg
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigMissing(key, HINT.format(key=key))
        node = node[part]
    return node


def main(argv):
    if len(argv) != 3 or argv[1] != "get":
        print("用法：config.py get <key>", file=sys.stderr)
        return 2
    try:
        value = require(load_config(Path.cwd()), argv[2])
    except ConfigMissing as e:
        print(e.hint, file=sys.stderr)
        return 2
    print(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
