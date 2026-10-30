#!/usr/bin/env python3
"""發布閘門①：驗證簡報上每個可點數字 == 其清單筆數。

用法：verify_counts.py <deck.html> [drill.json]
  drill.json 省略時從 HTML 內嵌的 <script id="drill-data"> 取。

不一致、資料集缺漏、按鈕標籤配對錯誤，任一發生即以 exit code 1 結束。
"""
import json
import re
import sys

BTN = re.compile(r'<button class="drill" data-k="([^"]+)"[^>]*>([^<]*)</button>')
DATA = re.compile(r'<script id="drill-data" type="application/json">(.*?)</script>', re.S)


def load(html_path, json_path):
    html = open(html_path, encoding="utf-8").read()
    if json_path:
        return html, json.load(open(json_path, encoding="utf-8"))
    m = DATA.search(html)
    if not m:
        sys.exit("FAIL: HTML 內找不到 <script id=\"drill-data\">，可點數字不會運作")
    return html, json.loads(m.group(1).replace("<\\/", "</"))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    html, data = load(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    errs, seen = [], set()

    for key, shown in BTN.findall(html):
        seen.add(key)
        if key not in data:
            errs.append(f"按鈕 data-k=\"{key}\" 沒有對應資料集")
            continue
        digits = re.sub(r"\D", "", shown)
        if not digits:
            continue                      # 案名之類的非數字按鈕
        n = len(data[key]["items"])
        if int(digits) != n:
            errs.append(f"{key}: 頁面顯示 {digits}，清單實為 {n}")

    if html.count("<button") != html.count("</button>"):
        errs.append("button 標籤未配對")
    unused = sorted(set(data) - seen)
    if unused:
        errs.append("資料集未被任何按鈕引用（清單白算了）：" + "、".join(unused))

    errs = list(dict.fromkeys(errs))
    if errs:
        print("複驗失敗，不得發布：", file=sys.stderr)
        for e in errs:
            print("  ✗ " + e, file=sys.stderr)
        sys.exit(1)

    total = sum(len(v["items"]) for v in data.values())
    print(f"✓ 複驗通過：{len(seen)} 個可點數字、{len(data)} 個資料集、{total} 筆票，數字與清單一致")


if __name__ == "__main__":
    main()
