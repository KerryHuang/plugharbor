"""delivery-flow 與 browser-docs 各放一份 harness-terms.md（${CLAUDE_PLUGIN_ROOT} 不能跨 plugin），內容必須逐位元相同。

單獨安裝 delivery-flow（旁邊沒有 browser-docs）時略過。
"""
import unittest
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[2]
MINE = PLUGINS / "delivery-flow" / "references" / "harness-terms.md"
THEIRS = PLUGINS / "browser-docs" / "references" / "harness-terms.md"


class HarnessTermsSync(unittest.TestCase):
    def test_copies_are_identical(self):
        if not THEIRS.exists():
            self.skipTest("browser-docs 不在旁邊")
        self.assertEqual(MINE.read_bytes(), THEIRS.read_bytes(), "兩份 harness-terms.md 漂移了，請同步")


if __name__ == "__main__":
    unittest.main()
