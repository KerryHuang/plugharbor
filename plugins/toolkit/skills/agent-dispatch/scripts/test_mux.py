#!/usr/bin/env python3
"""mux.py 測試。後端一律用 PATH stub，PATH 只含 stub 目錄與 /usr/bin:/bin，絕不碰真的 hc／herdr。

用法：python3 test_mux.py
"""
import json, os, shutil, socket, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mux  # noqa: E402

MUX = HERE / "mux.py"

# 每次呼叫記錄：calls.log（一行）、argv.log（一個參數一行，看原字串）、env.log
# 回應：resp.<程式>.<$1>.<$2>，找不到退而求其次 resp.<程式>.<$1>；err.<程式>.<$1> 寫 stderr；rc.<程式>.<$1> 設 exit code
STUB = r"""#!/bin/sh
n=$(basename "$0")
echo "$n $*" >> "$STUB_DIR/calls.log"
{ echo "CALL $n"; for a in "$@"; do echo "ARG:$a"; done; } >> "$STUB_DIR/argv.log"
echo "$n HC_TERMINAL_ID=[${HC_TERMINAL_ID-}]" >> "$STUB_DIR/env.log"
r="$STUB_DIR/resp.$n.$1.$2"; [ -f "$r" ] || r="$STUB_DIR/resp.$n.$1"
[ -f "$r" ] && cat "$r"
e="$STUB_DIR/err.$n.$1"; [ -f "$e" ] && cat "$e" >&2
rc="$STUB_DIR/rc.$n.$1"; [ -f "$rc" ] && exit "$(cat "$rc")"
exit 0
"""

HC_ENV = {"HC_TERMINAL_ID": "t1", "MUX_BACKEND": "hc"}
HERDR_ENV = {"HERDR_ENV": "1", "HERDR_PANE_ID": "main1", "MUX_BACKEND": "herdr"}


class MuxCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="mx"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        for name in ("hc", "herdr", "herdr-app", "claude", "codex", "herdr_layout.py", "app_layout.py"):
            (self.dir / name).write_text(STUB, encoding="utf-8")
            (self.dir / name).chmod(0o755)
        self.sock = None

    # core 在跑：真的開一個 listening socket（connect 成功才算在跑）
    def start_core(self):
        path = str(self.dir / "s")
        if self.sock:
            return path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(path)
        self.sock.listen(8)
        self.addCleanup(self.sock.close)
        return path

    def resp(self, prog, key, text, rc=None, err=None):
        (self.dir / f"resp.{prog}.{key}").write_text(text, encoding="utf-8")
        if rc is not None:
            (self.dir / f"rc.{prog}.{key.split('.')[0]}").write_text(str(rc), encoding="utf-8")
        if err is not None:
            (self.dir / f"err.{prog}.{key.split('.')[0]}").write_text(err, encoding="utf-8")

    def mux(self, args, env=None, core=True):
        e = {"PATH": f"{self.dir}:/usr/bin:/bin", "HOME": str(self.dir), "STUB_DIR": str(self.dir),
             "MUX_CORE_SOCKET": self.start_core() if core else str(self.dir / "nosock")}
        e.update(env or {})
        r = subprocess.run([sys.executable, str(MUX), *args], capture_output=True, text=True,
                           encoding="utf-8", env=e)
        return r.returncode, r.stdout, r.stderr

    def calls(self):
        f = self.dir / "calls.log"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    def hc_run(self):
        return next(c for c in self.calls() if c.startswith("hc run")).split()

    def argv_log(self):
        f = self.dir / "argv.log"
        return f.read_text(encoding="utf-8") if f.exists() else ""

    def ok(self, args, env, **kw):
        code, out, err = self.mux(args, env, **kw)
        self.assertEqual(code, 0, f"stdout={out} stderr={err}")
        return json.loads(out)


class TestDetect(unittest.TestCase):
    def test_hc_only(self):
        self.assertEqual(mux.detect_backend({"HC_TERMINAL_ID": "t1"}), "hc")

    def test_herdr_only(self):
        self.assertEqual(mux.detect_backend({"HERDR_ENV": "1", "HERDR_PANE_ID": "w:p1"}), "herdr")

    def test_herdr_env_without_pane_id_is_none(self):
        self.assertEqual(mux.detect_backend({"HERDR_ENV": "1"}), "none")

    def test_nothing_is_none(self):
        self.assertEqual(mux.detect_backend({}), "none")

    def test_both_sets_prefers_nearest_ancestor(self):
        env = {"HC_TERMINAL_ID": "t1", "HERDR_ENV": "1", "HERDR_PANE_ID": "w:p1"}
        self.assertEqual(mux.detect_backend(env, [100, 200, 300], hc_pid=300, herdr_pid=200), "herdr")
        self.assertEqual(mux.detect_backend(env, [100, 200, 300], hc_pid=200, herdr_pid=300), "hc")

    def test_both_sets_unknown_ancestry_defaults_hc(self):
        env = {"HC_TERMINAL_ID": "t1", "HERDR_ENV": "1", "HERDR_PANE_ID": "w:p1"}
        self.assertEqual(mux.detect_backend(env, None, None, None), "hc")
        self.assertEqual(mux.detect_backend(env, [100, 200], None, None), "hc")

    def test_mux_backend_override(self):
        env = {"HC_TERMINAL_ID": "t1", "HERDR_ENV": "1", "HERDR_PANE_ID": "w:p1", "MUX_BACKEND": "none"}
        self.assertEqual(mux.detect_backend(env), "none")
        self.assertEqual(mux.detect_backend({"MUX_BACKEND": "herdr"}), "herdr")

    def test_clean_env_prefix(self):
        want = ["env"] + [x for v in mux.POLLUTED_VARS for x in ("-u", v)] + ["A=1", "B=x y"]
        self.assertEqual(mux.clean_env_prefix({"A": "1", "B": "x y"}), want)
        for v in ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT", "HERDR_ENV",
                  "HERDR_PANE_ID", "HERDR_SOCKET_PATH", "HERDR_TAB_ID", "HERDR_WORKSPACE_ID"):
            self.assertIn(v, mux.POLLUTED_VARS)
        self.assertFalse([v for v in mux.POLLUTED_VARS if v.startswith("HC_")])


class TestCore(MuxCase):
    def test_core_not_running_never_calls_hc(self):
        code, out, _ = self.mux(["send", "t1", "--text", "x"], HC_ENV, core=False)
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["error"], "core_not_running")
        self.assertEqual(self.calls(), [])

    def test_stale_socket_is_not_running(self):
        path = str(self.dir / "stale")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)
        s.close()  # 檔還在但沒人聽
        self.assertTrue(os.path.exists(path))
        code, out, _ = self.mux(["alive", "t1"], {**HC_ENV, "MUX_CORE_SOCKET": path}, core=False)
        self.assertEqual(code, 3)
        self.assertEqual(self.calls(), [])

    def test_core_running_function(self):
        os.environ["MUX_CORE_SOCKET"] = self.start_core()
        self.addCleanup(os.environ.pop, "MUX_CORE_SOCKET", None)
        self.assertTrue(mux.core_running())
        os.environ["MUX_CORE_SOCKET"] = str(self.dir / "nope")
        self.assertFalse(mux.core_running())


class TestEnv(MuxCase):
    def test_env_hc_with_window(self):
        r = self.ok(["env"], HC_ENV)
        self.assertEqual(r, {"backend": "hc", "self": "t1", "window": True})
        self.assertEqual(self.calls(), ["herdr-app status"])

    def test_env_hc_without_window(self):
        self.resp("herdr-app", "status", "", rc=2, err="no Herdr window")
        self.assertFalse(self.ok(["env"], HC_ENV)["window"])

    def test_env_window_error_is_not_no_window(self):
        # 只有 exit 2 且訊息含 no Herdr window 才算沒開；其他失敗不能當成沒開
        for rc, err in ((1, "boom"), (2, "path must be shorter than SUN_LEN"), (2, "")):
            with self.subTest(rc=rc):
                self.resp("herdr-app", "status", "", rc=rc, err=err)
                code, out, _ = self.mux(["env"], HC_ENV)
                self.assertEqual((code, json.loads(out)["error"]), (1, "window_error"))

    def test_env_hc_core_down_no_hc_call(self):
        r = self.ok(["env"], HC_ENV, core=False)
        self.assertEqual(r, {"backend": "hc", "self": "t1", "window": False})
        self.assertEqual(self.calls(), [])

    def test_env_herdr(self):
        self.assertEqual(self.ok(["env"], HERDR_ENV), {"backend": "herdr", "self": "main1", "window": False})

    def test_env_none(self):
        self.assertEqual(self.ok(["env"], {"MUX_BACKEND": "none"}),
                         {"backend": "none", "self": None, "window": False})

    def test_none_backend_errors(self):
        for args in (["send", "x", "--text", "y"], ["wait", "x"], ["read", "x"], ["alive", "x"],
                     ["session", "x"], ["close", "x"], ["attach-hint", "x"],
                     ["spawn", "--name", "n", "--kind", "claude", "--cwd", "/tmp"]):
            with self.subTest(args=args):
                code, out, _ = self.mux(args, {"MUX_BACKEND": "none"})
                self.assertEqual(code, 4)
                self.assertEqual(json.loads(out)["error"], "no_backend")


class TestHc(MuxCase):
    LS = json.dumps({"spaces": [{"tabs": [{"tab": "tb1", "terminals": [
        {"terminal": "t1", "pane": "p1"}, {"terminal": "t5", "pane": "p5", "name": "w0"}]}]}]})

    def layout_env(self):
        return {**HC_ENV, "MUX_APP_LAYOUT_CMD": str(self.dir / "app_layout.py")}

    def spawn_args(self):
        return ["spawn", "--name", "w1", "--kind", "claude", "--cwd", "/tmp", "--", "--model", "m"]

    def test_spawn_with_window_places_next_to_main(self):
        self.resp("hc", "run", '{"address":"t7"}')
        self.resp("herdr-app", "ls", self.LS)
        self.resp("app_layout.py", "place", '{"pane":"p7","visible":true}')
        r = self.ok(self.spawn_args(), self.layout_env())
        self.assertEqual(r, {"id": "t7", "visible": True, "pane": "p7"})
        self.assertIn("app_layout.py place --main p1 --terminal t7 --name w1", self.calls())
        calls = self.calls()
        self.assertLess(calls.index("herdr-app status"), [i for i, c in enumerate(calls) if c.startswith("hc run")][0])

    def test_spawn_without_window_stays_hidden(self):
        self.resp("herdr-app", "status", "", rc=2, err="herdr-app: no Herdr window at x/herdr-app.sock")
        self.resp("hc", "run", '{"address":"t7"}')
        r = self.ok(self.spawn_args(), self.layout_env())
        self.assertEqual(r, {"id": "t7", "visible": False})
        self.assertFalse([c for c in self.calls() if c.startswith("app_layout.py")])
        self.assertFalse([c for c in self.calls() if c.startswith("herdr-app ls")])

    def test_spawn_window_error_does_not_start_worker(self):
        self.resp("herdr-app", "status", "", rc=1, err="boom")
        code, out, _ = self.mux(self.spawn_args(), self.layout_env())
        self.assertEqual((code, json.loads(out)["error"]), (1, "window_error"))
        self.assertFalse([c for c in self.calls() if c.startswith("hc run")])

    def test_spawn_main_pane_not_in_window_stays_hidden(self):
        self.resp("hc", "run", '{"address":"t7"}')
        self.resp("herdr-app", "ls", '{"spaces":[]}')
        r = self.ok(self.spawn_args(), self.layout_env())
        self.assertEqual(r, {"id": "t7", "visible": False})
        self.assertFalse([c for c in self.calls() if c.startswith("app_layout.py")])

    def test_spawn_layout_failure_keeps_worker_hidden(self):
        self.resp("hc", "run", '{"address":"t7"}')
        self.resp("herdr-app", "ls", self.LS)
        self.resp("app_layout.py", "place", '{"error":"layout_failed","hint":"x"}', rc=1)
        code, out, err = self.mux(self.spawn_args(), self.layout_env())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"id": "t7", "visible": False})
        self.assertIn("版面", err)

    def test_send_strips_hc_terminal_id(self):
        self.resp("hc", "send", '{"started":true}')
        self.ok(["send", "t2", "--text", "hi"], HC_ENV)
        self.assertIn("hc HC_TERMINAL_ID=[]", (self.dir / "env.log").read_text(encoding="utf-8"))

    def test_spawn_hc_unsets_polluted_env(self):
        self.resp("hc", "run", '{"address":"t7","name":"w1","state":"live"}')
        r = self.ok(["spawn", "--name", "w1", "--kind", "claude", "--cwd", "/tmp", "--env", "A=1",
                     "--", "--model", "m"], HC_ENV)
        self.assertEqual(r, {"id": "t7", "visible": False})
        argv = self.hc_run()
        self.assertEqual(argv[:2], ["hc", "run"])
        for flag in ("--bg", "--no-notify"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--name") + 1], "w1")
        self.assertFalse([a for a in argv if a.startswith("herdr.")])
        i = argv.index("env")
        j = argv.index("A=1")
        self.assertEqual(argv[i + 1:j], [x for v in mux.POLLUTED_VARS for x in ("-u", v)])
        for v in ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT", "HERDR_ENV",
                  "HERDR_PANE_ID", "HERDR_SOCKET_PATH"):
            self.assertIn(v, argv[i:j])
        self.assertFalse([a for a in argv if a.startswith("HC_")])
        self.assertTrue(argv[j + 1].endswith("/claude"))
        self.assertEqual(argv[j + 2:], ["--model", "m"])

    def test_spawn_hc_resolves_absolute_cli(self):
        self.resp("hc", "run", '{"address":"t7"}')
        self.ok(["spawn", "--name", "w1", "--kind", "claude", "--cwd", "/tmp", "--", "--model", "m"], HC_ENV)
        argv = self.hc_run()
        self.assertIn(str(self.dir / "claude"), argv)
        self.assertNotIn("claude", argv)  # 不能是裸名稱

    def test_spawn_hc_cli_not_found(self):
        (self.dir / "claude").unlink()
        code, out, _ = self.mux(["spawn", "--name", "w1", "--kind", "claude", "--cwd", "/tmp"], HC_ENV)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["error"], "cli_not_found")
        self.assertEqual(self.calls(), [])

    def test_spawn_codex_adds_no_daemon(self):
        self.resp("hc", "run", '{"address":"t7"}')
        self.ok(["spawn", "--name", "w1", "--kind", "codex", "--cwd", "/tmp", "--", "-m", "x"], HC_ENV)
        argv = self.hc_run()
        i = argv.index(str(self.dir / "codex"))
        self.assertEqual(argv[i + 1:], ["--no-daemon", "-m", "x"])

    def test_send_wait_status_mapping(self):
        for raw, want in (("done", "done"), ("idle", "idle"), ("working", "working"),
                          ("blocked", "blocked"), ("error", "error"), ("weird", "error")):
            with self.subTest(raw=raw):
                body = {"started": True, "status": raw,
                        "wait": {"ended": True, "reason": "status", "status": raw, "terminal": "t1"}}
                self.resp("hc", "send", json.dumps(body))
                r = self.ok(["send", "t1", "--text", "x", "--wait", "--timeout", "540"], HC_ENV)
                self.assertEqual(r["status"], want)
                self.assertEqual(r["raw"], body)
        self.assertIn("hc send --json --wait --timeout 540 -- t1 x", self.calls())

    def test_wait_not_ended_is_timeout(self):
        self.resp("hc", "wait", '{"ended":false,"reason":"timeout","status":"working"}')
        self.assertEqual(self.ok(["wait", "t1", "--timeout", "5"], HC_ENV)["status"], "timeout")

    def test_send_file_reads_content(self):
        text = "echo `date` $(whoami)\n\"quoted\" 第二行"
        f = self.dir / "prompt.txt"
        f.write_text(text, encoding="utf-8")
        self.resp("hc", "send", '{"started":true}')
        self.ok(["send", "t1", "--file", str(f)], HC_ENV)
        self.assertIn(f"ARG:{text}\n", self.argv_log())

    def test_actions(self):
        self.resp("hc", "wait", '{"ended":true,"status":"done"}')
        r = self.ok(["wait", "t1", "--timeout", "30"], HC_ENV)
        self.assertEqual(r["status"], "done")
        self.assertIn("hc wait --json --timeout 30 t1", self.calls())

        self.resp("hc", "read", "line1\nline2\n")
        code, out, _ = self.mux(["read", "t1", "--lines", "20"], HC_ENV)
        self.assertEqual((code, out), (0, "line1\nline2\n"))
        self.assertIn("hc read t1 --lines 20", self.calls())

        self.resp("hc", "get", '{"address":"t1","state":"live","status":"working"}')
        self.assertEqual(self.ok(["alive", "t1"], HC_ENV), {"alive": True})
        self.assertIn("hc get --json t1", self.calls())
        self.resp("hc", "get", '{"address":"t1","state":"finished"}')
        self.assertEqual(self.ok(["alive", "t1"], HC_ENV), {"alive": False})
        self.resp("hc", "get", "", rc=1, err="no such terminal")
        self.assertEqual(self.ok(["alive", "t1"], HC_ENV), {"alive": False})

        self.assertEqual(self.ok(["session", "t1"], HC_ENV), {"session": None})

        n = len(self.calls())
        self.assertEqual(self.ok(["close", "t1"], HC_ENV), {"closed": True})
        self.assertEqual(self.calls()[n:], ["hc kill t1", "hc rm t1"])

    def test_session_hc_reads_file(self):
        state = self.dir / "state"
        (state / "plugharbor" / "hc-sessions").mkdir(parents=True)
        (state / "plugharbor" / "hc-sessions" / "t7").write_text("sess-abc\n", encoding="utf-8")
        self.resp("hc", "get", '{"address":"t7","state":"live"}')
        r = self.ok(["session", "w1"], {**HC_ENV, "XDG_STATE_HOME": str(state)})
        self.assertEqual(r, {"session": "sess-abc"})
        self.assertIn("hc get --json w1", self.calls())

    def test_session_hc_missing_returns_null(self):
        self.resp("hc", "get", '{"address":"t7","state":"live"}')
        r = self.ok(["session", "w1"], {**HC_ENV, "XDG_STATE_HOME": str(self.dir / "state")})
        self.assertEqual(r, {"session": None})

    def test_attach_hint(self):
        self.assertIn("hc attach t1", self.ok(["attach-hint", "t1"], HC_ENV)["hint"])


class TestHerdr(MuxCase):
    def setUp(self):
        super().setUp()
        self.layout = {"MUX_LAYOUT_CMD": str(self.dir / "herdr_layout.py")}

    def test_spawn_herdr_sequence(self):
        self.resp("herdr", "pane.split", '{"result":{"pane":{"pane_id":"p9"}}}')
        r = self.ok(["spawn", "--name", "w1", "--kind", "claude", "--cwd", "/tmp", "--env", "A=1",
                     "--", "--model", "m"], {**HERDR_ENV, **self.layout})
        self.assertEqual(r, {"id": "p9", "visible": True})
        want = ["herdr pane split --current --direction right --cwd /tmp --no-focus --env A=1",
                "herdr_layout.py --main main1",
                "herdr agent start w1 --kind claude --pane p9 -- --model m",
                "herdr pane rename p9 w1"]
        self.assertEqual(self.calls(), want)

    def test_spawn_herdr_start_failure_cleans_up(self):
        self.resp("herdr", "pane.split", '{"result":{"pane":{"pane_id":"p9"}}}')
        self.resp("herdr", "agent.start", "", rc=1, err='{"error":{"code":"agent_not_ready"}}')
        self.resp("herdr", "pane.read", "trust this folder?")
        code, out, _ = self.mux(["spawn", "--name", "w1", "--kind", "claude", "--cwd", "/tmp"],
                                {**HERDR_ENV, **self.layout})
        self.assertEqual(code, 1)
        e = json.loads(out)
        self.assertEqual(e["error"], "spawn_failed")
        self.assertIn("trust this folder", e["hint"])
        self.assertIn("herdr pane close p9", self.calls())

    def test_send_wait_status_mapping(self):
        for raw, want in (("done", "done"), ("idle", "idle"), ("working", "working"),
                          ("blocked", "blocked"), ("error", "error"), ("unknown", "error"), ("zzz", "error")):
            with self.subTest(raw=raw):
                body = {"id": "x", "result": {"agent_status": raw, "name": "w1"}}
                self.resp("herdr", "agent.prompt", json.dumps(body))
                r = self.ok(["send", "p1", "--text", "hi", "--wait", "--timeout", "540"], HERDR_ENV)
                self.assertEqual(r["status"], want)
                self.assertEqual(r["raw"], body)
        self.assertIn("herdr agent prompt p1 hi --wait --timeout 540000", self.calls())

    def test_send_wait_error_codes(self):
        for code_name, want in (("timeout", "timeout"), ("agent_not_found", "gone"), ("agent_blocked", "blocked"),
                                ("something_else", "error")):
            with self.subTest(code=code_name):
                self.resp("herdr", "agent.prompt", "", rc=1, err=json.dumps({"error": {"code": code_name}}))
                r = self.ok(["send", "p1", "--text", "hi", "--wait"], HERDR_ENV)
                self.assertEqual(r["status"], want)
                self.assertEqual(r["raw"], {"error": {"code": code_name}})

    def test_send_file_reads_content(self):
        text = "echo `date` $(whoami)\n\"quoted\" 第二行"
        f = self.dir / "prompt.txt"
        f.write_text(text, encoding="utf-8")
        self.resp("herdr", "agent.prompt", '{"result":{}}')
        self.ok(["send", "p1", "--file", str(f)], HERDR_ENV)
        self.assertIn(f"ARG:{text}\n", self.argv_log())

    def test_actions(self):
        self.resp("herdr", "agent.wait", '{"result":{"agent_status":"idle"}}')
        self.assertEqual(self.ok(["wait", "p1", "--timeout", "30"], HERDR_ENV)["status"], "idle")
        self.assertIn("herdr agent wait p1 --timeout 30000", self.calls())

        self.resp("herdr", "agent.read", "screen text\n")
        code, out, _ = self.mux(["read", "p1", "--lines", "20"], HERDR_ENV)
        self.assertEqual((code, out), (0, "screen text\n"))
        self.assertIn("herdr agent read p1 --lines 20", self.calls())

        self.resp("herdr", "agent.get", '{"result":{"pane":{"agent_session":{"value":"sess-1"}}}}')
        self.assertEqual(self.ok(["alive", "p1"], HERDR_ENV), {"alive": True})
        self.assertEqual(self.ok(["session", "p1"], HERDR_ENV), {"session": "sess-1"})
        self.resp("herdr", "agent.get", "", rc=1, err='{"error":{"code":"agent_not_found"}}')
        self.assertEqual(self.ok(["alive", "p1"], HERDR_ENV), {"alive": False})
        self.assertEqual(self.ok(["session", "p1"], HERDR_ENV), {"session": None})

        n = len(self.calls())
        self.assertEqual(self.ok(["close", "p1"], HERDR_ENV), {"closed": True})
        self.assertEqual(self.calls()[n:], ["herdr pane close p1"])

    def test_herdr_never_touches_hc(self):
        self.resp("herdr", "agent.wait", '{"result":{"agent_status":"idle"}}')
        self.ok(["wait", "p1"], {**HERDR_ENV, "HC_TERMINAL_ID": "t1"}, core=False)
        self.assertEqual([c.split()[0] for c in self.calls()], ["herdr"])

    def test_attach_hint(self):
        self.assertIn("herdr agent attach p1", self.ok(["attach-hint", "p1"], HERDR_ENV)["hint"])


if __name__ == "__main__":
    unittest.main()
