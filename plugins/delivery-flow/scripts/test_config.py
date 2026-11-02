import pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import config  # noqa: E402

CLI = HERE / "config.py"


def write_cfg(root, text):
    d = pathlib.Path(root) / ".plugharbor"
    d.mkdir(exist_ok=True)
    (d / "delivery-flow.yml").write_text(text, encoding="utf-8")


class ConfigTest(unittest.TestCase):
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(config.ConfigMissing) as cm:
                config.load_config(pathlib.Path(t))
            self.assertIn(".plugharbor/delivery-flow.yml", cm.exception.hint)

    def test_missing_key(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "publish-target: file:docs/meetings\n")
            cfg = config.load_config(pathlib.Path(t))
            with self.assertRaises(config.ConfigMissing) as cm:
                config.require(cfg, "ticket.tool")
            self.assertEqual(cm.exception.key, "ticket.tool")
            self.assertIn("ticket.tool", cm.exception.hint)

    def test_jira_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: jira\n  states:\n    todo: To Do\n")
            cfg = config.load_config(pathlib.Path(t))
            self.assertEqual(config.require(cfg, "ticket.tool"), "jira")
            self.assertEqual(config.require(cfg, "ticket.states.todo"), "To Do")

    def test_cli_missing_key(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: linear\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.team"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(len(r.stderr.strip().splitlines()), 1)

    def test_cli_missing_file(self):
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)

    def test_missing_file_hint_names_requested_key(self):
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.team"],
                               cwd=t, capture_output=True, text=True)
            self.assertIn("ticket.team", r.stderr)

    def test_yaml_syntax_error(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket: [unclosed\n  tool: : x\n")
            with self.assertRaises(config.ConfigMissing) as cm:
                config.load_config(pathlib.Path(t))
            self.assertIn("格式錯誤", cm.exception.hint)
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(len(r.stderr.strip().splitlines()), 1)

    def test_non_mapping(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "- a\n- b\n")
            with self.assertRaises(config.ConfigMissing) as cm:
                config.load_config(pathlib.Path(t))
            self.assertIn("格式錯誤", cm.exception.hint)
            self.assertNotIn("建立", cm.exception.hint)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "")
            cfg = config.load_config(pathlib.Path(t))
            self.assertEqual(cfg, {})
            with self.assertRaises(config.ConfigMissing):
                config.require(cfg, "ticket.tool")
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)

    def test_null_value_is_missing(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool:\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout.strip(), "")

    def test_cli_get_ok(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: github\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "github"))


if __name__ == "__main__":
    unittest.main()
