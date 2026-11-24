#!/usr/bin/env python3
"""由 agents/*.md 產生 Pi 的角色包（pi/roles/<plugin>-<agent>.md），由 pi/roles.ts 註冊給 pi-herdr-agents。

pi-herdr-agents 的角色包協定：extension 回應 `pi-herdr-subagents:roles:discover:v1` 事件、
register 一個目錄，目錄下每個 .md 是一個角色；派工時 `subagent({ agent: "<plugin>-<agent>", ... })`。
它的 frontmatter 逐行讀 `key: value`，不經 YAML，值不加引號。

本檔在多個 plugin 各放一份完全相同的副本（plugin 須能單獨安裝；CI 驗兩份同步），
plugin 名取自本檔所在的 plugin 目錄。

對應：
  name           <plugin>-<agent>，原檔名已以 <plugin>- 開頭就不重複加；與檔名相同（不帶前綴會和使用者自己的角色撞名）
  description    原檔 description
  model          不寫（Pi 的模型名與 Claude 不同）；原等級寫進本文，由派工端挑模型
  thinking       原檔 model 的等級：haiku → low、sonnet → medium、opus → high
  tools          Read→read、Write→write、Edit→edit、Bash→bash、Grep→grep、Glob→find＋ls、Agent→subagent；
                 mcp__<server>__<tool> 的 server 段連字號換底線（Pi 的 MCP 工具名）；
                 WebSearch、WebFetch 在 Pi 沒有對應，略過並在本文註明
  spawning       原檔沒有 Agent 就 false
  maxTurns       寫進本文開頭當停損
  本文           原樣放在 system prompt 之後（system-prompt: append）

跑法：python3 plugins/<plugin>/scripts/gen-pi-roles.py          重新產生
      python3 plugins/<plugin>/scripts/gen-pi-roles.py --check  只比對，有差異就 exit 1（測試用）
"""
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT.name
AGENTS = ROOT / "agents"
OUT = ROOT / "pi" / "roles"
THINKING = {"haiku": "low", "sonnet": "medium", "opus": "high"}
TOOLS = {"Read": ["read"], "Write": ["write"], "Edit": ["edit"], "Bash": ["bash"], "Grep": ["grep"],
         "Glob": ["find", "ls"], "Agent": ["subagent"]}
NO_PI_EQUIVALENT = {"WebSearch", "WebFetch"}


def parse(text: str, name: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{name}: 缺 frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError(f"{name}: frontmatter 沒有結尾")
    meta = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[end + 1:]).strip("\n")


def pi_tools(tool: str, agent: str) -> list[str]:
    if tool in TOOLS:
        return TOOLS[tool]
    if tool.startswith("mcp__"):
        _, server, name = tool.split("__", 2)
        return [f"mcp__{server.replace('-', '_')}__{name}"]
    raise ValueError(f"{agent}: 工具 {tool!r} 沒有 Pi 對應")


def role_name(agent: str) -> str:
    return agent if agent.startswith(f"{PLUGIN}-") else f"{PLUGIN}-{agent}"


def render(path: Path) -> str:
    meta, body = parse(path.read_text(encoding="utf-8"), path.name)
    agent = meta.get("name") or path.stem
    if agent != path.stem:
        raise ValueError(f"{path.name}: name {agent!r} 與檔名不同")
    level = meta.get("model", "")
    if level not in THINKING:
        raise ValueError(f"{path.name}: model {level!r} 沒有 Pi 對應（只支援 {', '.join(THINKING)}）")
    declared = [t.strip() for t in meta.get("tools", "").split(",") if t.strip()]
    dropped = [t for t in declared if t in NO_PI_EQUIVALENT]
    tools = [p for t in declared if t not in NO_PI_EQUIVALENT for p in pi_tools(t, agent)]
    front = ["---", f"name: {role_name(agent)}", f"description: {meta.get('description', '')}",
             f"thinking: {THINKING[level]}"]
    if tools:
        front.append("tools: " + ", ".join(dict.fromkeys(tools)))
    if "Agent" not in declared:
        front.append("spawning: false")
    front += ["system-prompt: append", "session-mode: standalone", "auto-exit: true", "---"]
    header = [
        f"（由 plugins/{PLUGIN}/agents/{path.name} 產生；改原檔後跑 python3 plugins/{PLUGIN}/scripts/gen-pi-roles.py，不要手改。）",
        "目前的 harness 是 Pi。執行前先讀 ${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md，照它的 Pi 對照把"
        f"下面的 Claude 專屬用語換掉；${{CLAUDE_PLUGIN_ROOT}} 是 {PLUGIN} plugin 的根目錄，絕對路徑寫在派工 task 開頭。",
        f"原定義的模型等級是 {level}。",
    ]
    if dropped:
        header.append(f"原定義另有 {'、'.join(dropped)}，Pi 沒有對應工具；需要時回報呼叫端代查。")
    if meta.get("maxTurns", "").isdigit():
        header.append(f"停損：工具呼叫超過約 {meta['maxTurns']} 次仍未完成，就停下回報目前進度與卡點。")
    return "\n".join(front) + "\n\n" + "\n".join(header) + "\n\n" + body.rstrip() + "\n"


def expected() -> dict[str, str]:
    return {f"{role_name(p.stem)}.md": render(p) for p in sorted(AGENTS.glob("*.md"))}


def main(argv: list[str]) -> int:
    want = expected()
    have = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("*.md")} if OUT.is_dir() else {}
    if "--check" in argv:
        bad = sorted(n for n in want.keys() | have.keys() if want.get(n) != have.get(n))
        for n in bad:
            print(f"pi/roles/{n}：{'多出來' if n not in want else '缺少' if n not in have else '與 agents/*.md 不一致'}")
        if bad:
            print(f"跑 python3 plugins/{PLUGIN}/scripts/gen-pi-roles.py 重新產生")
        return 1 if bad else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for n in have.keys() - want.keys():
        (OUT / n).unlink()
    for n, text in want.items():
        with open(OUT / n, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print(f"產生 {len(want)} 個 Pi 角色到 plugins/{PLUGIN}/pi/roles")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
