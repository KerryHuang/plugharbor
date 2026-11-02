# -*- coding: utf-8 -*-
"""手冊封面的品牌文字：--brand 優先，其次設定 manual-brand，都沒有就是空字串（不寫任何品牌）。"""
import subprocess
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "config.py"


def resolve_brand(cli_brand):
    if cli_brand is not None:
        return cli_brand.strip()
    r = subprocess.run([sys.executable, str(CONFIG), "get", "manual-brand"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return ""  # 退出碼 2：沒設定，不是錯誤
    value = r.stdout.strip()
    return "" if value[:1] in "{[" else value  # manual-brand 只收字串
