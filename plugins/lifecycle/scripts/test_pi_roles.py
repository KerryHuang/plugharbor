"""pi/roles/ 與 agents/*.md 同步（gen-pi-roles.py --check），且每個角色檔符合 pi-herdr-agents 的 frontmatter 規則。"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "scripts" / "gen-pi-roles.py"


class PiRoles(unittest.TestCase):
    def test_roles_in_sync_with_agents(self):
        r = subprocess.run([sys.executable, str(GEN), "--check"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_role_frontmatter(self):
        roles = sorted((ROOT / "pi" / "roles").glob("*.md"))
        self.assertEqual(len(roles), len(list((ROOT / "agents").glob("*.md"))))
        for p in roles:
            lines = p.read_text(encoding="utf-8").split("\n")
            front = lines[1:lines.index("---", 1)]
            keys = [line.split(":", 1)[0] for line in front]
            self.assertEqual(len(keys), len(set(keys)), p.name)
            fields = dict(line.split(": ", 1) for line in front)
            self.assertEqual(fields["name"], p.stem)
            self.assertIn(fields["thinking"], {"low", "medium", "high"})
            self.assertNotIn("model", fields, "Pi 模型名與 Claude 不同，角色檔不寫死")
            for k in ("tools", "spawning"):
                if k in fields:
                    self.assertFalse(fields[k].startswith(("'", '"', "[")), f"{p.name}: {k} 不得加引號或用清單")


if __name__ == "__main__":
    unittest.main()
