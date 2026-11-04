#!/usr/bin/env node
// 背景 worker：沒有 herdr（也沒有可用的 Ghostty 分割）時的長任務模式。
// 每個 worker 一個工作目錄 <ws>：wt/（獨立 git worktree，分支 dispatch/<name>）、job.json、status.json、result.md、log.txt。
// 條件（SKILL.md 有寫）：只派不需要中途問人的工作；只在 worktree 改檔；不改主線、不 push；合併前由使用者審。
//   node bg.mjs start --repo <r> --name <n> --to <cli> [--model <m>] [--effort <e>] [--timeout <秒>] --ws <dir> [--state <檔>] <prompt 檔>
//   node bg.mjs status --ws <dir>        只讀狀態，不等待
//   node bg.mjs wait --ws <dir> [--timeout <秒>]   阻塞到狀態不再是 running（沒有完工通知的平台用）
//   node bg.mjs ghostty-split --cwd <dir> "<指令>"   印出新分割的 id（macOS、在 Ghostty 裡）
//   node bg.mjs ghostty-close <id>
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync, rmSync, statSync } from 'node:fs'
import { join, dirname, resolve } from 'node:path'
import { spawn, execFileSync } from 'node:child_process'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { resolveBin, buildArgs, scrubEnv, run, quotaInfo } from '../../agent-mesh-check/scripts/clis.mjs'
import { loadRouting, statePath, readState, writeState, blockCli, parallelLimit, sleepSync } from './route.mjs'

const self = fileURLToPath(import.meta.url)
const readJson = f => { try { return JSON.parse(readFileSync(f, 'utf8')) } catch { return null } }
const writeJson = (f, v) => writeFileSync(f, JSON.stringify(v, null, 2) + '\n')

// 能力偵測：herdr → Ghostty 分割（spike 結論見 references/background-worker.md）→ 背景
export function detectEnv(env = process.env, { ghostty = false } = {}) {
  if (env.HERDR_ENV === '1') return 'herdr'
  if (ghostty) return 'ghostty'
  return 'background'
}

// Ghostty 分割（macOS，Ghostty 1.4 起有 AppleScript 字典；spike 結論見 references/background-worker.md）
export const ghosttyAvailable = (env = process.env, platform = process.platform) =>
  platform === 'darwin' && env.TERM_PROGRAM === 'ghostty'

const asq = s => `"${String(s).replace(/[\\"]/g, '\\$&')}"`
export function ghosttySplitScript({ cwd, command, env = [] }) {
  return [
    'tell application "Ghostty"',
    '  set cfg to new surface configuration',
    `  set initial working directory of cfg to ${asq(cwd)}`,
    `  set command of cfg to ${asq(command)}`,
    `  set environment variables of cfg to {${env.map(asq).join(', ')}}`,
    '  set t to split (focused terminal of selected tab of front window) direction right with configuration cfg',
    '  return id of t',
    'end tell',
  ].join('\n')
}

// 分割不會在指令結束後自己關（wait after command 設 false 也一樣），收工要用 id 關掉
export const ghosttyCloseScript = id =>
  `tell application "Ghostty" to close (first terminal of selected tab of front window whose id is ${asq(id)})`

const alive = pid => { try { process.kill(pid, 0); return true } catch (e) { return e.code === 'EPERM' } }

// wsRoot 底下各工作目錄中，狀態是 running 且程序還活著、沒過期的數量
export function running(wsRoot) {
  if (!existsSync(wsRoot)) return 0
  return readdirSync(wsRoot, { withFileTypes: true }).filter(d => d.isDirectory())
    .filter(d => statusOf(join(wsRoot, d.name))?.state === 'running').length
}

// 同一個上層目錄的「數 running → 寫 running」要互斥：mkdir 當鎖（原子操作），超過 60 秒沒釋放視為過期
const LOCK_STALE_MS = 60_000
function withLock(dir, fn, waitMs = 10_000) {
  mkdirSync(dir, { recursive: true })
  const lock = join(dir, '.agent-dispatch.lock')
  const end = Date.now() + waitMs
  for (;;) {
    try { mkdirSync(lock); break } catch (e) {
      if (e.code !== 'EEXIST') throw e
      try { if (Date.now() - statSync(lock).mtimeMs > LOCK_STALE_MS) { rmSync(lock, { recursive: true, force: true }); continue } } catch { continue }
      if (Date.now() >= end) throw new Error(`拿不到並行鎖 ${lock}：另一個 start 進行中（超過 60 秒沒釋放會自動視為過期）`)
      sleepSync(100)
    }
  }
  try { return fn() } finally { rmSync(lock, { recursive: true, force: true }) }
}

// 建 worktree、寫 job.json 與 running 狀態；超過並行上限就拋錯。不啟動程序（start 才啟動）。
// 參數與 prompt 檔先驗完才建 worktree，失敗不留孤兒 worktree／分支。
export function prepare({ repo, name, cli, model, effort, promptFile, ws, state, timeout = 3600, lockWaitMs }) {
  ws = resolve(ws)
  if (!(Number.isFinite(timeout) && timeout > 0)) throw new Error(`--timeout 要是正數（秒），收到 ${timeout}`)
  if (!resolveBin(cli)) throw new Error(`${cli} 不在 PATH 上（未安裝？）`)
  const body = readFileSync(promptFile, 'utf8')
  const stateFile = state ?? statePath()
  return withLock(dirname(ws), () => {
    const limit = parallelLimit(readState(stateFile), loadRouting())
    if (running(dirname(ws)) >= limit) throw new Error(`並行已達上限 ${limit}，等其他 worker 結束再派`)
    mkdirSync(ws, { recursive: true })
    const worktree = join(ws, 'wt')
    execFileSync('git', ['-C', resolve(repo), 'worktree', 'add', '-q', worktree, '-b', `dispatch/${name}`], { stdio: 'pipe' })
    const resultFile = join(ws, 'result.md')
    const statusFile = join(ws, 'status.json')
    // 開頭固定一行：prompt 檔以 ---（frontmatter）開頭時不會被 CLI 當成選項
    const prompt = `背景 worker 任務（規則見最後一段）：

${body}

---
你是背景 worker，沒有人能即時回答你的問題。
- 只在目前目錄（獨立 git worktree）改檔；不要切分支、不要 push、不要動主線（git 的 push／fetch 在這裡已被關閉）。
- 完成或遇到需要使用者決策時，把結果寫到 ${resultFile}（完成／失敗／待決、做了什麼、要清的路徑），寫完就停。寫完結果檔才算完成。`
    writeJson(join(ws, 'job.json'), { name, cli, model, effort, timeout, worktree, resultFile, statusFile, stateFile, prompt })
    writeJson(statusFile, { state: 'running', pid: process.pid, cli, startedAt: new Date().toISOString() })
    return { ws, worktree, statusFile, resultFile }
  }, lockWaitMs)
}

// worker 程序的環境：清巢狀標記與推送用 token（scrubEnv），並用 GIT_CONFIG_* 只對 worker 關掉 git 的所有遠端傳輸，
// push 一律失敗（fetch 也會失敗）。protocol.<名>.allow 優先於 protocol.allow，常見的幾種都蓋掉。不寫進 repo 設定，主 repo 不受影響。
const GIT_PROTOCOLS = ['', 'file.', 'git.', 'ssh.', 'http.', 'https.', 'ext.']
export function workerEnv(env, resultFile) {
  const out = { ...scrubEnv(env), AGENT_DISPATCH_RESULT: resultFile }
  let n = Number(out.GIT_CONFIG_COUNT) || 0
  for (const p of GIT_PROTOCOLS) { out[`GIT_CONFIG_KEY_${n}`] = `protocol.${p}allow`; out[`GIT_CONFIG_VALUE_${n}`] = 'never'; n++ }
  out.GIT_CONFIG_COUNT = String(n)
  return out
}

function notify(title, msg) {
  if (process.env.AGENT_DISPATCH_NO_NOTIFY === '1' || process.platform !== 'darwin') return  // 其他平台未支援
  const q = s => String(s).replace(/["\\]/g, '\\$&')
  try { execFileSync('osascript', ['-e', `display notification "${q(msg)}" with title "${q(title)}"`], { stdio: 'ignore' }) } catch { /* 通知失敗不影響結果 */ }
}

// 監督者：跑 CLI、等它結束、依結果檔寫最終狀態、發通知。start 以 detached 方式起這個模式。
// 結果檔存在就是 done（輸出裡碰巧談到 429 不算額度錯誤）；監督程序自己出錯也寫 failed，不留 running。
export async function supervise(ws) {
  const job = readJson(join(ws, 'job.json'))
  const status = { ...readJson(job.statusFile), pid: process.pid }
  writeJson(job.statusFile, status)
  try {
    const r = await run(resolveBin(job.cli), buildArgs(job.cli, 'worker', job.prompt, job), {
      cwd: job.worktree, timeoutMs: job.timeout * 1000,
      env: workerEnv(process.env, job.resultFile) })
    writeFileSync(join(ws, 'log.txt'), r.out)
    const done = existsSync(job.resultFile)
    const q = !done && r.code !== 0 && !r.timedOut ? quotaInfo(r.out) : null
    const state = done ? 'done' : q ? 'quota' : 'failed'
    // 先寫最終狀態：之後改共用狀態檔（封鎖、降並行）失敗也不能把 done 翻成 failed
    const final = { ...status, state, code: r.code, timedOut: r.timedOut, endedAt: new Date().toISOString(),
      ...(state !== 'done' && { tail: r.out.slice(-2000) }) }
    writeJson(job.statusFile, final)
    try {
      if (q) blockCli(job.stateFile, job.cli, q.resetAt, 'quota')
      if (q || r.timedOut) {  // 爭用（額度、逾時）→ 並行上限降 1（最低 1），1 小時後自動恢復
        const s = readState(job.stateFile)
        writeState(job.stateFile, { ...s, maxParallel: Math.max(1, parallelLimit(s, loadRouting()) - 1), parallelResetAt: Date.now() + 3_600_000 })
      }
    } catch (e) { writeJson(job.statusFile, { ...final, stateError: String(e?.message ?? e) }) }
    notify(`worker ${job.name}：${state}`, state === 'done' ? job.resultFile : '看 status.json 與 log.txt')
    return state
  } catch (e) {
    writeJson(job.statusFile, { ...status, state: 'failed', error: String(e?.message ?? e), endedAt: new Date().toISOString() })
    notify(`worker ${job.name}：failed`, '看 status.json')
    return 'failed'
  }
}

export function start(opts) {
  const job = prepare(opts)
  const child = spawn(process.execPath, [self, '--supervise', job.ws], { detached: true, stdio: 'ignore', windowsHide: true })
  child.unref()
  // 立刻記監督程序的 pid：start 自己馬上結束，等監督程序開機才改會有空窗，並行計數會漏算
  writeJson(job.statusFile, { ...readJson(job.statusFile), pid: child.pid })
  return job
}

// 狀態檔寫 running 但程序已不在（被殺、重開機）→ 視為 failed。
// pid 可能被別的程序重用：已超過 startedAt＋job 的 timeout＋60 秒緩衝仍是 running，也視為 failed（stale）。
const STALE_MS = 60_000
export function statusOf(ws, now = Date.now()) {
  const s = readJson(join(ws, 'status.json'))
  if (s?.state !== 'running') return s
  if (!alive(s.pid)) return { ...s, state: 'failed', note: 'supervisor gone' }
  const timeout = readJson(join(ws, 'job.json'))?.timeout
  const started = Date.parse(s.startedAt)
  if (timeout > 0 && now > started + timeout * 1000 + STALE_MS) return { ...s, state: 'failed', note: 'stale：超過 timeout 仍是 running（pid 可能已被重用）' }
  return s
}

// 阻塞等到狀態不再是 running；逾時回 { state: 'timeout' }
export async function wait(ws, { timeoutMs = 3_600_000, intervalMs = 2000 } = {}) {
  const end = Date.now() + timeoutMs
  for (;;) {
    const s = statusOf(ws)
    if (s?.state !== 'running') return s
    if (Date.now() >= end) return { ...s, state: 'timeout' }
    await new Promise(r => setTimeout(r, intervalMs))
  }
}

function cli(argv) {
  const [cmd, ...rest] = argv
  if (cmd === '--supervise') return supervise(rest[0]).then(() => 0)
  const o = {}
  let file = null
  for (let i = 0; i < rest.length; i++) {
    const key = { '--repo': 'repo', '--name': 'name', '--to': 'cli', '--model': 'model', '--effort': 'effort',
      '--timeout': 'timeout', '--ws': 'ws', '--state': 'state', '--cwd': 'cwd' }[rest[i]]
    if (key) o[key] = rest[++i]; else file = rest[i]
  }
  // 互動分割有人在場，不設 AGENT_DISPATCH_RESULT：否則 Stop hook 會在 worker 每次想問人時擋下
  if (cmd === 'ghostty-split' && o.cwd && file) {
    console.log(execFileSync('osascript', ['-e', ghosttySplitScript({ cwd: o.cwd, command: file })], { encoding: 'utf8' }).trim())
    return 0
  }
  if (cmd === 'ghostty-close' && file) { execFileSync('osascript', ['-e', ghosttyCloseScript(file)]); return 0 }
  if (cmd === 'status' && o.ws) { console.log(JSON.stringify(statusOf(o.ws), null, 2)); return 0 }
  if (cmd === 'wait' && o.ws) {
    return wait(o.ws, o.timeout ? { timeoutMs: Number(o.timeout) * 1000 } : {}).then(s => {
      console.log(JSON.stringify(s, null, 2))
      return s?.state === 'done' ? 0 : s?.state === 'timeout' ? 124 : 1
    })
  }
  if (cmd === 'start' && o.repo && o.name && o.cli && o.ws && file) {
    try {
      const j = start({ ...o, timeout: o.timeout ? Number(o.timeout) : undefined, promptFile: file })
      console.log(`已啟動背景 worker ${o.name}：worktree ${j.worktree}；狀態 ${j.statusFile}；結果 ${j.resultFile}`)
      return 0
    } catch (e) { console.error(e.message); return 1 }
  }
  console.error(`用法：node bg.mjs start --repo <r> --name <n> --to <cli> [--model] [--effort] [--timeout] --ws <dir> [--state] <prompt 檔>
      node bg.mjs status --ws <dir>
      node bg.mjs wait --ws <dir> [--timeout <秒>]
      node bg.mjs ghostty-split --cwd <dir> "<指令>"
      node bg.mjs ghostty-close <id>`)
  return 2
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  Promise.resolve(cli(process.argv.slice(2))).then(code => { process.exitCode = code })
}
