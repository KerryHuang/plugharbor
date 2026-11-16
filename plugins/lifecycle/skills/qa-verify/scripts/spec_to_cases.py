#!/usr/bin/env python3
"""設計文件的驗收一節 → qa-verify 的案例檔（acceptance-format.md 格式）。

用法：spec_to_cases.py <設計文件> <輸出檔>
認兩種：`## 驗收`（案例 `###`、欄位 `####`）與舊範本 `### 2.3`（案例 `####`、欄位 `#####`）。
原樣轉、不改寫、不補字；缺欄就停。exit 0 成功（stdout 印案例數）、2 用法錯、4 缺欄或格式不符。
"""
import re
import sys
from pathlib import Path

FIELDS = {"前置條件": "前置條件", "前置": "前置條件", "步驟": "步驟", "預期": "預期", "預期結果": "預期"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
CHANNEL_RE = re.compile(r"\s*\[([^\]]+)\]\s*$")
# 與 validate.py 一致：整項內容是 <…>／{…} 才算佔位符（步驟裡的 JSON body、{id} 路徑參數是合法內容）；殘留的 [NEEDS CLARIFICATION 也擋
PLACEHOLDER_RE = re.compile(r"^\s*(<[^<>]+>|\{[^{}]+\})\s*$|\[NEEDS CLARIFICATION")
ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")


FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def fence_step(state, ln):
    """CommonMark fence：回傳 (新狀態, 這行是不是 fence 行)。state＝None 或開啟的 (字元, 長度)。"""
    m = FENCE_RE.match(ln)
    if not m:
        return state, False
    mark, rest = m.group(1), m.group(2)
    if state is None:
        if mark[0] == "`" and "`" in rest:
            return state, False
        return (mark[0], len(mark)), True
    if mark[0] == state[0] and len(mark) >= state[1] and not rest.strip():
        return None, True
    return state, True


def find_section(lines):
    """回傳 (驗收一節的行, 案例標題前綴, 欄位標題前綴)；找不到回 None。起點與終點都略過 fenced code 內的標題。"""
    fence_free = []  # (行號, 行)：fence 外的行
    state = None
    for i, ln in enumerate(lines):
        state, is_fence = fence_step(state, ln)
        if not is_fence and state is None:
            fence_free.append((i, ln))

    def span(start_re, end_re):
        for k, (i, ln) in enumerate(fence_free):
            if re.match(start_re, ln):
                end = next((j for j, l2 in fence_free[k + 1:] if re.match(end_re, l2)), len(lines))
                return lines[i + 1:end]
        return None

    sec = span(r"^##\s+驗收\s*$", r"^##\s")
    if sec is not None:
        return sec, "### ", "#### "
    sec = span(r"^###\s+2\.3(\s|$)", r"^#{1,3}\s")
    if sec is not None:
        return sec, "#### ", "##### "
    return None


def parse(section, case_p, field_p):
    cases, cur, sec, state = [], None, None, None
    for ln in section:
        state, is_fence = fence_step(state, ln)
        if is_fence or state is not None:
            continue
        if ln.startswith(case_p):
            head = ln[len(case_p):].strip()
            m = re.match(r"^(\S+?)(?:[:：]|\s|$)\s*(.*)$", head)
            cur = {"head": head, "id": m.group(1) if m else head, "rest": m.group(2) if m else "",
                   "前置條件": [], "步驟": [], "預期": []}
            cases.append(cur)
            sec = None
        elif ln.startswith(field_p):
            sec = FIELDS.get(ln[len(field_p):].strip())
        elif cur is not None and sec:
            it = ITEM_RE.match(ln)
            if it:
                cur[sec].append(ln.strip())
    return cases


def check(cases):
    errs, seen = [], set()
    for c in cases:
        cid = c["id"]
        if not ID_RE.match(cid):
            errs.append(f"{cid}：id 不是 ASCII（例 AC-01）")
        if cid in seen:
            errs.append(f"{cid}：id 重複")
        seen.add(cid)
        if not CHANNEL_RE.sub("", c["rest"]).strip():
            errs.append(f"{cid}：缺 標題")
        for k in ("步驟", "預期"):
            if not c[k]:
                errs.append(f"{cid}：缺 {k}")
        for k in ("前置條件", "步驟", "預期"):
            if any(PLACEHOLDER_RE.search(ITEM_RE.match(x).group(1)) for x in c[k]):
                errs.append(f"{cid}：{k} 仍是佔位符")
    return errs


def render(cases):
    out = []
    for c in cases:
        out.append(f"## {c['head']}")
        for k in ("前置條件", "步驟", "預期"):
            if c[k]:
                out.append(f"### {k}")
                out.extend(c[k])
        out.append("")
    return "\n".join(out)


def main(argv):
    if len(argv) != 3:
        print("用法: spec_to_cases.py <設計文件> <輸出檔>", file=sys.stderr)
        return 2
    lines = Path(argv[1]).read_text(encoding="utf-8-sig").splitlines()
    found = find_section(lines)
    if not found:
        print("找不到驗收一節（需要 `## 驗收`，或舊範本的 `### 2.3`）", file=sys.stderr)
        return 4
    cases = parse(*found)
    errs = check(cases) if cases else ["驗收一節沒有任何案例"]
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 4
    out = Path(argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(cases), encoding="utf-8")
    print(len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
