import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent
SCRIPT = HERE / "preflight.sh"


@unittest.skipUnless(shutil.which("bash"), "需要 bash")
class PreflightTest(unittest.TestCase):
    def run_pf(self, ws):
        return subprocess.run(["bash", str(SCRIPT), str(ws)], capture_output=True, text=True, encoding="utf-8")

    def test_old_delivery_flow_yml_asks_rename_not_rewrite(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / ".plugharbor"
            d.mkdir()
            (d / "delivery-flow.yml").write_text("qa:\n  environments: []\n", encoding="utf-8")
            r = self.run_pf(t)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("delivery-flow.yml", r.stdout)
            self.assertIn("改名", r.stdout)
            self.assertNotIn("會問你並代寫", r.stdout.split("qa.local.md")[0])


if __name__ == "__main__":
    unittest.main()
