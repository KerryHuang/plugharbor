#!/usr/bin/env python3
"""停用的 plugharbor plugin／skill 補救：讓 /doctor 關掉的能力在需要時還找得到。

起因：在別的專案跑 /doctor 會把少用的 plugin 寫成 enabledPlugins: false（常寫在 user 層，所有專案一起失效），
之後要用時清單裡已經沒有它，agent 也不知道它存在。
- SessionStart：只注入一行名稱，細節寫進 ~/.claude/disabled-skills/<專案雜湊>.md。
- UserPromptSubmit：使用者訊息命中停用 skill 的觸發詞（frontmatter `triggers` ∪ description「」片語）才注入，
  同 session 同一項只提示一次。
- `disabled-skills.py ignore <項目> --cwd <專案>`：使用者回「不要」時由 agent 呼叫，只在該專案忽略。
只看明確的 false 與 skillOverrides "off"；從沒啟用的專案層 plugin 是刻意不裝，不列。任何錯誤都 fail-open。
"""
import hashlib
import json
import os
import re
import shlex
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

MARKETPLACE = "plugharbor"
MIN_PHRASE = 4


@dataclass
class Skill:
    plugin: str
    name: str
    path: Path
    manual_only: bool
    phrases: list = field(default_factory=list)


@dataclass
class Item:
    key: str
    kind: str  # "plugin" | "skill"
    fix: str
    skills: list = field(default_factory=list)


def load(path):
    return load_checked(path)[0]


def load_checked(path):
    """回傳 (dict, 讀得完整)。不存在算完整（就是沒設定）；存在卻讀不到或壞掉算不完整。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, True
    except (OSError, ValueError):
        return {}, False  # 壞掉的檔，Claude Code 本身也整份忽略
    return (data, True) if isinstance(data, dict) else ({}, False)


def state_dir(home):
    return home / ".claude/disabled-skills"


def label(description):
    for sep in ("——", " — "):
        if sep in description:
            return description.split(sep, 1)[0].strip()
    return description[:20]


def frontmatter(path):
    """單行 key: value，description 另支援 `>-` 摺疊（後續縮排行）。"""
    try:
        lines = path.read_text(encoding="utf-8").split("\n")
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    fm, last = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            last = m.group(1)
            fm[last] = m.group(2).strip()
        elif last and line.startswith((" ", "\t")):
            fm[last] = (fm[last].lstrip(">-|").strip() + " " + line.strip()).strip()
    return fm


def phrases_of(fm):
    # description 的「」片語若是不含空白的純英文單字（如 commit、build），太泛、易誤觸，只接受 triggers 明寫的
    found = [p for p in re.findall(r"「([^」]+)」", fm.get("description", ""))
             if not re.fullmatch(r"[\x21-\x7e]+", p.strip())]
    try:
        triggers = json.loads(fm.get("triggers") or "[]")
    except ValueError:
        triggers = []
    if isinstance(triggers, list):
        found += [t for t in triggers if isinstance(t, str)]
    return list(dict.fromkeys(p.strip() for p in found if len(p.strip()) >= MIN_PHRASE))


def load_catalog(marketplace):
    """plugin 名 → skill 清單（只含 marketplace.json 列出的 plugin）。"""
    catalog = {}
    for entry in load(marketplace / ".claude-plugin/marketplace.json").get("plugins", []):
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        skills = []
        for md in sorted((marketplace / "plugins" / name / "skills").glob("*/SKILL.md")):
            fm = frontmatter(md)
            skills.append(Skill(name, md.parent.name, md, fm.get("disable-model-invocation") == "true", phrases_of(fm)))
        catalog[name] = skills
    return catalog


def labels(marketplace):
    return {e.get("name"): label(e.get("description", ""))
            for e in load(marketplace / ".claude-plugin/marketplace.json").get("plugins", [])}


def settings(home, cwd):
    """回傳 (enabled, overrides, 三層都讀得完整)。"""
    enabled, overrides, complete = {}, {}, True
    for scope, path in [("user", home / ".claude/settings.json"), ("project", cwd / ".claude/settings.json"),
                        ("local", cwd / ".claude/settings.local.json")]:
        data, ok = load_checked(path)
        complete = complete and ok
        plugins, skills = data.get("enabledPlugins"), data.get("skillOverrides")
        for key, value in (plugins.items() if isinstance(plugins, dict) else ()):
            enabled[key] = (value, scope)
        for key, value in (skills.items() if isinstance(skills, dict) else ()):
            overrides[key] = (value, path)
    return enabled, overrides, complete


def project_key(cwd):
    return str(Path(cwd).resolve())


def read_ignores(home):
    return {k: v for k, v in load(state_dir(home) / "ignore.json").items() if isinstance(v, list)}


def write_ignores(home, data):
    path = state_dir(home) / "ignore.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def add_ignore(home, cwd, key):
    data = read_ignores(home)
    keys = data.setdefault(project_key(cwd), [])
    if key not in keys:
        keys.append(key)
    write_ignores(home, data)


def marketplace_root(home):
    location = load(home / ".claude/plugins/known_marketplaces.json").get(MARKETPLACE, {})
    location = location.get("installLocation") if isinstance(location, dict) else None
    return Path(location) if isinstance(location, str) and location else None


def all_disabled(home, cwd, catalog):
    """回傳 (停用項目, 資料是否完整可據以 prune)。"""
    enabled, overrides, complete = settings(home, cwd)
    items = []
    for name, skills in catalog.items():
        value, scope = enabled.get(f"{name}@{MARKETPLACE}", (None, None))
        if value is False:
            items.append(Item(name, "plugin", f"claude plugin enable {name}@{MARKETPLACE} --scope {scope}",
                              [s for s in skills if not s.manual_only]))
    for key, (value, path) in sorted(overrides.items()):
        plugin, _, name = key.partition(":")
        if value != "off" or not name or enabled.get(f"{plugin}@{MARKETPLACE}", (None,))[0] is not True:
            continue
        skill = next((s for s in catalog.get(plugin, []) if s.name == name), None)
        if skill and not skill.manual_only:
            items.append(Item(key, "skill", f"刪掉 `{path}` 裡 skillOverrides 的 `{key}`", [skill]))
    return items, complete and bool(catalog)


def disabled_items(home, cwd):
    """回傳 (marketplace 的 plugins 目錄, 停用中且未被忽略的項目)；順手把已重新啟用的項目移出忽略清單。"""
    mp = marketplace_root(home)
    if mp is None:
        return None, []
    items, complete = all_disabled(home, cwd, load_catalog(mp))
    current = {i.key for i in items}
    data, pk = read_ignores(home), project_key(cwd)
    ignored = data.get(pk, [])
    kept = [k for k in ignored if k in current]
    # 只有讀到完整資料才 prune：marketplace 更新中、設定檔暫時壞掉時，集合會變空，不能據此清掉使用者的「不要」
    if complete and kept != ignored:
        if kept:
            data[pk] = kept
        else:
            data.pop(pk, None)
        write_ignores(home, data)
    return mp / "plugins", [i for i in items if i.key not in ignored]


def ignore_command(cwd, key):
    args = ["python3", str(Path(__file__).resolve()), "ignore", key, "--cwd", project_key(cwd)]
    return " ".join(shlex.quote(a) for a in args)


def write_details(home, cwd, plugins_dir, items):
    path = state_dir(home) / (hashlib.sha1(project_key(cwd).encode("utf-8")).hexdigest()[:12] + ".md")
    names = labels(plugins_dir.parent)
    out = [f"# 停用中的 plugharbor 項目（{project_key(cwd)}）", "",
           "用之前先用 AskUserQuestion 問使用者：「用它並重開」（讀 SKILL.md 照做並跑重開指令）、"
           "「只這次用」（讀 SKILL.md 照做，不改設定）、「不要」（跑忽略指令，不用）。"
           "SKILL.md 裡的 `${CLAUDE_PLUGIN_ROOT}` 換成該 plugin 目錄。", ""]
    for item in items:
        plugin = item.key.split(":", 1)[0]
        out += [f"## {item.key}（{names.get(plugin, '')}）", "",
                f"- plugin 目錄：`{plugins_dir / plugin}`",
                f"- 重開：`{item.fix}`",
                f"- 忽略：`{ignore_command(cwd, item.key)}`"]
        out += [f"- `{s.plugin}:{s.name}`：`{s.path}`" for s in item.skills]
        out.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def emit(event, text):
    out = json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}, ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))


def on_session_start(home, cwd):
    plugins_dir, items = disabled_items(home, cwd)
    if not items:
        return
    details = write_details(home, cwd, plugins_dir, items)
    emit("SessionStart", f"[toolkit] plugharbor 停用中：{'、'.join(i.key for i in items)}"
                         f"（用到前先問使用者；細節見 `{details}`）")


def hit(phrase, text):
    """ASCII 不分大小寫；片語兩端是英數字時要求字邊界（hangfire 不命中 hangfires）。"""
    p = phrase.lower()
    left = r"(?<![a-z0-9])" if re.match(r"[a-z0-9]", p) else ""
    right = r"(?![a-z0-9])" if re.search(r"[a-z0-9]$", p) else ""
    return re.search(left + re.escape(p) + right, text) is not None


def match(items, prompt, seen=frozenset()):
    """命中的 (Item, Skill)，依 items 與 skill 順序，略過已提示過的 `plugin:skill`，最多 3 個。"""
    text, hits = prompt.lower(), []
    for item in items:
        for skill in item.skills:
            if f"{skill.plugin}:{skill.name}" not in seen and any(hit(p, text) for p in skill.phrases):
                hits.append((item, skill))
                if len(hits) == 3:
                    return hits
    return hits


def asked(home, session_id):
    """同 session 已提示過的項目；session_id 缺就不去重。順手清掉 7 天前的紀錄。"""
    if not isinstance(session_id, str) or not re.fullmatch(r"[\w-]+", session_id):
        return None, set()
    folder = state_dir(home) / "sessions"
    folder.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 7 * 86400
    for old in folder.glob("*.json"):
        if old.stat().st_mtime < cutoff:
            old.unlink()
    path = folder / f"{session_id}.json"
    try:
        seen = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = []
    return path, set(seen if isinstance(seen, list) else [])


def on_prompt(home, cwd, prompt, session_id):
    if not isinstance(prompt, str) or not prompt.strip():
        return
    plugins_dir, items = disabled_items(home, cwd)
    record, seen = asked(home, session_id)
    hits = match(items, prompt, seen)
    if not hits:
        return
    if record:
        shown = {f"{s.plugin}:{s.name}" for _, s in hits}
        record.write_text(json.dumps(sorted(seen | shown), ensure_ascii=False), encoding="utf-8")
    lines = [f"- {s.plugin}:{s.name}：`{s.path}`；重開 `{i.fix}`；忽略 `{ignore_command(cwd, i.key)}`" for i, s in hits]
    emit("UserPromptSubmit",
         "[toolkit] 這則訊息可能用得上被停用的 plugharbor skill。用之前先用 AskUserQuestion 問使用者："
         "「用它並重開」（讀 SKILL.md 照做並跑重開指令）、「只這次用」（讀 SKILL.md 照做，不改設定）、"
         "「不要」（跑忽略指令，不用）。SKILL.md 裡的 `${CLAUDE_PLUGIN_ROOT}` 換成該 plugin 目錄。\n" + "\n".join(lines))


def main(argv):
    home = Path.home()
    if len(argv) > 2 and argv[1] == "ignore":
        cwd = argv[argv.index("--cwd") + 1] if "--cwd" in argv[:-1] else "."
        add_ignore(home, Path(cwd), argv[2])
        return 0
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    # 專案根目錄優先用 CLAUDE_PROJECT_DIR：payload 的 cwd 會跟著 session 內的 cd 走到子目錄
    cwd = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        on_session_start(home, cwd)
    elif event == "UserPromptSubmit":
        on_prompt(home, cwd, payload.get("prompt"), payload.get("session_id"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # noqa: BLE001 — hook 一律 fail-open，不擋 session
        sys.exit(0)
