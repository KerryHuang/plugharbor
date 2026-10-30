import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { syncUser, installSupport } from '../sync-user.mjs'
import { inspectCommand } from '../tool-policy.mjs'

const fixture = () => {
  const home = mkdtempSync(join(tmpdir(), 'plugharbor-home-test-'))
  const repo = mkdtempSync(join(tmpdir(), 'plugharbor-repo-test-'))
  mkdirSync(join(repo, 'plugins/toolkit/agents'), { recursive: true })
  writeFileSync(join(repo, 'plugins/toolkit/agents/reviewer.md'), '---\nname: reviewer\ndescription: Review settings.\nmodel: opus\neffort: medium\ntools: ["Read"]\n---\nRead evidence.\n')
  mkdirSync(join(repo, 'setup/home/shared'), { recursive: true })
  mkdirSync(join(repo, 'setup/home/rules'), { recursive: true })
  writeFileSync(join(repo, 'setup/home/CLAUDE.md'), '# User\n@shared/rules.md\n')
  writeFileSync(join(repo, 'setup/home/shared/rules.md'), 'Use Traditional Chinese.\n')
  return { home, repo, rules: join(repo, 'setup/home/rules') }
}
const done = (...dirs) => dirs.forEach(d => rmSync(d, { recursive: true, force: true }))
const agy = home => join(home, '.gemini/config/plugins/plugharbor-home')
const sha = body => createHash('sha256').update(body).digest('hex')

test('sync produces guidance and read-only agents from repo sources, with no skill mirrors', () => {
  const { home, repo } = fixture()
  try {
    assert.ok(syncUser({ home, repo, mcpNames: ['example-mcp'] }).changed.length > 0)
    assert.deepEqual(syncUser({ home, repo, mcpNames: ['example-mcp'] }).changed, [])
    const agent = readFileSync(join(home, '.codex/agents/reviewer.toml'), 'utf8')
    assert.ok(agent.includes('sandbox_mode = "read-only"'))
    assert.ok(agent.includes('plugharbor/runtime.md'))
    assert.ok(agent.includes('[mcp_servers."example-mcp"]\ncommand = "disabled-by-reviewer-policy"\nenabled = false'))
    assert.ok(!agent.includes('model = "opus"'))
    const codex = readFileSync(join(home, '.codex/AGENTS.md'), 'utf8')
    assert.ok(codex.startsWith('<!-- plugharbor:generated -->'))
    assert.ok(codex.includes('Use Traditional Chinese.'))
    assert.ok(readFileSync(join(home, '.pi/agent/APPEND_SYSTEM.md'), 'utf8').startsWith('<!-- plugharbor:generated -->'))
    const agyRoot = readFileSync(join(agy(home), 'rules/plugharbor-root.md'), 'utf8')
    assert.ok(agyRoot.startsWith('---\ntrigger: always_on\n---\n'), agyRoot)
    assert.ok(agyRoot.includes('Use Traditional Chinese.'), agyRoot)
    assert.equal(JSON.parse(readFileSync(join(agy(home), 'plugin.json'), 'utf8')).name, 'plugharbor-home')
    assert.ok(existsSync(join(home, '.codex/plugharbor-manifest.json')))
    assert.ok(!existsSync(join(home, '.agents')), 'no skill mirror')
    assert.ok(!existsSync(join(agy(home), 'skills')), 'no agy skill mirror')
  } finally { done(home, repo) }
})

test('foreign files and manual edits are preserved; ownership does not allow silent overwrites', () => {
  const { home, repo } = fixture()
  try {
    mkdirSync(join(home, '.agents/skills/other'), { recursive: true })
    writeFileSync(join(home, '.agents/skills/other/SKILL.md'), 'foreign')
    syncUser({ home, repo })
    writeFileSync(join(home, '.codex/agents/reviewer.toml'), 'manual edit')
    assert.throws(() => syncUser({ home, repo }), /手動修改|conflict/)
    assert.equal(readFileSync(join(home, '.codex/agents/reviewer.toml'), 'utf8'), 'manual edit')
    assert.equal(readFileSync(join(home, '.agents/skills/other/SKILL.md'), 'utf8'), 'foreign')
  } finally { done(home, repo) }
})

test('migrates claude-home generated files', () => {
  const { home, repo } = fixture()
  try {
    const files = {
      '.agents/skills/config-doctor/SKILL.md': 'old mirror',
      '.gemini/config/plugins/claude-home/skills/config-doctor/SKILL.md': 'old agy mirror',
      '.gemini/config/plugins/claude-home/plugin.json': '{}',
      '.codex/AGENTS.md': 'legacy agents',
      '.agents/skills/edited/SKILL.md': 'was generated',
    }
    const manifest = { files: {}, mcpNames: [] }
    for (const [rel, body] of Object.entries(files)) {
      mkdirSync(join(home, rel, '..'), { recursive: true })
      writeFileSync(join(home, rel), body)
      manifest.files[rel] = sha(body)
    }
    writeFileSync(join(home, '.agents/skills/edited/SKILL.md'), 'user modified this')
    writeFileSync(join(home, '.agents/skills/unlisted.md'), 'not in manifest')
    writeFileSync(join(home, '.codex/claude-home-manifest.json'), JSON.stringify(manifest))
    const result = syncUser({ home, repo })
    assert.ok(!existsSync(join(home, '.agents/skills/config-doctor/SKILL.md')))
    assert.ok(!existsSync(join(home, '.gemini/config/plugins/claude-home/skills/config-doctor/SKILL.md')))
    assert.ok(!existsSync(join(home, '.gemini/config/plugins/claude-home')), 'emptied legacy plugin dir removed')
    assert.equal(readFileSync(join(home, '.agents/skills/edited/SKILL.md'), 'utf8'), 'user modified this')
    assert.equal(readFileSync(join(home, '.agents/skills/unlisted.md'), 'utf8'), 'not in manifest')
    assert.deepEqual(result.kept, ['.agents/skills/edited/SKILL.md'])
    assert.ok(!existsSync(join(home, '.codex/claude-home-manifest.json')))
    const next = JSON.parse(readFileSync(join(home, '.codex/plugharbor-manifest.json'), 'utf8'))
    assert.ok(next.files['.codex/AGENTS.md'])
    assert.ok(readFileSync(join(home, '.codex/AGENTS.md'), 'utf8').includes('plugharbor:generated'))
    assert.deepEqual(syncUser({ home, repo }).changed, [])
  } finally { done(home, repo) }
})

test('migration replaces legacy claude-home hooks when installing support', () => {
  const { home, repo } = fixture()
  try {
    mkdirSync(join(home, '.codex'), { recursive: true })
    writeFileSync(join(home, '.codex/hooks.json'), JSON.stringify({ hooks: {
      SessionStart: [{ hooks: [{ type: 'command', command: "node '/h/.codex/support/claude-home/session-start.mjs'", timeout: 10 }] }],
      Stop: [{ hooks: [{ type: 'command', command: 'foreign-hook' }] }],
    } }))
    installSupport({ home, repo })
    const text = readFileSync(join(home, '.codex/hooks.json'), 'utf8')
    assert.ok(!text.includes('claude-home'))
    assert.ok(text.includes('foreign-hook'))
    assert.ok(text.includes('/plugharbor/session-start.mjs'))
  } finally { done(home, repo) }
})

test('support installation merges hooks, preserves foreign hooks, and is idempotent', () => {
  const { home, repo } = fixture()
  try {
    mkdirSync(join(home, '.codex'), { recursive: true })
    writeFileSync(join(home, '.codex/hooks.json'), JSON.stringify({ hooks: { Stop: [{ hooks: [{ type: 'command', command: 'foreign-hook' }] }] } }))
    installSupport({ home, repo })
    const first = readFileSync(join(home, '.codex/hooks.json'), 'utf8')
    installSupport({ home, repo })
    assert.equal(readFileSync(join(home, '.codex/hooks.json'), 'utf8'), first)
    assert.ok(first.includes('foreign-hook'))
    assert.ok(first.includes('tool-policy.mjs'))
    const stop = JSON.parse(first).hooks.Stop
    assert.equal(stop.length, 2, 'foreign Stop hook kept beside notify.mjs')
    assert.ok(stop[1].hooks[0].command.includes('notify.mjs'))
    const hooks = JSON.parse(readFileSync(join(agy(home), 'hooks.json'), 'utf8'))
    assert.ok(hooks['plugharbor-notify'].Stop[0].command.includes('notify.mjs'))
    assert.ok(existsSync(join(home, '.codex/support/plugharbor/runtime.md')))
    assert.ok(existsSync(join(home, '.codex/claude-coop.config.toml')))
  } finally { done(home, repo) }
})

test('Git guard denies dangerous commands without executing them and permits scoped staging', () => {
  for (const command of ['git add -vA', 'git clean -d --force', 'git push -vf origin main', 'git push origin +main', "bash -lc 'git add .'", 'git add .', 'git -C repo add -A', 'git add --all', 'git push origin main --force', 'git --no-pager tag v1', 'git reset --hard', 'git clean -fd', 'git push origin --delete main']) {
    assert.ok(inspectCommand(command), command)
  }
  for (const command of ['git status --short', 'git add file.md', 'git -C repo push origin feature/x', 'git tag --list', 'git log --oneline', 'printf "git add ."', 'echo git add .', "echo ';' git add .", "printf '%s' ';' git add .", "printf '%s\\n' git add ."]) {
    assert.equal(inspectCommand(command), null, command)
  }
})

test('sync removes deleted owned sources but preserves manual files', () => {
  const { home, repo } = fixture()
  try {
    syncUser({ home, repo })
    rmSync(join(repo, 'plugins/toolkit/agents/reviewer.md'))
    syncUser({ home, repo })
    assert.throws(() => readFileSync(join(home, '.codex/agents/reviewer.toml')), /ENOENT/)
    writeFileSync(join(home, '.codex/AGENTS.md'), '')
    assert.throws(() => syncUser({ home, repo }), /conflict/)
  } finally { done(home, repo) }
})

test('installation detects modified hook matcher instead of silently disabling protection', () => {
  const { home, repo } = fixture()
  try {
    installSupport({ home, repo })
    const path = join(home, '.codex/hooks.json')
    const value = JSON.parse(readFileSync(path, 'utf8'))
    value.hooks.PreToolUse[0].matcher = 'NeverMatch'
    writeFileSync(path, JSON.stringify(value))
    assert.throws(() => installSupport({ home, repo }), /hook conflict/)
  } finally { done(home, repo) }
})

test('installation migrates own hooks whose only difference is the node path', () => {
  const { home, repo } = fixture()
  try {
    installSupport({ home, repo })
    const path = join(home, '.codex/hooks.json')
    const value = JSON.parse(readFileSync(path, 'utf8'))
    const hook = value.hooks.PreToolUse[0].hooks[0]
    const current = hook.command
    hook.command = current.replace(/^('[^']*'|"[^"]*"|\S+)/, "'/opt/homebrew/Cellar/node/0.0.1/bin/node'")
    writeFileSync(path, JSON.stringify(value))
    installSupport({ home, repo })
    assert.equal(JSON.parse(readFileSync(path, 'utf8')).hooks.PreToolUse[0].hooks[0].command, current)
  } finally { done(home, repo) }
})

test('hook command changes warn that Codex trust must be renewed', () => {
  const { home, repo } = fixture()
  const messages = []
  const original = console.error
  console.error = message => messages.push(String(message))
  try {
    installSupport({ home, repo })
    assert.ok(messages.some(m => m.includes('/hooks')), 'new hooks should ask to re-trust')
    messages.length = 0
    installSupport({ home, repo })
    assert.equal(messages.length, 0, 'unchanged hooks should stay quiet')
  } finally { console.error = original; done(home, repo) }
})

test('migration only rewrites a node interpreter prefix, never a foreign wrapper', () => {
  const { home, repo } = fixture()
  try {
    installSupport({ home, repo })
    const path = join(home, '.codex/hooks.json')
    const value = JSON.parse(readFileSync(path, 'utf8'))
    const hook = value.hooks.PreToolUse[0].hooks[0]
    hook.command = hook.command.replace(/^('[^']*'|"[^"]*"|\S+)/, "'/usr/bin/env' bash -c")
    writeFileSync(path, JSON.stringify(value))
    assert.throws(() => installSupport({ home, repo }), /hook conflict/)
  } finally { done(home, repo) }
})

test('installation preserves runtime hook trust appended to the cooperation profile', () => {
  const { home, repo } = fixture()
  try {
    installSupport({ home, repo })
    const path = join(home, '.codex/claude-coop.config.toml')
    const body = readFileSync(path, 'utf8') + '\n[hooks.state]\ntrusted = "fixture"\n'
    writeFileSync(path, body)
    installSupport({ home, repo })
    assert.equal(readFileSync(path, 'utf8'), body)
  } finally { done(home, repo) }
})

const scopedSamples = [
  ['block.md', 'paths:\n  # not a pattern\n  - "**/*.cs" # code\n  - \'**/*.csproj\'', '**/*.cs,**/*.csproj'],
  ['inline.md', 'paths: ["**/*.md", \'**/*.mdx\'] # docs', '**/*.md,**/*.mdx'],
  ['crlf.md', 'paths:\n  - "**/*.py"\n# unrelated comment', '**/*.py'],
  ['indentless.md', 'paths: # selector\n- "**/*.vue"\n- "**/stores/**/*.ts"', '**/*.vue,**/stores/**/*.ts'],
  ['plain.md', 'paths: [src/**/*.js, tests/*.mjs]', 'src/**/*.js,tests/*.mjs'],
]

test('agy translates scoped rules to glob triggers and keeps global safety rules always on', () => {
  const { home, repo, rules } = fixture()
  try {
    for (const [name, meta] of scopedSamples) {
      const raw = `---\n${meta}\n---\nRule body.\n`
      writeFileSync(join(rules, name), name === 'crlf.md' ? raw.replace(/\n/g, '\r\n') : raw)
    }
    writeFileSync(join(rules, 'git-safety.md'), 'Global safety.\n')
    syncUser({ home, repo })
    for (const [name, , globs] of scopedSamples) {
      const out = readFileSync(join(agy(home), 'rules', name), 'utf8')
      assert.ok(out.includes('trigger: glob\n'), out)
      assert.ok(out.includes(`globs: ${JSON.stringify(globs)}\n`), out)
      assert.ok(!/^paths:/m.test(out), out)
      assert.ok(!out.includes('not a pattern'), out)
      assert.ok(out.endsWith('Rule body.\n'), out)
    }
    assert.equal(readFileSync(join(agy(home), 'rules/git-safety.md'), 'utf8'), '---\ntrigger: always_on\n---\nGlobal safety.\n')
    const codex = readFileSync(join(home, '.codex/AGENTS.md'), 'utf8')
    assert.ok(codex.includes('- "**/*.cs" # code'))
    assert.ok(codex.includes('Global safety.'))
    const pi = readFileSync(join(home, '.pi/agent/APPEND_SYSTEM.md'), 'utf8')
    assert.ok(!pi.includes('Global safety.'))
    assert.ok(!pi.includes('- "**/*.cs" # code'))
  } finally { done(home, repo) }
})

test('parses CRLF rule frontmatter', () => {
  const lf = fixture(), crlf = fixture()
  try {
    for (const [name, meta] of scopedSamples) {
      const raw = `---\n${meta}\n---\nRule body.\n`
      writeFileSync(join(lf.rules, name), raw)
      writeFileSync(join(crlf.rules, name), raw.replace(/\n/g, '\r\n'))
    }
    writeFileSync(join(lf.rules, 'plain-global.md'), '---\ndescription: x\n---\nBody.\n')
    writeFileSync(join(crlf.rules, 'plain-global.md'), '---\r\ndescription: x\r\n---\r\nBody.\r\n')
    syncUser({ home: lf.home, repo: lf.repo })
    syncUser({ home: crlf.home, repo: crlf.repo })
    for (const name of [...scopedSamples.map(s => s[0]), 'plain-global.md']) {
      const a = readFileSync(join(agy(lf.home), 'rules', name), 'utf8')
      const b = readFileSync(join(agy(crlf.home), 'rules', name), 'utf8')
      assert.equal(b, a, name)
      assert.ok(!b.includes('\r'), name)
    }
    assert.ok(readFileSync(join(agy(crlf.home), 'rules/plain-global.md'), 'utf8').includes('trigger: always_on'))
  } finally { done(lf.home, lf.repo, crlf.home, crlf.repo) }
})

test('invalid scoped rule selectors fail closed without emitting an always-on rule', () => {
  for (const paths of ['paths: []', 'paths: "**/*.cs"', 'paths:\n  - {bad: value}', 'paths: ["**/*.cs",', 'paths:\n  - "**/*.cs"\npaths: ["**/*.py"]', 'paths:\n  - ""', 'paths:\n  - "**/*,*.cs"', '"paths": ["**/*.cs"]', '  paths: ["**/*.cs"]', 'paths: ["**/*.cs"]\ntrigger: always_on', 'paths: ["**/*.cs"]\nglobs: "**/*"', 'paths: [*alias]', 'paths: [true]', 'paths: [123]', '"\\u0070aths": ["**/*.cs"]', '? paths\n: ["**/*.cs"]']) {
    const { home, repo, rules } = fixture()
    try {
      writeFileSync(join(rules, 'scoped.md'), `---\n${paths}\n---\nScoped.\n`)
      assert.throws(() => syncUser({ home, repo }), /paths|glob/)
      assert.throws(() => readFileSync(join(agy(home), 'rules/scoped.md')), /ENOENT/)
    } finally { done(home, repo) }
  }
})
