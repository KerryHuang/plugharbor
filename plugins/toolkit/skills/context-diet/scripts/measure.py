#!/usr/bin/env python3
"""量測每個 session 無條件進 context 的設定量，並統計近期實際使用證據。

用法：
  python3 measure.py [--project <dir>] [--days 28] [--all-projects] [--json]

輸出兩張表：
  1. 載入量：user 層／專案層 CLAUDE.md、全域 rules、scoped rules（附 paths）、MEMORY.md、
     各 plugin／本地 skill 的 description 總量、agent description＋tools 總量
  2. 使用證據：近 N 天 transcript（含 subagent）內 Skill 呼叫、subagent 派發、MCP server 呼叫次數；
     預設只看 --project 的 transcript，判 user 層／plugin 的去留要加 --all-projects
估 tokens：CJK 1 字≈1 token、其餘 4 字≈1 token（粗估，只用來排序，不當精確值）。
"""
import argparse, glob, json, os, re, sys, time
from collections import Counter

H = os.path.expanduser('~')


def read(p):
    try:
        return open(p, encoding='utf-8', errors='ignore').read()
    except OSError:
        return ''


def est_tokens(s):
    cjk = sum(1 for c in s if '\u2e80' <= c <= '\u9fff' or '\uff00' <= c <= '\uffef')
    return int(cjk + (len(s) - cjk) / 4)


def frontmatter(p):
    m = re.match(r'---\n(.*?)\n---', read(p), re.S)
    return m.group(1) if m else ''


def field(p, name):
    m = re.search(rf'^{name}:\s*(.*?)(?=\n\w[\w-]*:|\Z)', frontmatter(p), re.S | re.M)
    return m.group(1).strip() if m else ''


def paths_of(p):
    fm = frontmatter(p)
    m = re.search(r'^paths:\s*\n((?:\s+-.*\n?)+)', fm, re.M)
    return [x.strip(' -"\'') for x in m.group(1).strip().splitlines()] if m else []


def expand_includes(p, seen=None):
    """CLAUDE.md 的 @include 展開（相對路徑，遞迴），回傳合併後全文。"""
    seen = seen or set()
    s = read(p)
    out = s
    for inc in re.findall(r'^@(\S+)$', s, re.M):
        q = os.path.join(os.path.dirname(p), inc)
        if os.path.isfile(q) and q not in seen:
            seen.add(q)
            out += expand_includes(q, seen)
    return out


def enabled_plugins(project):
    en = {}
    for sp in [f'{H}/.claude/settings.json', f'{project}/.claude/settings.json',
               f'{project}/.claude/settings.local.json', f'{H}/.claude/settings.local.json']:
        try:
            en.update(json.load(open(sp)).get('enabledPlugins', {}))
        except Exception:
            pass
    return {k for k, v in en.items() if v}


def plugin_roots(project):
    """回傳 {plugin@marketplace: 目錄}。三個來源依序疊：快取目錄（取最新版）、installed_plugins.json、
    known_marketplaces.json（directory 型 marketplace 依其 marketplace.json 的 source 相對路徑解析）。"""
    roots = {}
    for d in glob.glob(f'{H}/.claude/plugins/cache/*/*/*/'):
        mk, name, ver = d.rstrip('/').split('/')[-3:]
        key = f'{name}@{mk}'
        if key not in roots or ver > roots[key][0]:
            roots[key] = (ver, d)
    roots = {k: v[1] for k, v in roots.items()}
    try:
        inst = json.load(open(f'{H}/.claude/plugins/installed_plugins.json')).get('plugins') or {}
        for key, entries in inst.items():
            for e in (entries if isinstance(entries, list) else [entries]):
                path = e.get('installPath')
                if path and os.path.isdir(path):
                    roots[key] = path
    except Exception:
        pass
    try:
        known = json.load(open(f'{H}/.claude/plugins/known_marketplaces.json'))
        for mk, info in known.items():
            loc = info.get('installLocation')
            try:
                mj = json.load(open(f'{loc}/.claude-plugin/marketplace.json'))
            except Exception:
                continue
            for pl in mj.get('plugins', []):
                src = pl.get('source')
                if isinstance(src, str) and not src.startswith(('http', 'git@')):
                    path = os.path.normpath(os.path.join(loc, src))
                    if os.path.isdir(path):
                        roots.setdefault(f'{pl["name"]}@{mk}', path)
    except Exception:
        pass
    return roots


def measure(project):
    rows = []  # (group, name, chars, tokens, note)

    def add(group, name, s, note=''):
        rows.append((group, name, len(s), est_tokens(s), note))

    # user 層
    u = f'{H}/.claude/CLAUDE.md'
    if os.path.isfile(u):
        add('每次載入', '~/.claude/CLAUDE.md（含 @include）', expand_includes(u))
    for f in sorted(glob.glob(f'{H}/.claude/rules/*.md')):
        ps = paths_of(f)
        add('每次載入' if not ps else 'scoped', f'~/.claude/rules/{os.path.basename(f)}', read(f), ' '.join(ps))
    # 專案層
    c = f'{project}/CLAUDE.md'
    if os.path.isfile(c):
        add('每次載入', 'CLAUDE.md', read(c))
    for f in sorted(glob.glob(f'{project}/.claude/rules/*.md')):
        ps = paths_of(f)
        add('每次載入' if not ps else 'scoped', f'.claude/rules/{os.path.basename(f)}', read(f), ' '.join(ps))
    # memory
    slug = re.sub(r'[^A-Za-z0-9]', '-', project)  # Claude Code 的目錄命名：非英數一律換 -（Windows 為 D--Repos-…）
    mem = f'{H}/.claude/projects/{slug}/memory/MEMORY.md'
    if os.path.isfile(mem):
        s = read(mem)
        add('每次載入', 'MEMORY.md', s, f'{len(s.splitlines())} 行，中位 {sorted(len(l) for l in s.splitlines())[len(s.splitlines()) // 2]} 字/行')
    # skills / agents
    en = enabled_plugins(project)
    sources = {'本地 .claude/skills': f'{project}/.claude', 'user ~/.claude/skills': f'{H}/.claude'}
    for key, d in plugin_roots(project).items():
        if key in en:
            sources[f'plugin {key}'] = d
    sources['claude.ai synced'] = f'{H}/.claude/skills/synced/*'
    for label, root in sources.items():
        sk = glob.glob(f'{root}/skills/*/SKILL.md') if label != 'claude.ai synced' else glob.glob(f'{root}/*/SKILL.md')
        ag = glob.glob(f'{root}/agents/*.md')
        hidden = [p for p in sk if field(p, 'disable-model-invocation') == 'true']
        sk = [p for p in sk if p not in hidden]  # description 不進 system prompt，不計
        if sk:
            s = ''.join(field(p, 'description') for p in sk)
            add('skill desc', label, s, f'{len(sk)} skills' + (f'，另 {len(hidden)} 支手動限定未計' if hidden else ''))
        if ag:
            s = ''.join(field(p, 'description') + field(p, 'tools') for p in ag)
            add('agent desc+tools', label, s, f'{len(ag)} agents')
    return rows, slug


def usage(slug, days, all_projects=False):
    since = time.time() - days * 86400
    skills, agents, mcp, slash = Counter(), Counter(), Counter(), Counter()
    base = f'{H}/.claude/projects/' + ('*' if all_projects else glob.escape(slug))
    files = [f for f in glob.glob(f'{base}/**/*.jsonl', recursive=True) if os.path.getmtime(f) >= since]
    for f in files:
        s = read(f)
        skills.update(re.findall(r'"name":"Skill","input":\{"skill":"([^"]+)"', s))
        agents.update(re.findall(r'"subagent_type":"([^"]+)"', s))
        mcp.update(m.split('__')[1] for m in re.findall(r'"name":"(mcp__[A-Za-z0-9_-]+__)', s))
        slash.update(re.findall(r'<command-name>(/[^<]+)</command-name>', s))
    return len(files), skills, agents, mcp, slash


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default=os.getcwd())
    ap.add_argument('--days', type=int, default=28)
    ap.add_argument('--all-projects', action='store_true', help='使用證據掃所有專案的 transcript')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    project = os.path.abspath(a.project)
    rows, slug = measure(project)
    n, skills, agents, mcp, slash = usage(slug, a.days, a.all_projects)
    if a.json:
        json.dump({'rows': rows, 'transcripts': n, 'skills': skills, 'agents': agents, 'mcp': mcp, 'slash': slash},
                  sys.stdout, ensure_ascii=False, indent=1)
        return
    print(f'# 載入量（{project}）\n')
    print(f'{"群組":16s} {"字元":>6s} {"~tok":>6s}  來源')
    tot = Counter()
    for g, name, ch, tk, note in sorted(rows, key=lambda r: (r[0], -r[3])):
        tot[g] += tk
        print(f'{g:16s} {ch:6d} {tk:6d}  {name}{"  [" + note + "]" if note else ""}')
    print()
    for g, tk in tot.most_common():
        print(f'  {g:16s} ≈ {tk:,} tokens')
    always = tot['每次載入'] + tot['skill desc'] + tot['agent desc+tools']
    print(f'\n  每 session 無條件 ≈ {always:,} tokens（scoped rules 另計，碰到路徑才載）')
    scope = '所有專案' if a.all_projects else '本專案'
    print(f'\n# 使用證據（近 {a.days} 天，{scope} {n} 份 transcript 含 subagent；只涵蓋本機）\n')
    for title, c in [('Skill 呼叫', skills), ('subagent 派發', agents), ('MCP server', mcp), ('使用者 slash', slash)]:
        print(f'## {title}')
        for k, v in c.most_common(40):
            print(f'  {v:5d}  {k}')
        print()


if __name__ == '__main__':
    main()
