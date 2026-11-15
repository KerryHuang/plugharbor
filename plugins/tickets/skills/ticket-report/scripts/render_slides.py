#!/usr/bin/env python3
"""把簡報草稿組成會議簡報 HTML：模型只寫文案，數字與清單由程式從 dataset 產生。

用法：render_slides.py <draft.md> <dataset.json> <out.html>
草稿語法見 references/weekly-outputs.md。草稿有錯時一次列出全部，不寫出檔案，exit 1。
"""
import html
import json
import pathlib
import re
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "references" / "drawer-template.html"
TOKEN = re.compile(r"\{\{([^{}|]+)(?:\|([^{}]*))?\}\}")
HEADING = re.compile(r"^## (.+?)(?:\s*\[(\d+)\])?$")
STAT = re.compile(r"^@\s+(.+?)\s+(\{\{[^{}]+\}\})$")
STAT_EXAMPLE = "@ 交付 {{delivered}}"


def render(draft, data):
    """回傳 (title, body_html, errors)；errors 每筆是 (行號或 None, 訊息, 範例或 None)。"""
    errors, used, out, open_tag = [], set(), [], None
    title, minutes = None, []

    def close():
        nonlocal open_tag
        if open_tag:
            out.append(open_tag)
            open_tag = None

    def ensure(start, end):
        nonlocal open_tag
        if open_tag != end:
            close()
            out.append(start)
            open_tag = end

    def inline(text, no):
        def button(m):
            key, label = html.unescape(m.group(1)).strip(), m.group(2)
            d = data.get(key)
            if d is None:
                errors.append((no, f"找不到資料集「{key}」（可用：{'、'.join(data)}）", STAT_EXAMPLE))
                return ""
            used.add(key)
            if label is not None and re.search(r"\d", label):
                # verify_counts 會把按鈕文字裡的數字當成筆數比對
                errors.append((no, f"按鈕文字「{html.unescape(label)}」含數字，會被當成筆數比對", "{{key|成品出庫}}，代碼寫在按鈕外"))
                return ""
            items = d.get("items") if isinstance(d, dict) else None
            shown = label if label else str(len(items) if isinstance(items, list) else 0)
            return f'<button class="drill" data-k="{html.escape(key)}">{shown}</button>'

        text = TOKEN.sub(button, html.escape(text))
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    for no, raw in enumerate(draft.splitlines(), 1):
        line = raw.strip()
        if not line:
            close()
        elif line.startswith("## "):
            close()
            m = HEADING.match(line)
            tag = ""
            if m.group(2):
                minutes.append(int(m.group(2)))
                tag = f' <span class="min">{m.group(2)} 分</span>'
            out.append(f"<h2>{inline(m.group(1), no)}{tag}</h2>")
        elif line.startswith("# "):
            close()
            title = line[2:].strip()
            out.append(f"<h1>{html.escape(title)}</h1>")
        elif line.startswith("> "):
            close()
            out.append(f'<p class="sub">{inline(line[2:], no)}</p>')
        elif line.startswith("@"):
            m = STAT.match(line)
            if not m:
                errors.append((no, "統計列要是「@ 標籤 {{資料集}}」", STAT_EXAMPLE))
                continue
            ensure('<div class="stats">', "</div>")
            out.append(f'<div class="stat"><span class="lbl">{inline(m.group(1), no)}</span>{inline(m.group(2), no)}</div>')
        elif line.startswith("- "):
            ensure("<ul>", "</ul>")
            out.append(f"<li>{inline(line[2:], no)}</li>")
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", c) for c in cells):
                continue
            head = open_tag != "</table>"
            ensure("<table>", "</table>")
            cell = "th" if head else "td"
            out.append("<tr>" + "".join(f"<{cell}>{inline(c, no)}</{cell}>" for c in cells) + "</tr>")
        else:
            close()
            out.append(f"<p>{inline(line, no)}</p>")
    close()

    if title is None:
        errors.append((None, "缺少 `# 標題`", "# 週會簡報"))
    if minutes and sum(minutes) != 30:
        errors.append((None, f"分鐘加總 {sum(minutes)}，議程固定 30", "## 卡點決策 [8]"))
    for key, d in data.items():
        if not (isinstance(d, dict) and isinstance(d.get("items"), list)):
            errors.append((None, f"資料集「{key}」沒有 items 陣列", None))
        if key not in used:
            errors.append((None, f"資料集「{key}」沒有被任何按鈕引用", f"@ 標籤 {{{{{key}}}}}"))
    return title, "\n".join(out), errors


def fill(template, title, body, data):
    embedded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "\\u003c!--")
    parts = [
        (r"<title>.*?</title>", f"<title>{html.escape(title)}</title>"),
        (r"(?<=<body>\n).*?(?=<aside id=\"drawer\")", body + "\n\n"),
        (r"(?<=<script id=\"drill-data\" type=\"application/json\">\n).*?(?=\n</script>)", embedded),
    ]
    for pattern, value in parts:
        template, n = re.subn(pattern, lambda _: value, template, count=1, flags=re.S)
        if n != 1:
            sys.exit(f"FAIL: drawer-template.html 找不到要替換的區段：{pattern}")
    return template


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    draft = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    data = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
    title, body, errors = render(draft, data)
    if errors:
        for no, message, example in errors:
            print(f"✗ {f'L{no} ' if no else ''}{message}", file=sys.stderr)
            if example:
                print(f"  正確範例：{example}", file=sys.stderr)
        print(f"✗ {len(errors)} 個錯誤；沒有寫出簡報", file=sys.stderr)
        sys.exit(1)
    out = pathlib.Path(sys.argv[3])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fill(TEMPLATE.read_text(encoding="utf-8"), title, body, data), encoding="utf-8")
    print(f"✓ {out}")


if __name__ == "__main__":
    main()
