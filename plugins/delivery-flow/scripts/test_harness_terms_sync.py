"""delivery-flow 與 browser-docs 共用的檔案各放一份（${CLAUDE_PLUGIN_ROOT} 不能跨 plugin，且兩個 plugin 要能各自獨立安裝），內容必須逐位元相同。

單獨安裝 delivery-flow（旁邊沒有 browser-docs）時略過。
"""
import unittest
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[2]
SHARED = (
    "references/harness-terms.md",
    "references/annotate-spec.md",
    "references/anonymize-before-capture.md",
    "scripts/annotate.py",
    "scripts/anonymize-page.js",
)


class SharedCopiesSync(unittest.TestCase):
    def test_copies_are_identical(self):
        if not (PLUGINS / "browser-docs").exists():
            self.skipTest("browser-docs 不在旁邊")
        for rel in SHARED:
            with self.subTest(rel=rel):
                mine = PLUGINS / "delivery-flow" / rel
                theirs = PLUGINS / "browser-docs" / rel
                self.assertEqual(mine.read_bytes(), theirs.read_bytes(), f"兩份 {rel} 漂移了，請同步")


if __name__ == "__main__":
    unittest.main()
