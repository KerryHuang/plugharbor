"""check-decision-propagation.py 的 R5（暫定標記）與 R6（版本＝CHANGELOG）測試，各有應通過與應失敗案例。

跑法：python3 -m unittest discover -s plugins/sdlc/skills/verifying-specs/scripts -p 'test_*.py'
"""
import importlib.util
import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

_spec = importlib.util.spec_from_file_location(
    "cdp", pathlib.Path(__file__).with_name("check-decision-propagation.py"))
cdp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdp)

HEADER_NEW = "| # | 決策 | 選定 | 否決的選項與原因 | 依據 | 拍板 | 階段 | 日期 | 狀態 |\n|---|---|---|---|---|---|---|---|---|\n"
HEADER_OLD = "| # | 決策 | 選定 | 否決的選項與原因 | 依據 | 拍板 | 階段 | 日期 |\n|---|---|---|---|---|---|---|---|\n"


def frd(body: str, version: str = "1.1", changelog: str = "| v1.0 | 初版 | 2026-10-01 | 建立 |\n| v1.1 | — | 2026-10-02 | 改 |\n",
        changelog_on_top: bool = False) -> str:
    cl = f"<!-- CHANGELOG -->\n| 版本 | Ticket | 日期 | 修改摘要 |\n|---|---|---|---|\n{changelog}<!-- /CHANGELOG -->\n"
    main = (f"# 測試_需求文件\n\n| 項目 | 內容 |\n|---|---|\n| 版本 | {version} |\n\n"
            f"## 1. 需求\n\n{body}\n\n## D. 決策紀錄\n\n| # | 決策 | 選定 |\n|---|---|---|\n"
            f"| D-001 | 甲 | A |\n| D-002 | 乙 | B |\n\n## 9. 附錄\n")
    return cl + main if changelog_on_top else main + cl


class Base(unittest.TestCase):
    def run_check(self, decisions: str, doc: str):
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            (base / "decisions.md").write_text(decisions, encoding="utf-8")
            (base / "測試_需求文件.md").write_text(doc, encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cdp.main(["x", str(base)])
            return code, buf.getvalue()


class R5Provisional(Base):
    DEC = HEADER_NEW + ("| D-001 | 甲 | A | 無其他方案 | 實資料 | PO | FRD | 2026-10-01 | 定案 |\n"
                        "| D-002 | 乙 | B | C——成本高 | 實資料 | SA | FRD | 2026-10-01 | 暫定 |\n")

    def test_pass_provisional_marked_everywhere(self):
        code, out = self.run_check(self.DEC, frd("依 D-001 計算；空值顯示 0（暫定，D-002 待確認）。"))
        self.assertEqual(code, 0, out)

    def test_fail_provisional_bare_reference(self):
        code, out = self.run_check(self.DEC, frd("依 D-001 計算；空值規則見 D-002。"))
        self.assertEqual(code, 1)
        self.assertIn("[R5] D-002", out)
        self.assertIn("未帶", out)

    def test_fail_one_marked_one_bare_on_same_line(self):
        code, out = self.run_check(self.DEC, frd("（暫定，D-002 待確認）另見 D-002。"))
        self.assertIn("[R5] D-002", out)

    def test_fail_decided_with_leftover_mark(self):
        code, out = self.run_check(self.DEC, frd("依 D-001（暫定，D-001 待確認）；（暫定，D-002 待確認）"))
        self.assertEqual(code, 1)
        self.assertIn("[R5] D-001", out)
        self.assertIn("殘留", out)

    def test_skip_when_old_chain_has_no_status_column(self):
        old = HEADER_OLD + ("| D-001 | 甲 | A | 無其他方案 | 實資料 | PO | FRD | 2026-10-01 |\n"
                            "| D-002 | 乙 | B | C——成本高 | 實資料 | SA | FRD | 2026-10-01 |\n")
        code, out = self.run_check(old, frd("依 D-001；見 D-002。"))
        self.assertEqual(code, 0, out)
        self.assertNotIn("R5", out)

    def test_status_column_order_does_not_shift_stage(self):
        rows = cdp.parse_decisions(self.DEC)
        self.assertEqual(rows, [("001", "frd", "定案"), ("002", "frd", "暫定")])


class R6Version(Base):
    DEC = HEADER_OLD + ("| D-001 | 甲 | A | 無其他方案 | 實資料 | PO | FRD | 2026-10-01 |\n"
                        "| D-002 | 乙 | B | 無其他方案 | 實資料 | PO | FRD | 2026-10-01 |\n")

    def test_pass_header_equals_latest_changelog(self):
        code, out = self.run_check(self.DEC, frd("D-001、D-002", version="1.1"))
        self.assertEqual(code, 0, out)

    def test_fail_header_behind_changelog(self):
        code, out = self.run_check(self.DEC, frd("D-001、D-002", version="1.0"))
        self.assertEqual(code, 1)
        self.assertIn("[R6]", out)
        self.assertIn("1.0 ≠ CHANGELOG 最高版本 1.1", out)

    def test_pass_descending_changelog_on_top(self):
        desc = "| v1.10 | — | 2026-10-03 | 改 |\n| v1.9 | — | 2026-10-02 | 改 |\n"
        code, out = self.run_check(self.DEC, frd("D-001、D-002", version="1.10", changelog=desc, changelog_on_top=True))
        self.assertEqual(code, 0, out)

    def test_skip_without_header_version(self):
        doc = frd("D-001、D-002").replace("| 版本 | 1.1 |\n", "")
        code, out = self.run_check(self.DEC, doc)
        self.assertEqual(code, 0, out)


class BodyText(unittest.TestCase):
    def test_changelog_on_top_keeps_body_for_r1(self):
        doc = frd("引用 D-003", changelog_on_top=True)
        self.assertIn("003", cdp.body_ids(doc))

    def test_line_numbers_match_original(self):
        doc = frd("第一段\n（暫定，D-002 待確認）", changelog_on_top=True)
        original = next(i for i, l in enumerate(doc.splitlines(), 1) if "暫定，D-002" in l)
        gaps = cdp.provisional_gaps(cdp.body_text(doc), {"002": "定案"})
        self.assertEqual([g[1] for g in gaps], [original])


if __name__ == "__main__":
    unittest.main()
