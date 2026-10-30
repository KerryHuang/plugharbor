"""sa-flow 要同時在 Claude Code 與 Pi 可執行：檢查 Pi manifest、SKILL.md frontmatter、Claude 專屬用語都有中立對照。

跑法：python3 -m unittest plugins/sa-flow/scripts/test_harness_neutral.py
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TERMS_FILE = ROOT / "references" / "harness-terms.md"
POINTER = "${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md"
SCANNED = ("skills", "agents", "references", "templates")

# Agent Skills 規格欄位（Pi 認得），其餘 frontmatter 欄位要在 harness-terms.md 說明 Pi 上的處理
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools", "disable-model-invocation"}
# Claude Code 專屬用語：出現在 skill／agent／reference／template 內，就必須在 harness-terms.md 有對照
FIXED_TERMS = {
    "${CLAUDE_PLUGIN_ROOT}": r"\$\{CLAUDE_PLUGIN_ROOT\}",
    "$ARGUMENTS": r"\$ARGUMENTS\b",
    "subagent_type": r"\bsubagent_type\b",
    "general-purpose": r"\bgeneral-purpose\b",
    "Explore agent": r"\bExplore agent\b",
    "context: fork": r"context: fork",
    "run_in_background": r"\brun_in_background\b",
    "/reload-plugins": r"/reload-plugins\b",
}
CLAUDE_TOOLS = (
    "AskUserQuestion", "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "TaskOutput", "TaskStop",
    "SendMessage", "TeamCreate", "TeamDelete", "NotebookEdit", "WebFetch", "WebSearch", "BashOutput", "KillShell",
    "ExitPlanMode", "EnterPlanMode", "EnterWorktree", "ExitWorktree", "ListMcpResourcesTool", "ReadMcpResourceTool",
    "ScheduleWakeup", "CronCreate", "CronDelete", "CronList", "SlashCommand", "ToolSearch",
)
ENV_VAR = re.compile(r"\$\{?CLAUDE_[A-Z_]+\}?")
MCP_PREFIX = re.compile(r"mcp__([A-Za-z0-9_-]+?)__")
# agents/ 沒有 skill base dir，裸相對路徑會解到 agents/ 底下（2.51.2 修過的 bug）
BARE_PLUGIN_PATH = re.compile(r"(?<![\w/}.@-])(?:references|templates|scripts|skills)/[\w./-]+")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def scanned_files() -> list[pathlib.Path]:
    files = [p for d in SCANNED for p in sorted((ROOT / d).rglob("*.md"))]
    return [p for p in files if p != TERMS_FILE]


def parse_frontmatter(text: str) -> dict[str, str]:
    """Stdlib 版 YAML 子集：單行 scalar（含引號）與 >/| 區塊，足以檢查本 plugin 的 frontmatter。"""
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError("missing frontmatter block")
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        top = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if top:
            key, value = top.group(1), top.group(2).strip()
            if key in fields:
                raise ValueError(f"duplicate key {key}")
            if value in (">", "|", ">-", "|-"):
                value = ""
            elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key] = value
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
        elif line.strip():
            raise ValueError(f"unparseable frontmatter line: {line!r}")
    return fields


def terms_text() -> str:
    return TERMS_FILE.read_text(encoding="utf-8") if TERMS_FILE.exists() else ""


def defined(term: str, text: str) -> bool:
    return f"`{term}`" in text


class PiManifest(unittest.TestCase):
    def test_manifest_lists_existing_skill_dirs(self) -> None:
        manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertIn("pi-package", manifest.get("keywords", []))
        skills = manifest.get("pi", {}).get("skills")
        self.assertTrue(skills, "package.json 缺 pi.skills")
        for entry in skills:
            path = (ROOT / entry).resolve()
            self.assertTrue(path.is_dir(), f"pi.skills 指向不存在的目錄：{entry}")
            self.assertTrue(list(path.glob("*/SKILL.md")), f"pi.skills 目錄沒有任何 SKILL.md：{entry}")

    def test_manifest_has_no_version_to_drift(self) -> None:
        # 版本只在 plugin.json／marketplace.json／README 三處同步，manifest 不再多一處
        manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertNotIn("version", manifest)


class SkillFrontmatter(unittest.TestCase):
    def test_every_skill_frontmatter_loads(self) -> None:
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                fields = parse_frontmatter(skill.read_text(encoding="utf-8"))
                name = fields.get("name", "")
                self.assertEqual(name, skill.parent.name)
                self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertLessEqual(len(name), 64)
                description = fields.get("description", "")
                self.assertTrue(description.strip(), "description 空白，Pi 不會載入")
                self.assertLessEqual(len(description), 1024)

    def test_pi_loader_accepts_every_skill(self) -> None:
        # 有裝 Pi 時直接用 Pi 自己的 loader 驗；沒裝就跳過（CI 無 Pi）
        pi = shutil.which("pi")
        loader = pathlib.Path(os.path.realpath(pi)).parent.parent / "core" / "skills.js" if pi else None
        if not loader or not loader.exists():
            self.skipTest("Pi 未安裝")
        script = (
            f"const m = await import({json.dumps(loader.as_uri())});"
            f"const r = m.loadSkillsFromDir({{dir: {json.dumps(str(ROOT / 'skills'))}, source: 'path'}});"
            "console.log(JSON.stringify({n: r.skills.length, d: r.diagnostics}));"
        )
        out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
        result = json.loads(out.stdout)
        self.assertEqual(result["d"], [])
        self.assertEqual(result["n"], len(list((ROOT / "skills").glob("*/SKILL.md"))))


class HarnessTerms(unittest.TestCase):
    def test_every_skill_points_to_harness_terms(self) -> None:
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                body = FRONTMATTER.sub("", skill.read_text(encoding="utf-8"), count=1)
                self.assertIn(POINTER, "\n".join(body.splitlines()[:6]), "指向要放在標題下方前幾行")

    def test_claude_terms_have_neutral_definition(self) -> None:
        text = terms_text()
        missing: dict[str, str] = {}
        for path in scanned_files():
            content = path.read_text(encoding="utf-8")
            rel = str(path.relative_to(ROOT))
            found = {term for term, rx in FIXED_TERMS.items() if re.search(rx, content)}
            found |= {tool for tool in CLAUDE_TOOLS if re.search(rf"\b{tool}\b", content)}
            found |= {m.group(0).strip("${}") for m in ENV_VAR.finditer(content)}
            found |= {f"mcp__{m.group(1)}__" for m in MCP_PREFIX.finditer(content)}
            for term in found:
                probe = "${" + term + "}" if term.startswith("CLAUDE_") else term
                if not defined(probe, text):
                    missing.setdefault(term, rel)
        self.assertEqual(missing, {}, "以下 Claude 專屬用語在 references/harness-terms.md 沒有對照（term → 首見檔）")

    def test_non_spec_frontmatter_keys_are_explained(self) -> None:
        text = terms_text()
        keys = set()
        for skill in (ROOT / "skills").glob("*/SKILL.md"):
            keys |= set(parse_frontmatter(skill.read_text(encoding="utf-8"))) - SPEC_KEYS
        self.assertEqual({k for k in keys if not defined(f"{k}:", text)}, set())

    def test_agents_use_plugin_root_paths(self) -> None:
        for agent in sorted((ROOT / "agents").glob("*.md")):
            with self.subTest(agent=agent.name):
                self.assertEqual(BARE_PLUGIN_PATH.findall(agent.read_text(encoding="utf-8")), [])

    def test_agent_tools_have_pi_mapping(self) -> None:
        # agent frontmatter tools: 的每個 Claude 工具都要在對照表有 Pi 工具名，才能轉成 subagent tools 白名單
        text = terms_text()
        missing = set()
        for agent in (ROOT / "agents").glob("*.md"):
            tools = parse_frontmatter(agent.read_text(encoding="utf-8")).get("tools", "")
            for tool in (t.strip() for t in tools.split(",") if t.strip()):
                if not tool.startswith("mcp__") and not defined(tool, text):
                    missing.add(tool)
        self.assertEqual(missing, set())

    def test_no_main_session_fallback_for_agents(self) -> None:
        # 多數 skill 寫明主 session 不做 agent 的工作（linear-create 主 session 不呼叫 save_issue）
        self.assertNotIn("改在當前 session 依 agent 內文逐一執行", terms_text())


if __name__ == "__main__":
    unittest.main()
