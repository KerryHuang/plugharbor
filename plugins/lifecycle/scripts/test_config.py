import pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import config  # noqa: E402

CLI = HERE / "config.py"


def write_cfg(root, text):
    d = pathlib.Path(root) / ".plugharbor"
    d.mkdir(exist_ok=True)
    (d / "lifecycle.yml").write_text(text, encoding="utf-8")


class ConfigTest(unittest.TestCase):
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(config.ConfigMissing) as cm:
                config.load_config(pathlib.Path(t))
            self.assertIn(".plugharbor/lifecycle.yml", cm.exception.hint)

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

    def test_empty_string_is_missing(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, 'ticket:\n  tool: ""\n')
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout.strip(), "")

    def test_non_utf8_file_is_format_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / ".plugharbor"
            d.mkdir()
            (d / "lifecycle.yml").write_bytes("ticket:\n  tool: 票\n".encode("big5"))
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn("UTF-8", r.stderr)

    def test_cli_get_ok(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: github\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "github"))

    def test_old_delivery_flow_yml_only_asks_rename(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / ".plugharbor"
            d.mkdir()
            (d / "delivery-flow.yml").write_text("ticket:\n  tool: linear\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(CLI), "get", "ticket.tool"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (3, ""))
            self.assertIn("lifecycle.yml", r.stderr)
            self.assertIn("delivery-flow.yml", r.stderr)
            self.assertNotIn("Traceback", r.stderr)

    def test_old_delivery_flow_yml_blocks_defaulted_key(self):
        # 有預設值的鍵也不能默默回預設：舊檔存在時一律要使用者先改名
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / ".plugharbor"
            d.mkdir()
            (d / "delivery-flow.yml").write_text("scale: full\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(CLI), "get", "scale"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (3, ""))
            self.assertIn("delivery-flow.yml", r.stderr)

    def test_spec_dir_reads_legacy_sdlc_docs_path(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: github\n")
            (pathlib.Path(t) / "CLAUDE.md").write_text("# 專案\n\nsdlc-docs-path: ../docs\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(CLI), "get", "spec.dir"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "../docs"))
            self.assertIn("sdlc-docs-path", r.stderr)

    def test_spec_dir_in_lifecycle_yml_wins_over_legacy(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "spec:\n  dir: specs\n")
            (pathlib.Path(t) / "CLAUDE.md").write_text("sdlc-docs-path: ../docs\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(CLI), "get", "spec.dir"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "specs"))

    def test_scale_defaults_to_lean(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: github\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "scale"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "lean"))

    def test_spec_dir_defaults_to_docs_specs(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "ticket:\n  tool: github\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "spec.dir"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "docs/specs"))

    def test_defaults_apply_without_config_file(self):
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, str(CLI), "get", "scale"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "lean"))

    def test_scale_explicit_full(self):
        with tempfile.TemporaryDirectory() as t:
            write_cfg(t, "scale: full\n")
            r = subprocess.run([sys.executable, str(CLI), "get", "scale"],
                               cwd=t, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "full"))


if __name__ == "__main__":
    unittest.main()
