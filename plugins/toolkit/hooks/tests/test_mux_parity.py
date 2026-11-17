"""hook／node 內嵌的「在不在 herdr 內」判斷要與 mux.detect_backend 一致；scrubEnv 的 HERDR_* 要是 POLLUTED_VARS 的子集。"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN / "skills" / "agent-dispatch" / "scripts"))
import mux  # noqa: E402

ENV_HOOK = PLUGIN / "hooks" / "herdr-env-context.py"
SAMPLES = {
    "only_hc": {"HC_TERMINAL_ID": "t1"},
    "only_herdr": {"HERDR_ENV": "1", "HERDR_PANE_ID": "w:p1"},
    "both": {"HC_TERMINAL_ID": "t1", "HERDR_ENV": "1", "HERDR_PANE_ID": "w:p1"},
    "neither": {},
    "env_without_pane": {"HERDR_ENV": "1"},
}
CLEAN = ("HERDR_ENV", "HERDR_PANE_ID", "HC_TERMINAL_ID", "MUX_BACKEND")


def hook_inside(sample):
    env = {k: v for k, v in os.environ.items() if k not in CLEAN}
    env.update(sample)
    p = subprocess.run([sys.executable, str(ENV_HOOK)], env=env, input=b"", capture_output=True, timeout=10)
    return p.stdout != b""


def node_inside(sample):
    code = ("import('" + (PLUGIN / "skills/agent-dispatch/scripts/bg.mjs").as_posix() + "').then(m=>"
            "console.log(m.detectEnv(JSON.parse(process.argv[1]),{ghostty:false})))")
    r = subprocess.run(["node", "-e", code, json.dumps(sample)], capture_output=True, timeout=20)
    return r.stdout.decode().strip() == "herdr"


class Parity(unittest.TestCase):
    def test_hook_and_node_match_mux(self):
        for name, sample in SAMPLES.items():
            # both 且沒有祖先資訊時 mux 回 hc，仍屬「在內」
            want = mux.detect_backend(sample) != "none"
            with tempfile.TemporaryDirectory():
                self.assertEqual(hook_inside(sample), want, name)
            self.assertEqual(node_inside(sample), want, name)

    def test_polluted_vars_cover_scrubenv_herdr_vars(self):
        src = (PLUGIN / "skills" / "agent-mesh-check" / "scripts" / "clis.mjs").read_text(encoding="utf-8")
        body = src[src.index("export function scrubEnv"):]
        body = body[:body.index("\n}\n")]
        names = set(re.findall(r"'(HERDR_[A-Z_]+)'", body))
        self.assertTrue({"HERDR_PANE_ID", "HERDR_SOCKET_PATH", "HERDR_TAB_ID", "HERDR_WORKSPACE_ID"} <= names, names)
        self.assertTrue(names <= set(mux.POLLUTED_VARS), names - set(mux.POLLUTED_VARS))


if __name__ == "__main__":
    unittest.main()
