#!/usr/bin/env node
// 驗證本機 agent CLI：① 有沒有裝 ② 自己能不能回話 ③ 互相能不能叫。用法見 usage。
import { mkdtempSync, rmSync, mkdirSync, readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { tmpdir, homedir, hostname } from 'node:os'
import { randomBytes } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { CLIS, resolveBin, buildArgs, scrubEnv, run, classify, version } from './clis.mjs'

const usage = `用法：node mesh.mjs [--from <${CLIS.join('|')}>] [--full] [--timeout <秒，預設 180>] [--concurrency <預設 4>] [--json]
  --from   目前入口（執行本 skill 的 CLI）；省略時從環境變數判斷，判斷不出來就要求指定
  --full   第 3 層驗全部兩兩組合，而不是只驗入口 ↔ 其他
exit：全部通過或略過 0；有失敗、逾時、未登入 1；用法錯誤 2`

export function pairs(installed, from, full) {
  if (full) return installed.flatMap(a => installed.filter(b => b !== a).map(b => [a, b]))
  if (!installed.includes(from)) return []
  return installed.filter(x => x !== from).flatMap(x => [[from, x], [x, from]])
}

// 各 CLI 給子程序設的標記（2026-10-23 實測）。巢狀時可能同時存在多個，那時才看 --from。
const MARKERS = { claude: ['CLAUDECODE'], codex: ['CODEX_THREAD_ID', 'CODEX_CI'], agy: ['ANTIGRAVITY_AGENT'], pi: ['PI_CODING_AGENT'] }
const detectAll = env => CLIS.filter(c => MARKERS[c].some(k => env[k]))

// agent 自報的 --from 可能錯（pi 用 Claude 模型時會說自己是 claude），只有一個標記時以標記為準。
export function resolveFrom(given, env) {
  const found = detectAll(env)
  if (found.length === 1) return { from: found[0], note: given && given !== found[0] ? `--from ${given} 與環境標記不符，改用 ${found[0]}` : '' }
  if (given) return { from: given, note: found.length > 1 && !found.includes(given) ? `環境同時有 ${found.join('、')} 的標記，依 --from 用 ${given}` : '' }
  return { from: null, note: found.length > 1 ? `環境同時有 ${found.join('、')} 的標記，請用 --from 指定` : '' }
}

export function statePath(env, platform = process.platform) {
  if (env.XDG_STATE_HOME) return join(env.XDG_STATE_HOME, 'agent-mesh', 'last.json')
  if (platform === 'win32') return join(env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local'), 'agent-mesh', 'last.json')
  return join(homedir(), '.local', 'state', 'agent-mesh', 'last.json')
}

// Windows 上 CLI 的背景子程序可能鎖住暫存目錄十幾秒，當次刪不掉；下次執行時清掉超過一小時的殘留。
export function sweepStale(dir = tmpdir(), now = Date.now()) {
  for (const name of readdirSync(dir)) {
    if (!name.startsWith('agent-mesh-')) continue
    const p = join(dir, name)
    try { if (now - statSync(p).mtimeMs > 3_600_000) rmSync(p, { recursive: true, force: true }) } catch { /* 仍被鎖住就留給下次 */ }
  }
}

export function diffVersions(prev, now) {
  if (!prev) return []
  return Object.keys(now).filter(c => prev[c] && now[c] && prev[c] !== now[c]).map(c => ({ cli: c, from: prev[c], to: now[c] }))
}

// 預期字串只出現在回覆裡、不出現在 prompt 裡：codex 會把 prompt 原文印進輸出，照抄型 prompt 會假通過。
const challenge = () => { const n = randomBytes(4).toString('hex'); return { prompt: `Reply with only this text converted to uppercase, nothing else: ping-${n}`, expect: `PING-${n.toUpperCase()}` } }

// A 只需執行 `node <檔名>`：各 CLI 的 shell 不同（Windows 的 codex 用 PowerShell），把 B 的完整指令交給 A 就得處理各家引號。
export const callerScript = (bin, b, prompt, timeoutMs) => `import { run, buildArgs, scrubEnv } from ${JSON.stringify(new URL('./clis.mjs', import.meta.url).href)}
const r = await run(${JSON.stringify(bin)}, buildArgs(${JSON.stringify(b)}, 'probe', ${JSON.stringify(prompt)}), { env: scrubEnv(process.env), timeoutMs: ${timeoutMs} })
process.stdout.write(r.out)
`

const tail = s => s.trim().split(/\r?\n/).slice(-4).join(' ⏎ ').slice(0, 300)

async function pool(jobs, limit, perCli) {
  const busy = Object.fromEntries(CLIS.map(c => [c, 0]))
  const results = new Array(jobs.length)
  let active = 0
  return new Promise(resolve => {
    const pending = new Set(jobs.map((_, i) => i))
    const tick = () => {
      if (!pending.size && !active) return resolve(results)
      for (const i of [...pending]) {
        if (active >= limit) break
        const uses = jobs[i].uses
        if (uses.some(c => busy[c] >= perCli)) continue
        pending.delete(i); active++; uses.forEach(c => busy[c]++)
        jobs[i].fn().then(r => { results[i] = r; active--; uses.forEach(c => busy[c]--); tick() })
      }
    }
    tick()
  })
}

async function main(argv) {
  const opt = { full: false, timeout: 180, concurrency: 4, json: false, from: null }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--help' || a === '-h') { console.log(usage); return 0 }
    else if (a === '--full') opt.full = true
    else if (a === '--json') opt.json = true
    else if (a === '--from') opt.from = argv[++i]
    else if (a === '--timeout') opt.timeout = Number(argv[++i])
    else if (a === '--concurrency') opt.concurrency = Number(argv[++i])
    else { console.error(`不認得的參數：${a}\n${usage}`); return 2 }
  }
  if (opt.from && !CLIS.includes(opt.from)) { console.error(`--from 必須是 ${CLIS.join('／')}`); return 2 }
  const who = resolveFrom(opt.from, process.env)
  opt.from = who.from
  if (who.note) console.error(`[入口] ${who.note}`)
  if (!opt.full && !opt.from) { console.error(`判斷不出目前入口，請加 --from <cli>（或用 --full）\n${usage}`); return 2 }

  const env = scrubEnv(process.env)
  const timeoutMs = opt.timeout * 1000
  const rows = []
  const versions = {}
  const bins = {}
  // ① 安裝
  for (const c of CLIS) {
    bins[c] = resolveBin(c)
    versions[c] = bins[c] ? await version(c, bins[c]) : null
    rows.push({ layer: 1, a: c, b: '', status: bins[c] ? 'pass' : 'skip', ms: 0, note: bins[c] ? (versions[c] ?? '版本讀不到') : '未安裝' })
  }
  const installed = CLIS.filter(c => bins[c])
  if (opt.from && !installed.includes(opt.from)) { console.error(`入口 ${opt.from} 不在 PATH 上`); return 2 }

  sweepStale()
  const sandbox = mkdtempSync(join(tmpdir(), 'agent-mesh-'))
  try {
    // ② 自己能不能回話
    const self = await pool(installed.map(c => ({ uses: [c], fn: async () => {
      const ch = challenge()
      const r = await run(bins[c], buildArgs(c, 'probe', ch.prompt), { cwd: sandbox, timeoutMs, env })
      const status = classify(r, ch.expect)
      return { layer: 2, a: c, b: '', status, ms: r.ms, note: status === 'pass' ? '' : tail(r.out) }
    } })), opt.concurrency, 2)
    rows.push(...self)
    const ok = new Set(self.filter(r => r.status === 'pass').map(r => r.a))
    // ③ A 用 shell 叫 B
    const mesh = pairs(installed, opt.from, opt.full)
    const jobs = mesh.map(([a, b]) => ({ uses: [a, b], fn: async () => {
      if (!ok.has(a) || !ok.has(b)) return { layer: 3, a, b, status: 'skip', ms: 0, note: '第 2 層未通過' }
      const ch = challenge()
      const script = `call-${a}-${b}.mjs`
      writeFileSync(join(sandbox, script), callerScript(bins[b], b, ch.prompt, timeoutMs))
      const driver = `Run this exact shell command once in the current directory and wait for it to finish (it takes up to a minute): node ${script}\nThen reply with its final output line verbatim and nothing else. Do not run anything else.`
      const r = await run(bins[a], buildArgs(a, 'driver', driver), { cwd: sandbox, timeoutMs: timeoutMs * 2, env })
      const status = classify(r, ch.expect)
      return { layer: 3, a, b, status, ms: r.ms, note: status === 'pass' ? '' : tail(r.out) }
    } }))
    rows.push(...await pool(jobs, opt.concurrency, 2))
  } finally {
    // Windows 上子程序剛結束時 cwd 的 handle 可能還沒釋放（EBUSY）；清不掉只警告，不能讓結果跟著丟。
    try { rmSync(sandbox, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 }) }
    catch (e) { console.error(`[清理] 暫存目錄沒刪掉，可手動刪：${sandbox}（${e.code ?? e.message}）`) }
  }

  const file = statePath(process.env)
  let prev = null
  try { prev = JSON.parse(readFileSync(file, 'utf8')).versions } catch { /* 第一次跑 */ }
  const changed = diffVersions(prev, versions)
  const record = { time: new Date().toISOString(), host: hostname(), platform: process.platform, from: opt.from, full: opt.full, versions, results: rows }
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, JSON.stringify(record, null, 2) + '\n')

  if (opt.json) console.log(JSON.stringify({ ...record, changed, file }, null, 2))
  else {
    const mark = { pass: '✅ 通過', skip: '⏭ 略過', fail: '❌ 失敗', timeout: '⏱ 逾時', auth: '🔑 未登入／額度' }
    const label = r => r.layer === 1 ? `① 安裝 ${r.a}` : r.layer === 2 ? `② 自己回話 ${r.a}` : `③ ${r.a} → ${r.b}`
    console.log(`入口：${opt.from ?? '（--full）'}　模式：${opt.full ? '全部兩兩' : '入口為中心'}`)
    for (const r of rows) console.log(`${label(r).padEnd(22)} ${mark[r.status].padEnd(10)} ${r.ms ? `${(r.ms / 1000).toFixed(1)}s` : ''} ${r.note}`)
    for (const c of changed) console.log(`⚠ ${c.cli} 版本和上次不同：${c.from} → ${c.to}`)
    console.log(`結果檔：${file}`)
  }
  return rows.every(r => r.status === 'pass' || r.status === 'skip') ? 0 : 1
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main(process.argv.slice(2)).then(code => { process.exitCode = code })
