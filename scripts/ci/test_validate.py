"""validate.py 的共用副本同步檢查測試。直接執行：python3 scripts/ci/test_validate.py"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

A = {"tickets": {"scout": "tickets-scout"}}


class ExpectedCopy(unittest.TestCase):
    def test_alias_rewrites_bare_and_prefixed(self):
        src = "派 `scout`；`lifecycle:scout`；scouting；`scout-x`；`lifecycle:domain-advisor`"
        self.assertEqual(
            validate.expected_copy(src, "tickets", A),
            "派 `tickets-scout`；`tickets:tickets-scout`；scouting；`scout-x`；`lifecycle:domain-advisor`",
        )


class SharedCopyErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def manifest(self, aliases=None, copy="browser-docs"):
        return {
            "aliases": aliases or {},
            "groups": [["plugins/lifecycle/references/x.md", f"plugins/{copy}/references/x.md"]],
        }

    def test_identical_copies_pass(self):
        self.write("plugins/lifecycle/references/x.md", "a\n")
        self.write("plugins/browser-docs/references/x.md", "a\n")
        self.assertEqual(validate.shared_copy_errors(self.root, self.manifest()), [])

    def test_drift_names_both_files(self):
        self.write("plugins/lifecycle/references/x.md", "a\n")
        self.write("plugins/browser-docs/references/x.md", "a\nb\n")
        errs = validate.shared_copy_errors(self.root, self.manifest())
        self.assertEqual(len(errs), 1)
        self.assertIn("plugins/browser-docs/references/x.md", errs[0])
        self.assertIn("plugins/lifecycle/references/x.md", errs[0])

    def test_missing_copy_reported(self):
        self.write("plugins/lifecycle/references/x.md", "a\n")
        errs = validate.shared_copy_errors(self.root, self.manifest())
        self.assertEqual(len(errs), 1)
        self.assertIn("缺副本", errs[0])

    def test_alias_applied_before_compare(self):
        self.write("plugins/lifecycle/references/x.md", "派 `scout`\n")
        self.write("plugins/tickets/references/x.md", "派 `tickets-scout`\n")
        m = self.manifest(A, copy="tickets")
        self.assertEqual(validate.shared_copy_errors(self.root, m), [])


if __name__ == "__main__":
    unittest.main()
