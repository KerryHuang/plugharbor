# 測試：python -m unittest discover -s <本目錄> -p "test_*.py"
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardcode_scan import scan  # noqa: E402


class HardcodeScan(unittest.TestCase):
    def kinds(self, name, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / name
            p.write_text(text, encoding="utf-8")
            return sorted({h[0] for h in scan([Path(d)])})

    def test_machine_values_are_found(self):
        self.assertEqual(self.kinds("r.md", "裝在 D:\\Tools\\x"), ["drive-path"])
        self.assertEqual(self.kinds("r.md", "跑 /e/Repos/app"), ["drive-path"])
        self.assertEqual(self.kinds("r.md", "見 /home/user/x"), ["home-path"])
        self.assertEqual(self.kinds("r.md", "連 100.101" + ".5.6"), ["private-ip"])
        self.assertEqual(self.kinds("r.md", "寄 bob@corp.test"), ["email"])
        self.assertEqual(self.kinds("r.md", "開 localhost:5173"), ["localhost-port"])
        self.assertEqual(self.kinds("r.md", "存 /var/folders/ab/T/x"), ["tmp-path"])
        self.assertEqual(self.kinds("r.md", "連 172.20.1.1 與 192.168.0.9"), ["private-ip"])

    def test_placeholders_and_local_files_are_ignored(self):
        self.assertEqual(self.kinds("r.md", "路徑 /<磁碟代號>/<目錄>、a@example.com、noreply@x.com、8.8.8.8、src/a/b"), [])
        self.assertEqual(self.kinds("CLAUDE.local.md", "D:\\Tools\\x"), [])
        self.assertEqual(self.kinds(".env", "HOST=10.0.0.1"), [])
        self.assertEqual(self.kinds("settings.local.json", '{"p": "/Users/user/x"}'), [])
        self.assertEqual(self.kinds("r.md", "remote git@gitlab.corp.io:a/b.git"), [])
        self.assertEqual(self.kinds("r.md", "裝 pi-code@1" + ".4.0"), [])

    def test_virtualenv_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".venv" / "lib" / "m.py"
            p.parent.mkdir(parents=True)
            p.write_text("x = 'C:\\Data'", encoding="utf-8")
            self.assertEqual(scan([Path(d)]), [])

    def test_line_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text("ok\nC:\\Data\\y\n", encoding="utf-8")
            self.assertEqual([h[2] for h in scan([p])], [2])


if __name__ == "__main__":
    unittest.main()
