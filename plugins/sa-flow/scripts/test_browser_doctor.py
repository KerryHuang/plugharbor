import importlib.util, pathlib, tempfile, unittest, sys
HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("doctor", HERE / "browser-doctor.py")
doctor = importlib.util.module_from_spec(spec); spec.loader.exec_module(doctor)

class Registration(unittest.TestCase):
    def test_claude_isolated_ok(self):
        self.assertIsNone(doctor.check_claude_args(["/c", "npx", "-y", "chrome-devtools-mcp@latest", "--isolated", "--viewport", "1680x1000"]))
    def test_claude_browserurl_fails(self):
        r = doctor.check_claude_args(["/c", "npx", "chrome-devtools-mcp@latest", "--browserUrl=http://127.0.0.1:9222"])
        self.assertIn("--isolated", r)
    def test_codex_autoconnect_fails(self):
        r = doctor.check_codex_args(["/c", "npx", "chrome-devtools-mcp@latest", "--autoConnect", "--channel=stable"])
        self.assertIn("--isolated", r)

class Version(unittest.TestCase):
    def test_floor(self):
        self.assertTrue(doctor.version_ok("1.9.0"))
        self.assertTrue(doctor.version_ok("1.8.0"))
        self.assertFalse(doctor.version_ok("1.7.12"))

class MissingEntry(unittest.TestCase):
    def test_check_missing_entry(self):
        r = doctor.check_claude_args("MISSING")
        self.assertIn("未註冊", r)

class ParseUserDataDirs(unittest.TestCase):
    def test_live_dirs_regex_with_space(self):
        text = (
            'chrome.exe --user-data-dir="C:\\Users\\John Doe\\AppData\\Local\\Temp\\puppeteer_dev_chrome_profile-abc" --type=renderer\n'
            'chrome.exe --user-data-dir=C:\\Temp\\puppeteer_dev_chrome_profile-xyz\n'
            'chrome.exe --user-data-dir="C:\\Users\\example\\.cache\\claude-shared-chrome"'
        )
        got = doctor.parse_user_data_dirs(text)
        self.assertEqual(got, [
            "C:\\Users\\John Doe\\AppData\\Local\\Temp\\puppeteer_dev_chrome_profile-abc",
            "C:\\Temp\\puppeteer_dev_chrome_profile-xyz",
        ])

class Stale(unittest.TestCase):
    def test_only_unreferenced_dirs(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = pathlib.Path(t)
            a = tmp / "puppeteer_dev_chrome_profile-aaaaaa"; a.mkdir()
            b = tmp / "puppeteer_dev_chrome_profile-bbbbbb"; b.mkdir()
            (tmp / "unrelated").mkdir()
            got = doctor.stale_profiles(tmp, live_dirs={str(b)})
            self.assertEqual(got, [a])

class Orphans(unittest.TestCase):
    def test_ppid1_server_only(self):
        lines = [
            "100 1 node /x/node_modules/.bin/chrome-devtools-mcp --isolated",
            "101 100 node /x/telemetry/watchdog",
            "102 1 npm exec chrome-devtools-mcp",
            "103 555 node /x/node_modules/.bin/chrome-devtools-mcp --isolated",
        ]
        self.assertEqual(doctor.orphan_server_pids(lines), [100])

if __name__ == "__main__":
    unittest.main()
