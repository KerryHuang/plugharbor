#!/usr/bin/env python3
"""操作手冊圖文比：正文字數 ÷ 圖片數。

用法:
    python3 text-image-ratio.py <手冊.md> [<手冊2.md> ...]

判準：200～400 通過；400～600 提醒；>600 不過（參考標竿 169）。

## 為什麼要有這支腳本

早期 `manual-reviewer` 用的是 `len(整份檔案) / 圖片數`，**那是錯的**：
分子含 markdown 語法、表格框線、空白、以及每張圖那串
`![a01 主控台，紅框處為…](images/a01-dashboard-entry.png)`（60~90 字元）。

後果不只是數字偏高，是**方向錯了**——每補一張圖，分子跟著變大，
這個指標反而懲罰補圖，與它的設計用意相反。

實測同一批檔：舊算式 445、新算式 276；另一份 371 → 225。
曾據舊算式的 445 提議放寬 200～400 的判準，**差點因為量錯而放寬一條有效判準**。

## 算法（定義死，不要再各自發明）

分子：剝除圖片語法、程式碼區塊、HTML 註解後，計 CJK 與英數字元
      （`[一-鿿＀-￯A-Za-z0-9]`）——不計標點、空白、markdown 符號。
分母：行首 `![` 的出現次數。
"""
import io
import re
import sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError（實測）。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

IMG_LINE = re.compile(r"^!\[", re.M)
IMG_INLINE = re.compile(r"!\[.*?\]\(.*?\)", re.S)
CODE_FENCE = re.compile(r"```.*?```", re.S)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
COUNTED = re.compile(r"[一-鿿＀-￯ A-Za-z0-9]".replace(" ", ""))


def ratio(path):
    raw = io.open(path, encoding="utf-8").read()
    images = len(IMG_LINE.findall(raw))
    body = HTML_COMMENT.sub("", CODE_FENCE.sub("", IMG_INLINE.sub("", raw)))
    chars = len(COUNTED.findall(body))
    return chars, images, (chars // images if images else 0)


def verdict(r):
    if r == 0:
        return "無圖", 1
    if r > 600:
        return "不過", 1
    if r > 400:
        return "提醒", 0
    if r < 200:
        return "偏少（圖多於字，通常沒問題，確認每張圖都有被正文指到）", 0
    return "通過", 0


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    worst = 0
    for p in sys.argv[1:]:
        chars, images, r = ratio(p)
        v, bad = verdict(r)
        worst = max(worst, bad)
        print(f"{p}\n  正文 {chars} 字 / {images} 圖 = 每圖 {r} 字 → {v}")
    sys.exit(worst)


if __name__ == "__main__":
    main()
