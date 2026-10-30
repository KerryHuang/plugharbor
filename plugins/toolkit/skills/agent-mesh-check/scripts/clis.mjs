// 四個 agent CLI 的共用核心：找執行檔、組無互動指令、清巢狀環境變數、帶逾時執行、判定結果。
// agent-dispatch 以相對路徑 import 這支；參數的實測依據見 ../references/cli-notes.md。
import { spawn } from 'node:child_process'
import { accessSync, statSync, constants } from 'node:fs'
import { join, delimiter } from 'node:path'

export const CLIS = ['claude', 'codex', 'agy', 'pi']

const pathOf = env => env.PATH ?? env.Path ?? ''

export function resolveBin(name, env = process.env, platform = process.platform) {
  const names = platform === 'win32' ? [`${name}.exe`, `${name}.cmd`, name] : [name]
  for (const dir of pathOf(env).split(platform === 'win32' ? ';' : delimiter).filter(Boolean)) {
    for (const n of names) {
      const p = join(dir, n)
      try {
        if (!statSync(p).isFile()) continue
        if (platform !== 'win32') accessSync(p, constants.X_OK)
        return p
      } catch { /* 下一個 */ }
    }
  }
  return null
}

// probe：唯讀只回字串；driver：自動核准，只用在驗證第 3 層的 A；ask：派工短問答，唯讀但保留使用者設定。
export function buildArgs(name, mode, prompt) {
  switch (name) {
    case 'claude':
      return mode === 'driver' ? ['-p', prompt, '--allowedTools', 'Bash'] : ['-p', prompt, '--tools', '']
    case 'codex': {
      const lean = mode === 'ask' ? [] : ['--ignore-user-config', '--ignore-rules']
      return ['exec', ...lean, '--ephemeral', '--skip-git-repo-check', '-s', mode === 'driver' ? 'danger-full-access' : 'read-only', prompt]
    }
    case 'agy':
      // agy 沒有真正的唯讀：--mode plan 在 -p 只產計畫不回答，--sandbox 只限 shell、不限它的寫檔工具。
      return mode === 'driver' ? ['-p', prompt, '--dangerously-skip-permissions'] : ['-p', prompt, '--sandbox', '--disable-slash-commands']
    case 'pi':
      return mode === 'driver' ? ['-p', prompt, '--tools', 'bash', '--no-session'] : ['-p', prompt, '--no-tools', '--no-session']
    default:
      throw new Error(`未知的 CLI：${name}`)
  }
}

// 從某個 CLI 裡再叫 CLI 時，留著外層的標記會被當成巢狀 session 擋下或誤判。
export function scrubEnv(env) {
  const out = {}
  for (const [k, v] of Object.entries(env)) {
    if (k === 'CLAUDECODE' || k.startsWith('CLAUDE_CODE_') || k === 'HERDR_PANE_ID') continue
    if (k.startsWith('CODEX_') && k !== 'CODEX_HOME') continue
    if (k.startsWith('PI_') || k.startsWith('AGY_') || k.startsWith('ANTIGRAVITY_')) continue
    out[k] = v
  }
  return out
}

const cmdQuote = a => `"${String(a).replace(/"/g, '""')}"`

export function run(bin, args, { cwd, timeoutMs = 180_000, env = process.env } = {}) {
  return new Promise(done => {
    const t0 = Date.now()
    const viaCmd = /\.cmd$/i.test(bin)
    const child = viaCmd
      ? spawn([bin, ...args].map(cmdQuote).join(' '), { cwd, env, shell: true, windowsHide: true })
      : spawn(bin, args, { cwd, env, windowsHide: true })
    const chunks = []
    let timedOut = false
    const timer = setTimeout(() => { timedOut = true; child.kill('SIGKILL') }, timeoutMs)
    child.stdout.on('data', c => chunks.push(c))
    child.stderr.on('data', c => chunks.push(c))
    child.stdin.on('error', () => {})
    child.stdin.end('')
    const finish = code => { clearTimeout(timer); done({ code, out: Buffer.concat(chunks).toString('utf8'), ms: Date.now() - t0, timedOut }) }
    child.on('error', e => { chunks.push(Buffer.from(String(e.message))); finish(null) })
    child.on('close', finish)
  })
}

const AUTH = /\b(log ?in|logged out|not authenticated|authenticat\w*|401|unauthori[sz]ed|credits?|quota|rate.?limit)\b/i

export function classify(r, expect) {
  if (r.timedOut) return 'timeout'
  if (r.out.includes(expect)) return 'pass'
  if (AUTH.test(r.out)) return 'auth'
  return 'fail'
}

export async function version(name, bin) {
  const r = await run(bin, ['--version'], { timeoutMs: 20_000, env: scrubEnv(process.env) })
  return r.code === 0 ? r.out.trim().split(/\r?\n/)[0] : null
}
