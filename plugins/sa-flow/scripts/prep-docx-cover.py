# -*- coding: utf-8 -*-
"""把手冊 md 開頭的 H1 ＋ 文件資訊表，改寫成 Word 封面頁。

    python3 prep-docx-cover.py <來源.md> <輸出.md>

pandoc 的 docx 沒有「封面頁」概念。做法是用 fenced div 指定 custom-style
（樣式定義在 manual-reference.docx），結尾插 raw openxml 分頁符——
`\\newpage` 是 LaTeX 語法，docx 不認。
"""
import io, re, sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError（實測）。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

src, out = sys.argv[1], sys.argv[2]
s = io.open(src, encoding="utf-8").read()

m = re.search(r'^#\s+(.+)$', s, re.M)
title = m.group(1).strip().replace("操作手冊：", "") if m else "操作手冊"

tbl = re.search(r'^\|.*\|\n\|[-\s|:]+\|\n(?:\|.*\|\n)+', s, re.M)
meta = {}
if tbl:
    for line in tbl.group(0).strip().split("\n")[2:]:
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 2 and c[0]:
            meta[c[0]] = c[1]

body = re.sub(r'^#\s+.+?\n', '', s, count=1, flags=re.M)
if tbl:
    body = body.replace(tbl.group(0), "", 1)

# 靜態目錄——不用 Word 的 TOC 欄位：那要使用者按 F9 才會展開，
# 客戶開檔看到「請按 F9」會困惑，且 LibreOffice 根本不執行 updateFields。
lines = []
for lv, txt in re.findall(r'^(#{1,2})\s+(.+)$', body, re.M):
    txt = txt.strip()
    lines.append(("%s" if len(lv) == 1 else "　　%s") % txt)
toc = "\n\n".join('::: {custom-style="%s"}\n%s\n:::'
                   % ("TocL1" if not t.startswith("　") else "TocL2", t) for t in lines)

info = "　｜　".join("%s：%s" % (k, v) for k, v in meta.items() if k != "功能名稱")

cover = """::: {custom-style="CoverTitle"}
%s
:::

::: {custom-style="CoverSub"}
操作手冊
:::

::: {custom-style="CoverMeta"}
%s
:::

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

::: {custom-style="TocTitle"}
目　錄
:::

%s

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

""" % (title, info, toc)

io.open(out, "w", encoding="utf-8").write(cover + body.lstrip("\n"))
print("封面：%s（%s）" % (title, info))
