#!/usr/bin/env python3
"""verify_counts 的測試。直接執行：python3 test_verify_counts.py"""
import json, pathlib, subprocess, sys, tempfile, unittest

SCRIPT = pathlib.Path(__file__).parent / "verify_counts.py"

HTML = """<html><body>
<button class="drill" data-k="a">{shown}</button>
{extra}
<script id="drill-data" type="application/json">{data}</script>
</body></html>"""


def run(shown="2", extra="", data=None, json_data=None):
    data = data or {"a": {"label": "A", "items": [{"id": "X-1"}, {"id": "X-2"}]}}
    with tempfile.TemporaryDirectory() as t:
        p = pathlib.Path(t) / "deck.html"
        p.write_text(HTML.format(shown=shown, extra=extra, data=json.dumps(data)), encoding="utf-8")
        args = [sys.executable, str(SCRIPT), str(p)]
        if json_data is not None:
            j = pathlib.Path(t) / "dataset.json"
            j.write_text(json.dumps(json_data), encoding="utf-8")
            args.append(str(j))
        return subprocess.run(args, capture_output=True, text=True)


class VerifyCountsTest(unittest.TestCase):
    def test_match_passes(self):
        r = run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_number_mismatch_fails(self):
        r = run(shown="3")
        self.assertEqual(r.returncode, 1)
        self.assertIn("頁面顯示 3，清單實為 2", r.stderr)

    def test_button_without_dataset_fails(self):
        r = run(extra='<button class="drill" data-k="ghost">1</button>')
        self.assertEqual(r.returncode, 1)
        self.assertIn("ghost", r.stderr)

    def test_unused_dataset_fails(self):
        data = {"a": {"label": "A", "items": [{"id": "X-1"}, {"id": "X-2"}]},
                "b": {"label": "B", "items": [{"id": "X-3"}]}}
        r = run(data=data)
        self.assertEqual(r.returncode, 1)
        self.assertIn("未被任何按鈕引用", r.stderr)

    def test_json_matching_embedded_passes(self):
        r = run(json_data={"a": {"label": "A", "items": [{"id": "X-1"}, {"id": "X-2"}]}})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_embedded_differs_from_json_fails(self):
        # 頁面內嵌清單（抽屜實際顯示的）與 dataset.json 不同，不能因 json 對得上就放行
        embedded = {"a": {"label": "A", "items": [{"id": "X-1"}, {"id": "X-2"}, {"id": "X-9"}]}}
        r = run(data=embedded, json_data={"a": {"label": "A", "items": [{"id": "X-1"}, {"id": "X-2"}]}})
        self.assertEqual(r.returncode, 1)
        self.assertIn("內嵌", r.stderr)


if __name__ == "__main__":
    unittest.main()
