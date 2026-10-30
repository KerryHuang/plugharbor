#!/usr/bin/env node
// plugharbor 的 setup/home 與 reviewer agents 是來源；各 CLI 的副本由 manifest 管理，不覆蓋使用者的其他檔案。
import { existsSync, readFileSync, writeFileSync, mkdirSync, readdirSync, unlinkSync, rmdirSync } from 'node:fs'
import { join, dirname, relative, basename, resolve } from 'node:path'
import { homedir } from 'node:os'
import { createHash } from 'node:crypto'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

const here = dirname(fileURLToPath(import.meta.url))
const digest = body => createHash('sha256').update(body).digest('hex')
const read = path => existsSync(path) ? readFileSync(path, 'utf8') : ''
const split = raw => {
  const text = raw.replace(/\r\n/g, '\n')
  const end = text.startsWith('---\n') ? text.indexOf('\n---\n', 4) : -1
  if (end < 0) throw new Error('缺少有效 frontmatter')
  return { header: text.slice(0, end + 5), body: text.slice(end + 5), meta: text.slice(4, end) }
}
const field = (meta, name) => meta.match(new RegExp(`^${name}:\\s*(.+)$`, 'm'))?.[1].trim()
const walk = path => existsSync(path) ? readdirSync(path, { withFileTypes: true }).flatMap(e => {
  if (e.name === '__pycache__' || e.name.endsWith('.pyc')) return []
  const p = join(path, e.name)
  return e.isDirectory() ? walk(p) : e.isFile() ? [p] : []
}) : []

// 只接受 paths 的字串陣列子集；不把未解析的 YAML 當成全域規則。
function agyRuleMeta(meta) {
  const lines = meta.split('\n')
  const fail = () => { throw new Error('無法安全轉換 rule paths 成 agy globs；請使用非空字串陣列') }
  // 有限子集只接受 plain mapping key；跳脫、explicit 或 flow key 不可落入全域分支。
  if (lines.some(line => line.trim() && !/^\s*#/.test(line) && (
    /^\s*(?:["']|\?(?:\s|$)|:(?:\s|$))/.test(line) ||
    !/^(?:\s|-[ \t]+|[A-Za-z_][\w-]*[ \t]*:)/.test(line)
  ))) fail()
  // 拒絕無法辨識的 key 寫法與來源中的 agy trigger，避免重複 key 改變範圍。
  if (lines.some(line => /^\s*["']?(?:trigger|globs)["']?\s*:/.test(line))) fail()
  const starts = lines.flatMap((line, i) => /^\s*["']?paths["']?\s*:/.test(line) ? [i] : [])
  if (!starts.length) return meta.trim() + (meta.trim() ? '\n' : '') + 'trigger: always_on'
  if (starts.length !== 1) fail()
  const at = starts[0]
  if (!/^paths\s*:/.test(lines[at])) fail()
  let end = at + 1
  while (end < lines.length && (!lines[end].trim() || /^\s|^#|^-\s/.test(lines[end]))) end++
  const scalar = value => {
    const text = value.trim()
    let parsed
    if (text.startsWith('"')) {
      const match = text.match(/^("(?:[^"\\]|\\.)*")(?:\s+#.*)?$/)
      if (!match) fail()
      try { parsed = JSON.parse(match[1]) } catch { fail() }
    } else if (text.startsWith("'")) {
      const match = text.match(/^'((?:[^']|'')*)'(?:\s+#.*)?$/)
      if (!match) fail()
      parsed = match[1].replace(/''/g, "'")
    } else {
      parsed = text.replace(/\s+#.*$/, '')
      if (!/^[\w./*?!{}-]+$/.test(parsed)) fail()
      if (/^[*!{]|^(?:null|true|false|[-+]?\d[\d.eE+-]*)$/i.test(parsed)) fail()
    }
    if (!parsed || /[,\r\n]/.test(parsed)) fail()
    return parsed
  }
  const value = lines[at].replace(/^paths\s*:/, '').trim()
  let patterns
  if (value && !value.startsWith('#')) {
    const match = value.match(/^\[(.*)\](?:\s+#.*)?$/)
    if (!match || lines.slice(at + 1, end).some(line => line.trim() && !/^\s*#/.test(line))) fail()
    const items = match[1].match(/"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^,]+/g) ?? []
    if (items.join(',') !== match[1] || !items.length) fail()
    patterns = items.map(scalar)
  } else {
    patterns = lines.slice(at + 1, end).filter(line => line.trim() && !/^\s*#/.test(line)).map(line => {
      const match = line.match(/^\s*-\s+(.+)$/)
      if (!match) fail()
      return scalar(match[1])
    })
  }
  if (!patterns.length) fail()
  const remaining = [...lines.slice(0, at), ...lines.slice(end)].join('\n').trim()
  return (remaining ? remaining + '\n' : '') + `trigger: glob\nglobs: ${JSON.stringify(patterns.join(','))}`
}

const MANIFEST = '.codex/plugharbor-manifest.json'
const LEGACY_MANIFEST = '.codex/claude-home-manifest.json'
const AGY = '.gemini/config/plugins/plugharbor-home'
const SUPPORT = '.codex/support/plugharbor'

function ownership(home) {
  const path = join(home, MANIFEST)
  const state = read(path) ? JSON.parse(read(path)) : { files: {}, mcpNames: [] }
  const changed = []
  const kept = []
  const desired = new Set()
  // 舊 claude-home 的副本：只動舊 manifest 列出且 hash 仍相符的檔案，其餘保留並回報。
  const legacyPath = join(home, LEGACY_MANIFEST)
  if (existsSync(legacyPath)) {
    const legacy = JSON.parse(read(legacyPath))
    for (const [rel, hash] of Object.entries(legacy.files ?? {})) {
      const target = join(home, rel)
      if (!existsSync(target)) continue
      if (digest(readFileSync(target)) !== hash) { kept.push(rel); continue }
      unlinkSync(target)
      changed.push(rel)
      for (let dir = dirname(target); dir !== home && dir.startsWith(home); dir = dirname(dir)) {
        try { rmdirSync(dir) } catch { break }
      }
    }
    unlinkSync(legacyPath)
    if (!state.mcpNames?.length && legacy.mcpNames?.length) state.mcpNames = legacy.mcpNames
  }
  return {
    state, changed, kept,
    put(to, body) {
      const rel = relative(home, to)
      desired.add(rel)
      const current = existsSync(to) ? readFileSync(to) : null
      const expected = Buffer.from(body)
      if (current?.equals(expected)) { state.files[rel] = digest(expected); return }
      if (current !== null && state.files[rel] !== digest(current)) throw new Error(`conflict：${rel} 已有未受管理內容或手動修改，未覆寫`)
      mkdirSync(dirname(to), { recursive: true })
      writeFileSync(to, expected)
      state.files[rel] = digest(expected)
      changed.push(rel)
      mkdirSync(dirname(path), { recursive: true })
      writeFileSync(path, JSON.stringify(state, null, 2) + '\n')
    },
    prune() {
      for (const [rel, hash] of Object.entries(state.files)) {
        if (!rel.startsWith(`${AGY}/rules/`) && !rel.startsWith('.codex/agents/')) continue
        if (desired.has(rel)) continue
        const target = join(home, rel)
        if (existsSync(target)) {
          if (digest(readFileSync(target)) !== hash) throw new Error(`conflict：${rel} 已手動修改，未刪除`)
          unlinkSync(target)
          changed.push(rel)
        }
        delete state.files[rel]
      }
    },
    save() {
      mkdirSync(dirname(path), { recursive: true })
      writeFileSync(path, JSON.stringify(state, null, 2) + '\n')
    },
  }
}

// 來源：repo/setup/home（CLAUDE.md、shared、rules）與 repo/plugins/toolkit/agents。
// skill 由各 CLI 的 plugin 機制提供，這裡不鏡像。
export function syncUser({ home = homedir(), repo = resolve(here, '../..'), mcpNames } = {}) {
  const owned = ownership(home)
  if (mcpNames) owned.state.mcpNames = mcpNames
  const runtime = join(home, SUPPORT, 'runtime.md')
  const src = join(repo, 'setup/home')
  const reviewerPrefix = `你正在 Codex 執行唯讀審查。先讀 ${runtime} 的 reviewer 適配。若下文說 rules 已載入且禁止重讀，但實際只有索引，必須讀取相關來源再下結論。受審檔若是 Codex，使用 Codex schema，不用 Claude frontmatter／模型值判錯。缺乏證據時標未驗證。不得改檔、執行受審 hook、派工或呼叫 MCP。\n\n`
  for (const p of walk(join(repo, 'plugins/toolkit/agents')).filter(p => p.endsWith('.md'))) {
    const { meta, body } = split(read(p))
    const name = field(meta, 'name'), description = field(meta, 'description')
    if (!name || !description) throw new Error(`agent 缺 name/description：${p}`)
    const toml = [
      `name = ${JSON.stringify(name)}`, `description = ${JSON.stringify(description)}`,
      'sandbox_mode = "read-only"',
      `developer_instructions = ${JSON.stringify(reviewerPrefix + body.trim())}`,
      // agent TOML 先驗 transport 才合併 parent；disabled server 仍須提供合法 transport。
      ...(owned.state.mcpNames ?? []).map(n => `\n[mcp_servers.${JSON.stringify(n)}]\ncommand = "disabled-by-reviewer-policy"\nenabled = false`), '',
    ].join('\n')
    owned.put(join(home, '.codex/agents', `${name}.toml`), toml)
  }
  let root = read(join(src, 'CLAUDE.md')).replace(/\r\n/g, '\n')
  root = root.replace(/^@(\S+\.md)\s*$/gm, (_, path) => {
    const value = read(join(src, path)).replace(/\r\n/g, '\n')
    if (!value) throw new Error(`找不到 user root 匯入：${path}`)
    return value.trim()
  })
  const rules = []
  const scoped = []
  for (const p of walk(join(src, 'rules')).filter(p => p.endsWith('.md'))) {
    const text = read(p).replace(/\r\n/g, '\n')
    const label = `~/.claude/rules/${basename(p)}`
    if (text.startsWith('---\n')) {
      const { meta, body: textBody } = split(text)
      owned.put(join(home, AGY, 'rules', basename(p)), '---\n' + agyRuleMeta(meta).trim() + '\n---\n' + textBody)
      if (/^paths:/m.test(meta)) { scoped.push(`- ${label}\n${meta}`); continue }
      rules.push(`\n## ${label}\n\n${textBody}`)
    } else {
      owned.put(join(home, AGY, 'rules', basename(p)), '---\ntrigger: always_on\n---\n' + text)
      rules.push(`\n## ${label}\n\n${text}`)
    }
  }
  owned.put(join(home, '.codex/AGENTS.md'), `<!-- plugharbor:generated -->\n${root}\n${rules.join('\n')}\n## 條件式規則：工作前按 paths 讀取原檔\n\n${scoped.join('\n')}\n\n## 雙工具適配\n\n涉及 reviewer 或跨工具交接時，先讀 ${runtime}。\n`)
  // pi 不讀 ~/.claude/CLAUDE.md，經 APPEND_SYSTEM.md 附加；~/.claude/rules 由 pi-code claude-rules.ts 載入，不在這裡重複。
  owned.put(join(home, '.pi/agent/APPEND_SYSTEM.md'), `<!-- plugharbor:generated -->\n${root}\n`)
  // agy 不讀 ~/.claude/CLAUDE.md，user root 改以 always_on rule 進 plugharbor-home plugin。
  owned.put(join(home, AGY, 'rules/plugharbor-root.md'), `---\ntrigger: always_on\n---\n${root}\n`)
  owned.put(join(home, AGY, 'plugin.json'), JSON.stringify({
    name: 'plugharbor-home',
    description: 'User-level rules generated from plugharbor',
    version: '1.0.0',
  }, null, 2))
  owned.prune()
  owned.save()
  return { changed: owned.changed, kept: owned.kept }
}

// Homebrew 的 Cellar 路徑含版本號，brew upgrade 後失效；有穩定 symlink 就用它。
function nodeBin() {
  const stable = '/opt/homebrew/bin/node'
  return process.platform === 'darwin' && existsSync(stable) ? stable : process.execPath
}

export function installSupport({ home = homedir(), repo = resolve(here, '../..') } = {}) {
  const owned = ownership(home)
  const dest = join(home, SUPPORT)
  for (const name of ['sync-user.mjs', 'session-start.mjs', 'tool-policy.mjs', 'notify.mjs', 'runtime.md']) owned.put(join(dest, name), readFileSync(join(here, name)))
  // session-start 從這裡找回來源 repo。
  owned.put(join(dest, 'repo'), resolve(repo))
  // Codex /hooks 會在目前 profile 追加信任狀態；保留 runtime 的狀態區塊。
  const profile = join(home, '.codex/claude-coop.config.toml')
  const base = readFileSync(join(here, 'claude-coop.config.toml'), 'utf8')
  const currentProfile = read(profile)
  const stateAt = currentProfile.indexOf('\n[hooks.state]')
  if (stateAt >= 0 && currentProfile.slice(0, stateAt).trimEnd() === base.trimEnd()) {
    owned.state.files[relative(home, profile)] = digest(currentProfile)
    owned.put(profile, currentProfile)
  } else owned.put(profile, base)
  const hookPath = join(home, '.codex/hooks.json')
  const hooks = read(hookPath) ? JSON.parse(read(hookPath)) : { hooks: {} }
  const quote = value => process.platform === 'win32' ? `"${value}"` : `'${value.replace(/'/g, "'\\''")}'`
  const retrust = []
  for (const [event, script, matcher] of [['SessionStart', 'session-start.mjs', undefined], ['PreToolUse', 'tool-policy.mjs', '^Bash$'], ['Stop', 'notify.mjs', undefined]]) {
    // Windows 的 Codex 用 PowerShell 跑 hook：開頭是帶引號的路徑會被當成字串而解析失敗，改用 PATH 上的裸 node。
    const command = `${process.platform === 'win32' ? 'node' : quote(nodeBin())} ${quote(join(dest, script))}`
    const groups = hooks.hooks ??= {}
    const entries = groups[event] ??= []
    // 舊 claude-home 的 entry 已隨舊副本移除，指令不再有效，一併拿掉。
    const legacy = g => g.hooks?.length && g.hooks.every(h => h.command?.includes(`/claude-home/${script}`) || h.command?.includes(`\\claude-home\\${script}`))
    if (entries.some(legacy)) { entries.splice(0, entries.length, ...entries.filter(g => !legacy(g))); retrust.push(event) }
    const mine = entries.filter(g => g.hooks?.some(h => h.command?.includes(`/plugharbor/${script}`) || h.command?.includes(`\\plugharbor\\${script}`)))
    // 只有 node 路徑不同（舊版寫入 process.execPath）視為自己的 entry，原地更新；其他前綴屬手動改動，照常報衝突。
    const scriptArg = ` ${quote(join(dest, script))}`
    const old = mine.length === 1 && mine[0].hooks.length === 1 ? mine[0].hooks[0].command : undefined
    const prefix = old?.endsWith(scriptArg) ? old.slice(0, -scriptArg.length).replace(/^['"]|['"]$/g, '') : undefined
    if (old !== command && prefix && /(^|[\\/])node(\.exe)?$/i.test(prefix)) { mine[0].hooks[0].command = command; retrust.push(event) }
    if (mine.length === 0) { entries.push({ ...(matcher ? { matcher } : {}), hooks: [{ type: 'command', command, timeout: 10 }] }); retrust.push(event) }
    else if (mine.length !== 1 || mine[0].hooks.length !== 1 || mine[0].hooks[0].command !== command || mine[0].matcher !== matcher || mine[0].hooks[0].type !== 'command' || mine[0].hooks[0].timeout !== 10) throw new Error(`hook conflict：${event}，保留手動設定`)
  }
  // hooks.json 包含別人的設定，僅合併自己的 entries；不接管整份檔案。
  mkdirSync(dirname(hookPath), { recursive: true })
  writeFileSync(hookPath, JSON.stringify(hooks, null, 2) + '\n')
  // agy 讀已啟用 plugin 根目錄的 hooks.json（頂層鍵是 hook 名稱；Stop 是扁平的 handler 清單，不包 matcher）。
  const notify = `${process.platform === 'win32' ? 'node' : quote(nodeBin())} ${quote(join(dest, 'notify.mjs'))}`
  owned.put(join(home, AGY, 'hooks.json'), JSON.stringify({
    'plugharbor-notify': { Stop: [{ type: 'command', command: notify, timeout: 10 }] }
  }, null, 2) + '\n')
  owned.save()
  // Codex 以內容雜湊記錄 hook 信任；指令一變就失效，不提示的話 Git guard 會靜默不跑。
  if (retrust.length) console.error(`Codex hook 已${[...new Set(retrust)].join('、')}新增或更新：請在 Codex 執行 /hooks 重新信任，否則該 hook 不會執行。`)
  return { changed: owned.changed, kept: owned.kept }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const args = process.argv.slice(2)
    const install = args.includes('--install')
    const at = args.indexOf('--repo')
    const repo = at >= 0 ? resolve(args[at + 1] ?? '') : resolve(here, '../..')
    let mcpNames
    if (install) {
      installSupport({ repo })
      // codex 未安裝或失敗時沿用 manifest 內記錄的清單。
      try { mcpNames = JSON.parse(execFileSync('codex', ['mcp', 'list', '--json'], { encoding: 'utf8' })).map(x => x.name) } catch {}
    }
    const { changed, kept } = syncUser({ repo, mcpNames })
    if (!args.includes('--quiet')) console.log(`user 副本已同步：${changed.length} 個檔案。`)
    if (kept.length) console.error(`舊 claude-home 副本已被修改，保留未刪：\n${kept.map(k => '  ' + k).join('\n')}`)
  } catch (error) { console.error(error.message); process.exitCode = 1 }
}
