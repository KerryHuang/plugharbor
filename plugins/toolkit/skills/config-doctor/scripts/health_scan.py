# config-doctor Phase 1：結構與存在性掃描（機械、唯讀）
# 用法：python health_scan.py [--project <dir>] [--marketplace <dir>]
#   --project      要掃的專案根目錄（預設：目前工作目錄）；不掃專案層傳 --project ""
#   --marketplace  自家 plugin marketplace 源碼目錄（選填；給了才掃 plugin 結構與版本一致性）
# 輸出：FINDING|<P0-P3>|<area>|<message> 逐行 + SUMMARY JSON。
# 注意：結果是「疑點」非「結論」——P0 也可能是刻意設計或範例文字誤判，逐項驗證後才定案。
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path

findings: list[tuple[str, str, str]] = []


def add(sev: str, area: str, msg: str) -> None:
    findings.append((sev, area, msg))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def frontmatter(text: str) -> dict[str, str] | None:
    """粗略解析 YAML frontmatter 第一層 key（不依賴 pyyaml）。"""
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2).strip()
    return fm


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)  # 程式碼區塊與 inline code 裡的連結是範例，不檢查


def check_md_links(md: Path, layer: str) -> None:
    for target in LINK_RE.findall(CODE_RE.sub("", read(md))):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        t = target.split("#")[0]
        if not t:
            continue
        if not (md.parent / t).exists():
            add("P0", layer, f"斷鏈 {md.name} → {target}（{md.parent}）｜注意：文中「範例連結」會誤報，須人工判")


def check_skill_dir(d: Path, layer: str) -> None:
    sk = d / "SKILL.md"
    if not sk.exists():
        add("P0", layer, f"skill 目錄無 SKILL.md：{d}｜可能是本地 plugin 等刻意形態，先查用途再定案")
        return
    text = read(sk)
    fm = frontmatter(text)
    if fm is None:
        add("P0", layer, f"SKILL.md 無合法 frontmatter：{sk}")
        return
    if "name" in fm and fm["name"] != d.name:
        add("P1", layer, f"SKILL.md name「{fm['name']}」≠ 目錄名「{d.name}」：{sk}")
    if not fm.get("description"):
        add("P0", layer, f"SKILL.md 缺 description（無法被觸發）：{sk}")
    known = {"name", "description", "argument-hint", "arguments", "disable-model-invocation",
             "user-invocable", "allowed-tools", "disallowed-tools", "model", "effort",
             "context", "agent", "background", "hooks", "license", "metadata"}
    for k in fm:
        if k not in known:
            add("P2", layer, f"SKILL.md 非標準 frontmatter 欄位「{k}:」：{sk}")
    lines = text.count("\n") + 1
    if lines > 500:
        add("P2", layer, f"SKILL.md {lines} 行（官方建議 <500，宜拆 references/）：{sk}")
    check_md_links(sk, layer)


def check_rules(rules_dir: Path, layer: str) -> None:
    if not rules_dir.exists():
        return
    for r in sorted(rules_dir.glob("*.md")):
        text = read(r)
        fm = frontmatter(text)
        if fm is None or "paths" not in text.split("---")[1 if text.startswith("---") else 0]:
            add("P3", layer, f"rule 無 frontmatter paths（全域載入；可能刻意）：{r.name}")
        check_md_links(r, layer)


def check_agents(agents_dir: Path, layer: str) -> None:
    if not agents_dir.exists():
        return
    entries = list(agents_dir.iterdir())
    if not entries:
        add("P3", layer, f"agents/ 為空目錄：{agents_dir}")
    for a in agents_dir.glob("*.md"):
        fm = frontmatter(read(a))
        if fm is None or "name" not in fm or not fm.get("description"):
            add("P0", layer, f"agent frontmatter 不完整（name/description）：{a}")


def check_settings(sp: Path, layer: str) -> dict:
    if not sp.exists():
        return {}
    try:
        cfg = json.loads(read(sp))
    except json.JSONDecodeError as e:
        add("P0", layer, f"settings JSON 解析失敗：{sp}（{e}）")
        return {}
    for _event, groups in (cfg.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                for token in re.findall(r"[$\w~{}:\\/.-]+\.(?:mjs|cjs|sh|py|ps1|js|ts)", h.get("command", "")):
                    resolved = resolve_path(token)
                    if resolved is None:
                        add("P3", layer, f"hook 路徑含無法靜態解析的變數，未驗證存在性：{token}（{sp.name}）")
                    elif not Path(resolved).exists():
                        add("P0", layer, f"hook 指向不存在的腳本：{token}（{sp.name}）")
    sl = cfg.get("statusLine", {})
    if isinstance(sl, dict) and sl.get("command"):
        for token in re.findall(r"[$\w~{}:\\/.-]+\.(?:mjs|cjs|sh|py|ps1|js|ts)", sl["command"]):
            resolved = resolve_path(token)
            if resolved is None:
                add("P3", layer, f"statusLine 路徑含無法靜態解析的變數，未驗證存在性：{token}")
            elif not Path(resolved).exists():
                add("P0", layer, f"statusLine 指向不存在的腳本：{token}")
    return cfg


def scan_layer(root: Path, tag: str) -> dict:
    """掃一個 .claude 層（user 或 project）。回傳 settings dict 供 plugin 對齊檢查。"""
    if (root / "skills").exists():
        for d in (root / "skills").iterdir():
            if d.is_dir() and d.name != "synced":  # synced/ 是 claude.ai 同步區，結構由官方管
                check_skill_dir(d, f"{tag}/skills")
    check_rules(root / "rules", f"{tag}/rules")
    check_agents(root / "agents", f"{tag}/agents")
    # agents/ 空目錄由 check_agents 回報，此處跳過避免雙報
    for sub in ("skills", "rules", "hooks", "scripts", "designs"):
        base = root / sub
        if not base.exists():
            continue
        for d in [base, *base.rglob("*")]:
            if d.is_dir() and not any(d.iterdir()):
                add("P3", tag, f"空目錄：{d}")
    return check_settings(root / "settings.json", f"{tag}/settings")


def check_claude_md(cm: Path, base: Path, tag: str) -> None:
    if not cm.exists():
        return
    text = read(cm)
    for imp in re.findall(r"@([\w./-]+\.md)", text):
        if not (cm.parent / imp).exists():
            add("P0", tag, f"@import 斷鏈：@{imp}")
    for ref in re.findall(r"`\.?/?\.claude/(rules/[\w-]+\.md)`", text) + re.findall(r"`(rules/[\w-]+\.md)`", text):
        if not (base / ref).exists():
            add("P0", tag, f"文字索引斷鏈：{ref}")


def resolve_path(token: str):
    """展開路徑中的家目錄寫法。仍含無法靜態解析的變數（$CLAUDE_PROJECT_DIR 等）時回 None。"""
    home = str(Path.home())
    t = token.replace("${HOME}", home).replace("$HOME", home).replace("~", home)
    return None if "$" in t else t


def check_plugins_state(user: Path, cfgs: list[dict]) -> dict[str, str]:
    reg = user / "plugins/installed_plugins.json"
    installed: dict[str, str] = {}
    if not reg.exists():
        return installed
    data = json.loads(read(reg))
    cwd = str(Path.cwd())
    for full, recs in data.get("plugins", {}).items():
        for rec in recs:
            if rec.get("projectPath", "").replace("\\", "/").lower() == cwd.replace("\\", "/").lower():
                installed[full] = rec["version"]
            if rec.get("scope") == "user":
                installed.setdefault(full, rec["version"])
    # directory 來源的 marketplace 就地載入，不寫進 installed_plugins.json，不該報未安裝
    dir_markets = {
        n for cfg in cfgs
        for n, m in (cfg.get("extraKnownMarketplaces") or {}).items()
        if (m.get("source") or {}).get("source") == "directory"
    }
    for cfg in cfgs:
        for name, enabled in (cfg.get("enabledPlugins") or {}).items():
            if enabled and name not in installed and name.split("@")[-1] not in dir_markets:
                add("P1", "plugins", f"enabledPlugins 啟用了未安裝的 plugin：{name}")
    return installed


def scan_marketplace(mkt: Path, installed: dict[str, str]) -> None:
    mj = mkt / ".claude-plugin/marketplace.json"
    if not mj.exists():
        add("P0", "mkt", f"找不到 marketplace.json：{mj}")
        return
    for p in json.loads(read(mj)).get("plugins", []):
        name, ver = p["name"], p.get("version")
        pj = mkt / "plugins" / name / ".claude-plugin/plugin.json"
        if not pj.exists():
            add("P0", "mkt", f"marketplace.json 列了 {name} 但無 plugin.json")
            continue
        real = json.loads(read(pj)).get("version")
        if ver != real:
            add("P1", "mkt", f"{name} 版本不一致：marketplace.json={ver} vs plugin.json={real}")
        inst = next((v for k, v in installed.items() if k.startswith(name + "@")), None)
        if inst and inst != real:
            add("P1", "mkt", f"{name} 安裝版 {inst} 落後源碼版 {real}（需 /plugin 更新才生效）")
    for pdir in (mkt / "plugins").iterdir():
        if not pdir.is_dir():
            continue
        tag = f"mkt/{pdir.name}"
        if (pdir / "skills").exists():
            for d in (pdir / "skills").iterdir():
                if d.is_dir():
                    check_skill_dir(d, tag)
        check_agents(pdir / "agents", tag)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--marketplace", default="")
    args = ap.parse_args()

    user = Path.home() / ".claude"
    cfgs = [scan_layer(user, "user")]
    check_claude_md(user / "CLAUDE.md", user, "user/CLAUDE.md")

    if args.project:
        proj_root = Path(args.project).resolve()
        cfgs.append(scan_layer(proj_root / ".claude", "proj"))
        check_claude_md(proj_root / "CLAUDE.md", proj_root / ".claude", "proj/CLAUDE.md")

    installed = check_plugins_state(user, cfgs)
    if args.marketplace:
        scan_marketplace(Path(args.marketplace).resolve(), installed)

    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    for sev, area, msg in sorted(findings, key=lambda f: (order[f[0]], f[1])):
        print(f"FINDING|{sev}|{area}|{msg}")
    print("SUMMARY|" + json.dumps(Counter(f[0] for f in findings), ensure_ascii=False))


if __name__ == "__main__":
    main()
