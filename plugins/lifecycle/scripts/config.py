#!/usr/bin/env python3
"""讀 lifecycle 的專案設定 `.plugharbor/lifecycle.yml`。

用法：python3 config.py get <key>   （key 用點號，例如 ticket.tool；以目前目錄為專案根）
缺檔、缺鍵（值為空也算）或檔案格式錯誤（YAML 語法、最上層不是對應、非 UTF-8）：退出碼 2，stderr 一行說明。
有預設值的鍵（DEFAULTS）缺檔或缺鍵時回預設值；只有舊檔 delivery-flow.yml 時一律退出碼 2 並提示改名。
"""
import json
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(".plugharbor") / "lifecycle.yml"
OLD_PATH = Path(".plugharbor") / "delivery-flow.yml"
HINT = "請在專案根的 .plugharbor/lifecycle.yml 補上 {key}（範例見 references/config.md）"
RENAME_HINT = "找到舊設定 .plugharbor/delivery-flow.yml：請改名為 .plugharbor/lifecycle.yml（鍵不變）後再跑"
DEFAULTS = {"scale": "lean", "spec.dir": "docs/specs"}


class ConfigMissing(Exception):
    def __init__(self, key, hint):
        super().__init__(f"{key}: {hint}")
        self.key = key
        self.hint = hint


def load_config(root: Path, key: str = "ticket.tool") -> dict:
    path = Path(root) / CONFIG_PATH
    if not path.is_file():
        if (Path(root) / OLD_PATH).is_file():
            raise ConfigMissing("(rename)", RENAME_HINT)
        raise ConfigMissing("(file)", HINT.format(key=key))
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        raise ConfigMissing("(format)", f"{CONFIG_PATH} 格式錯誤：不是 UTF-8 編碼，請另存為 UTF-8")
    except yaml.YAMLError as e:
        msg = " ".join(str(e).split())
        raise ConfigMissing("(format)", f"{CONFIG_PATH} 格式錯誤：{msg}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigMissing("(format)", f"{CONFIG_PATH} 格式錯誤：最上層必須是 key: value 的對應，不是 {type(data).__name__}")
    return data


def require(cfg: dict, key: str):
    node = cfg
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigMissing(key, HINT.format(key=key))
        node = node[part]
    if node is None or node == "":
        raise ConfigMissing(key, HINT.format(key=key))
    return node


def main(argv):
    if len(argv) != 3 or argv[1] != "get":
        print("用法：config.py get <key>", file=sys.stderr)
        return 2
    key = argv[2]
    try:
        value = require(load_config(Path.cwd(), key), key)
    except ConfigMissing as e:
        if key not in DEFAULTS or e.key in ("(rename)", "(format)"):
            print(e.hint, file=sys.stderr)
            return 2
        value = DEFAULTS[key]
    print(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
