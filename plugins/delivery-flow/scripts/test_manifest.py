"""delivery-flow 的 package.json 不放 version：版本只在 plugin.json／marketplace.json／README 三處同步。"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PiManifest(unittest.TestCase):
    def test_manifest_has_no_version_to_drift(self):
        manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertNotIn("version", manifest)


if __name__ == "__main__":
    unittest.main()
