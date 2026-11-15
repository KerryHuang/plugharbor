#!/usr/bin/env python3
"""render_slides 的測試。直接執行：python3 test_render_slides.py"""
import json, pathlib, re, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).parent
RENDER = HERE / "render_slides.py"
VERIFY = HERE / "verify_counts.py"

DATA = {
    "delivered": {"label": "上週交付", "note": "n", "items": [{"id": "D-1", "title": "甲"}, {"id": "D-2", "title": "乙"}]},
    "review": {"label": "等驗收", "items": [{"id": "D-3", "title": "丙"}]},
}
DRAFT = """# 週會簡報
> 週會日 2026-01-05

## 上週定調 [3]
上週**交付**偏少。

@ 交付 {{delivered}}
@ 等驗收 {{review}}

## 其他 [27]
- 第一點，共 {{review}} 張
| 來源 | 期限 |
|---|---|
| 卡點 | 01-09 |
"""


def run(draft=DRAFT, data=None):
    data = DATA if data is None else data
    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t)
        (d / "draft.md").write_text(draft, encoding="utf-8")
        (d / "dataset.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        out = d / "sub" / "slides.html"
        r = subprocess.run([sys.executable, str(RENDER), str(d / "draft.md"), str(d / "dataset.json"), str(out)],
                           capture_output=True, encoding="utf-8")
        html = out.read_text(encoding="utf-8") if out.exists() else None
        v = None
        if html is not None:
            v = subprocess.run([sys.executable, str(VERIFY), str(out), str(d / "dataset.json")],
                               capture_output=True, encoding="utf-8")
        return r, html, v


class RenderSlidesTest(unittest.TestCase):
    def test_output_passes_the_publish_gate(self):
        r, html, v = run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(v.returncode, 0, v.stderr)

    def test_counts_come_from_dataset_not_draft(self):
        _, html, _ = run()
        self.assertIn('<button class="drill" data-k="delivered">2</button>', html)
        self.assertEqual(html.count('data-k="review">1</button>'), 2)

    def test_draft_content_is_rendered(self):
        _, html, _ = run()
        self.assertIn("<title>週會簡報</title>", html)
        self.assertIn('<p class="sub">週會日 2026-01-05</p>', html)
        self.assertRegex(html, r'<h2>上週定調 <span class="min">3 分</span></h2>')
        self.assertIn("<strong>交付</strong>", html)
        self.assertIn('<span class="lbl">交付</span>', html)
        self.assertIn("<li>第一點", html)
        self.assertIn("<th>來源</th>", html)
        self.assertIn("<td>01-09</td>", html)

    def test_template_sample_data_is_gone(self):
        _, html, _ = run()
        self.assertNotIn("DEMO-1", html)
        self.assertNotIn("範例資料", html)

    def test_draft_text_cannot_inject_html(self):
        r, html, _ = run(DRAFT.replace("上週**交付**偏少。", "<img src=x onerror=alert(1)> {{delivered}}"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_dataset_cannot_close_the_script_tag(self):
        data = json.loads(json.dumps(DATA))
        data["review"]["items"][0]["title"] = "</script><script>alert(1)</script><!--"
        r, html, v = run(data=data)
        self.assertEqual(r.returncode, 0, r.stderr)
        embedded = re.search(r'id="drill-data"[^>]*>(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("</script", embedded)
        self.assertNotIn("<!--", embedded)
        self.assertEqual(v.returncode, 0, v.stderr)

    def test_drawer_only_links_http_urls(self):
        _, html, _ = run()
        self.assertIn(r"/^https?:\/\//i.test(it.url)", html)

    def test_label_form_for_non_numeric_button(self):
        r, html, v = run(DRAFT.replace("第一點，共 {{review}} 張", "案子 {{review|成品出庫}}"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('data-k="review">成品出庫</button>', html)
        self.assertEqual(v.returncode, 0, v.stderr)

    def test_all_errors_are_listed_with_line_and_example_and_nothing_written(self):
        bad = DRAFT.replace("@ 交付 {{delivered}}", "@ 交付 {{nope}}") \
            .replace("第一點，共 {{review}} 張", "{{review|INV-050}} {{other}}")
        r, html, _ = run(bad)
        self.assertEqual(r.returncode, 1)
        self.assertIsNone(html)
        self.assertRegex(r.stderr, r"(?m)^✗ L7 找不到資料集「nope」")
        self.assertRegex(r.stderr, r"(?m)^✗ L11 按鈕文字「INV-050」含數字")
        self.assertRegex(r.stderr, r"(?m)^✗ L11 找不到資料集「other」")
        self.assertIn("正確範例：", r.stderr)
        self.assertRegex(r.stderr, r"(?m)^✗ \d+ 個錯誤；沒有寫出簡報$")

    def test_unused_dataset_is_an_error(self):
        r, html, _ = run("# 標題\n\n只有 {{review}}\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("「delivered」沒有被任何按鈕引用", r.stderr)
        self.assertIsNone(html)

    def test_minutes_must_total_30(self):
        r, html, _ = run(DRAFT.replace("## 其他 [27]", "## 其他 [20]"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("分鐘加總 23", r.stderr)
        self.assertIsNone(html)

    def test_missing_title_and_broken_dataset(self):
        r, _, _ = run("沒有標題 {{review}} {{delivered}}\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("缺少 `# 標題`", r.stderr)
        r, _, _ = run(data={"review": {"label": "x"}, "delivered": DATA["delivered"]})
        self.assertEqual(r.returncode, 1)
        self.assertIn("「review」沒有 items 陣列", r.stderr)


if __name__ == "__main__":
    unittest.main()
