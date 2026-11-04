#!/usr/bin/env python3
"""發布閘門①：驗證簡報上每個可點數字 == 其清單筆數。

用法：verify_counts.py <deck.html> [drill.json]
  一律驗 HTML 內嵌的 <script id="drill-data">；給了 drill.json 時兩者須相同。

不一致、資料集缺漏、按鈕標籤配對錯誤，任一發生即以 exit code 1 結束。
"""
import json
import re
import sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

BTN = re.compile(r'<button class="drill" data-k="([^"]+)"[^>]*>([^<]*)</button>')
DATA = re.compile(r'<script id="drill-data" type="application/json">(.*?)</script>', re.S)


def load(html_path, json_path):
    html = open(html_path, encoding="utf-8").read()
    m = DATA.search(html)
    if not m:
        sys.exit("FAIL: HTML 內找不到 <script id=\"drill-data\">，可點數字不會運作")
    embedded = json.loads(m.group(1).replace("<\\/", "</"))
    if json_path:
        # 抽屜顯示的是內嵌資料；與 dataset.json 不同時，對 json 驗過也不代表頁面正確
        if json.load(open(json_path, encoding="utf-8")) != embedded:
            sys.exit("FAIL: HTML 內嵌的 drill-data 與 dataset.json 不一致，請重新嵌入")
    return html, embedded


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
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
