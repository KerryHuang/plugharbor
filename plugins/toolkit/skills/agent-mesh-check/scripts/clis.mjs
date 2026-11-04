// 四個 agent CLI 的共用核心：找執行檔、組無互動指令、清巢狀環境變數、帶逾時執行、判定結果。
// agent-dispatch 以相對路徑 import 這支；參數的實測依據見 ../references/cli-notes.md。
import { spawn } from 'node:child_process'
import { accessSync, statSync, readFileSync, existsSync, constants } from 'node:fs'
import { join, dirname, delimiter } from 'node:path'

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

// probe：唯讀只回字串；driver：自動核准，只用在驗證第 3 層的 A；ask：派工短問答，唯讀但保留使用者設定；
// worker：背景 worker 要能改檔（claude 自動接受編輯、pi 開讀寫工具，codex／agy 同 driver）。
// opts.model／opts.effort：派工指定模型與思考等級（參數名見 ../references/cli-notes.md）；不給就和以前完全相同。
export function buildArgs(name, mode, prompt, { model, effort, resultFile } = {}) {
  const m = (flag, v) => (v ? [flag, v] : [])
  // prompt 以 - 開頭（如 --- frontmatter）會被當成選項（claude 報 unknown option）；前面補一個半形空格，四家都當位置參數
  if (String(prompt).startsWith('-')) prompt = ` ${prompt}`
  switch (name) {
    case 'claude': {
      const base = mode === 'worker' ? ['-p', prompt, '--permission-mode', 'acceptEdits', '--allowedTools', 'Bash']
        : mode === 'driver' ? ['-p', prompt, '--allowedTools', 'Bash']
        : mode === 'ask' ? ['-p', prompt, '--tools', 'Read,Grep,Glob'] : ['-p', prompt, '--tools', '']
      // acceptEdits 只放行 cwd（wt/）底下；結果檔在上一層，要加進可寫範圍。--add-dir 吃多個值，放最後
      const dir = mode === 'worker' && resultFile ? ['--add-dir', dirname(resultFile)] : []
      return [...base, ...m('--model', model), ...m('--effort', effort), ...dir]
    }
    case 'codex': {
      const lean = mode === 'ask' ? [] : ['--ignore-user-config', '--ignore-rules']
      const pick = [...m('-m', model), ...m('-c', effort && `model_reasoning_effort=${effort}`)]
      const full = mode === 'driver' || mode === 'worker'
      return ['exec', ...lean, ...pick, '--ephemeral', '--skip-git-repo-check', '-s', full ? 'danger-full-access' : 'read-only', prompt]
    }
    case 'agy': {
      // agy 沒有真正的唯讀：--mode plan 在 -p 只產計畫不回答，--sandbox 只限 shell、不限它的寫檔工具。
      const base = mode === 'driver' || mode === 'worker' ? ['-p', prompt, '--dangerously-skip-permissions'] : ['-p', prompt, '--sandbox', '--disable-slash-commands']
      return [...base, ...m('--model', model), ...m('--effort', effort)]
    }
    case 'pi': {
      const base = mode === 'worker' ? ['-p', prompt, '--tools', 'read,bash,edit,write', '--no-session']
        : mode === 'driver' ? ['-p', prompt, '--tools', 'bash', '--no-session']
        : mode === 'ask' ? ['-p', prompt, '--tools', 'read,grep,find,ls', '--no-mcp', '--no-session'] : ['-p', prompt, '--no-tools', '--no-session']
      // pi 的思考等級可掛在 --model 後面（"<model>:<thinking>"）；沒指定模型時用 --thinking
      const pick = model ? m('--model', effort ? `${model}:${effort}` : model) : m('--thinking', effort)
      return [...base, ...pick]
    }
    default:
      throw new Error(`未知的 CLI：${name}`)
  }
}

// 額度用盡的錯誤訊息 → 重置時間；不是額度錯誤回 null。
// 只看輸出最後 20 行（且不超過 2000 字元）：前面是 CLI 印出的 prompt 與執行紀錄，談到 rate limit 不代表真的超額。
// 關鍵字還要和錯誤字樣同一行（「Credits used: 12」這類統計不算）。
// 重置時間：相對時間（in N minutes/hours）優先，其次帶時區的 ISO 時間；不在未來 7 天內就用預設 1 小時，避免永不改派或封到遠期。
const QUOTA = /\b(usage limit|quota|rate.?limit|credits?|429)\b/i
const ERRORISH = /error|exceeded|reached|exhausted|usage limit|rate.?limit|too many requests/i
export function quotaInfo(out, now = Date.now()) {
  const tail = out.slice(-2000).split(/\r?\n/).slice(-20).join('\n')
  if (!tail.split('\n').some(l => QUOTA.test(l) && ERRORISH.test(l))) return null
  const ok = t => t > now && t <= now + 7 * 86_400_000
  const rel = tail.match(/in\s+(\d+)\s*(minute|min|hour|hr)s?\b/i)
  if (rel) return { resetAt: now + Number(rel[1]) * (/^h/i.test(rel[2]) ? 3_600_000 : 60_000) }
  for (const m of tail.matchAll(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})/g)) {
    const t = Date.parse(m[0])
    if (ok(t)) return { resetAt: t }
  }
  return { resetAt: now + 3_600_000 }
}

// 從某個 CLI 裡再叫 CLI 時，留著外層的標記會被當成巢狀 session 擋下或誤判。
// 推送用 token 一律不傳（被派的 CLI 不該 push）；真的要傳就列在 AGENT_DISPATCH_KEEP_ENV（逗號分隔）。
const PUSH_TOKENS = ['GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN', 'GITLAB_TOKEN', 'GLAB_TOKEN']
export function scrubEnv(env) {
  const keep = new Set(String(env.AGENT_DISPATCH_KEEP_ENV ?? '').split(',').map(s => s.trim()).filter(Boolean))
  const out = {}
  for (const [k, v] of Object.entries(env)) {
    if (PUSH_TOKENS.includes(k) && !keep.has(k)) continue
    if (k === 'CLAUDECODE' || k.startsWith('CLAUDE_CODE_') || k === 'HERDR_PANE_ID' || k === 'AGENT_DISPATCH_RESULT') continue
    if (k.startsWith('CODEX_') && k !== 'CODEX_HOME') continue
    if (k.startsWith('PI_') || k.startsWith('AGY_') || k.startsWith('ANTIGRAVITY_')) continue
    out[k] = v
  }
  return out
}

const cmdQuote = a => `"${String(a).replace(/"/g, '""')}"`

// npm 在 Windows 裝的 CLI 是 .cmd shim；經 cmd.exe 跑會在換行處截斷參數、展開 %VAR%。
// 讀 shim 找出它呼叫的 JS 入口，改用目前的 node 直接執行，不經 shell。
export function cmdShimTarget(bin) {
  try {
    const m = readFileSync(bin, 'utf8').match(/"%~?dp0%?\\([^"]+?\.(?:js|mjs|cjs))"/i)
    const js = m && join(dirname(bin), ...m[1].split('\\'))
    return js && existsSync(js) ? js : null
  } catch { return null }
}

// Windows 命令列上限：CreateProcess 32767 字元，經 cmd.exe 8191。超過時 spawn 的錯誤訊息很誤導，先算好直接回明確錯誤。
// 非 Windows 不檢查（ARG_MAX 大得多）。js：.cmd shim 解析出的 JS 入口（改用 node 直接跑、不經 cmd.exe）。
export function cmdLineError(bin, args, platform = process.platform, js = null) {
  if (platform !== 'win32') return null
  const viaShell = /\.cmd$/i.test(bin) && !js
  const limit = viaShell ? 8191 : 32767
  const len = (js ? [process.execPath, js, ...args] : [bin, ...args]).map(cmdQuote).join(' ').length
  return len > limit ? `[run] prompt 太長：命令列約 ${len} 字元，超過 Windows 上限 ${limit}${viaShell ? '（經 cmd.exe）' : ''}；請縮短 prompt，或把內容寫進檔案、prompt 只放路徑` : null
}

// POSIX 的子程序在自己的程序群組，終端機的 Ctrl-C 送不到；父程序結束或收到訊號時代為殺掉還在跑的群組。
const live = new Set()
function track(pid) {
  live.add(pid)
  if (live.hooked) return
  live.hooked = true
  const killAll = () => { for (const p of live) { try { process.kill(-p, 'SIGKILL') } catch { /* 已結束 */ } } }
  process.on('exit', killAll)
  for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.once(sig, () => { killAll(); process.kill(process.pid, sig) })
}

// 逾時：殺整個程序樹（POSIX 用 detached 開新程序群組、殺 -pid；Windows 用 taskkill /T /F），
// 孫程序握著 stdout 時 close 會一直等，所以殺完最多再等 2 秒就直接回。
export function run(bin, args, { cwd, timeoutMs = 180_000, env = process.env, platform = process.platform } = {}) {
  return new Promise(done => {
    const t0 = Date.now()
    const viaCmd = /\.cmd$/i.test(bin)
    const js = viaCmd ? cmdShimTarget(bin) : null
    const tooLong = cmdLineError(bin, args, platform, js)
    if (tooLong) { done({ code: null, out: tooLong, ms: 0, timedOut: false }); return }
    if (viaCmd && !js && args.some(a => /[\r\n]/.test(String(a)))) {
      done({ code: null, out: `[run] ${bin} 不是可解析的 npm shim，無法經 cmd.exe 安全傳遞多行參數`, ms: 0, timedOut: false })
      return
    }
    const detached = platform !== 'win32'
    const child = js
      ? spawn(process.execPath, [js, ...args], { cwd, env, windowsHide: true, detached })
      : viaCmd
        ? spawn([bin, ...args].map(cmdQuote).join(' '), { cwd, env, shell: true, windowsHide: true, detached })
        : spawn(bin, args, { cwd, env, windowsHide: true, detached })
    if (detached && child.pid) track(child.pid)
    const chunks = []
    let timedOut = false, ended = false, grace = null
    const killTree = () => {
      try {
        if (platform === 'win32') spawn('taskkill', ['/T', '/F', '/PID', String(child.pid)], { stdio: 'ignore', windowsHide: true })
        else process.kill(-child.pid, 'SIGKILL')
      } catch { try { child.kill('SIGKILL') } catch { /* 已結束 */ } }
    }
    const timer = setTimeout(() => {
      timedOut = true
      killTree()
      grace = setTimeout(() => finish(null), 2000)
    }, timeoutMs)
    child.stdout.on('data', c => chunks.push(c))
    child.stderr.on('data', c => chunks.push(c))
    child.stdin.on('error', () => {})
    child.stdin.end('')
    const finish = code => {
      if (ended) return
      ended = true
      live.delete(child.pid)
      clearTimeout(timer); clearTimeout(grace)
      child.stdout.destroy(); child.stderr.destroy()
      done({ code, out: Buffer.concat(chunks).toString('utf8'), ms: Date.now() - t0, timedOut })
    }
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
