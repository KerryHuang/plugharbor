#!/usr/bin/env python3
"""SessionStart hook：列出被明確停用的 plugharbor plugin／skill，讓 agent 需要時還找得到。

起因：在別的專案跑 /doctor 會把少用的 plugin 寫成 enabledPlugins: false（常寫在 user 層，所有專案一起失效），
之後要用時清單裡已經沒有它，agent 也不知道它存在。
只看明確的 false 與 skillOverrides "off"：從沒啟用的專案層 plugin 是刻意不裝（如公司 workspace 自帶 sdlc），不列。
依 user → project → local 設定算實際狀態；沒有停用就不輸出（零常駐成本）。
"""
import json
import sys
from pathlib import Path

MARKETPLACE = "plugharbor"


def load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}  # 不存在或壞掉的設定檔，Claude Code 本身也整份忽略
    return data if isinstance(data, dict) else {}


def label(description):
    for sep in ("——", " — "):
        if sep in description:
            return description.split(sep, 1)[0].strip()
    return description[:20]


def manual_only(skill_md):
    try:
        head = skill_md.read_text(encoding="utf-8").split("---", 2)[1]
    except (OSError, IndexError):
        return False
    return any(line.replace(" ", "") == "disable-model-invocation:true" for line in head.splitlines())


def find(home, cwd):
    """回傳 (plugins 目錄, [停用 plugin 行], [關閉 skill 行])。"""
    location = load(home / ".claude/plugins/known_marketplaces.json").get(MARKETPLACE, {}).get("installLocation")
    if not location:
        return None, [], []
    plugins_dir = Path(location) / "plugins"
    catalog = {e.get("name"): e.get("description", "")
               for e in load(Path(location) / ".claude-plugin/marketplace.json").get("plugins", [])}

    enabled, overrides = {}, {}
    for scope, path in [("user", home / ".claude/settings.json"), ("project", cwd / ".claude/settings.json"),
                        ("local", cwd / ".claude/settings.local.json")]:
        data = load(path)
        for key, value in (data.get("enabledPlugins") or {}).items():
            enabled[key] = (value, scope)
        for key, value in (data.get("skillOverrides") or {}).items():
            overrides[key] = (value, path)

    plugins = []
    for name, description in catalog.items():
        value, scope = enabled.get(f"{name}@{MARKETPLACE}", (None, None))
        if value is False:
            plugins.append(f"- {name}（{label(description)}）：`claude plugin enable {name}@{MARKETPLACE} --scope {scope}`")

    skills = []
    for key, (value, path) in sorted(overrides.items()):
        plugin, _, skill = key.partition(":")
        if value != "off" or not skill or enabled.get(f"{plugin}@{MARKETPLACE}", (None,))[0] is not True:
            continue
        if not manual_only(plugins_dir / plugin / "skills" / skill / "SKILL.md"):
            skills.append(f"- {key}：刪掉 `{path}` 裡 skillOverrides 的這個 key")
    return plugins_dir, plugins, skills


def main():
    try:
        cwd = Path(json.load(sys.stdin).get("cwd") or ".")
    except (ValueError, AttributeError):  # stdin 不是 JSON 物件：退回目前目錄
        cwd = Path(".")
    plugins_dir, plugins, skills = find(Path.home(), cwd)
    if not plugins and not skills:
        return 0
    msg = ("[toolkit] 以下 plugharbor plugin／skill 被停用，清單裡看不到但檔案都在。需要時先讀 "
           f"`{plugins_dir}/<plugin>/skills/<skill>/SKILL.md` 照做（`${{CLAUDE_PLUGIN_ROOT}}` 換成 "
           f"`{plugins_dir}/<plugin>`），再用 AskUserQuestion 問要不要重開"
           "（下個 session 或 /reload-plugins 生效；user 層會影響所有專案）。\n"
           + "\n".join(plugins + skills))
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}},
                     ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
