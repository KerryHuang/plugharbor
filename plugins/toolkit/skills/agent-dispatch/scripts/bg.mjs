#!/usr/bin/env node
// 背景 worker：沒有 herdr（也沒有可用的 Ghostty 分割）時的長任務模式。
// 每個 worker 一個工作目錄 <ws>：wt/（獨立 git worktree，分支 dispatch/<name>）、job.json、status.json、result.md、log.txt。
// 條件（SKILL.md 有寫）：只派不需要中途問人的工作；只在 worktree 改檔；不改主線、不 push；合併前由使用者審。
//   node bg.mjs start --repo <r> --name <n> --to <cli> [--model <m>] [--effort <e>] [--timeout <秒>] --ws <dir> [--state <檔>] <prompt 檔>
//   node bg.mjs status --ws <dir>        只讀狀態，不等待
//   node bg.mjs wait --ws <dir> [--timeout <秒>]   阻塞到狀態不再是 running（沒有完工通知的平台用）
//   node bg.mjs ghostty-split --cwd <dir> "<指令>"   印出新分割的 id（macOS、在 Ghostty 裡）
//   node bg.mjs ghostty-close <id>
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync } from 'node:fs'
import { join, dirname, resolve } from 'node:path'
import { spawn, execFileSync } from 'node:child_process'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { resolveBin, buildArgs, scrubEnv, run, quotaInfo } from '../../agent-mesh-check/scripts/clis.mjs'
import { loadRouting, statePath, readState, writeState, blockCli, parallelLimit } from './route.mjs'

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

// wsRoot 底下各工作目錄中，狀態是 running 且程序還活著的數量
export function running(wsRoot) {
  if (!existsSync(wsRoot)) return 0
  return readdirSync(wsRoot, { withFileTypes: true }).filter(d => d.isDirectory()).filter(d => {
    const s = readJson(join(wsRoot, d.name, 'status.json'))
    return s?.state === 'running' && alive(s.pid)
  }).length
}

// 建 worktree、寫 job.json 與 running 狀態；超過並行上限就拋錯。不啟動程序（start 才啟動）。
export function prepare({ repo, name, cli, model, effort, promptFile, ws, state, timeout = 3600 }) {
  ws = resolve(ws)
  const stateFile = state ?? statePath()
  const limit = parallelLimit(readState(stateFile), loadRouting())
  if (running(dirname(ws)) >= limit) throw new Error(`並行已達上限 ${limit}，等其他 worker 結束再派`)
  if (!resolveBin(cli)) throw new Error(`${cli} 不在 PATH 上（未安裝？）`)
  mkdirSync(ws, { recursive: true })
  const worktree = join(ws, 'wt')
  execFileSync('git', ['-C', resolve(repo), 'worktree', 'add', '-q', worktree, '-b', `dispatch/${name}`], { stdio: 'pipe' })
  const resultFile = join(ws, 'result.md')
  const statusFile = join(ws, 'status.json')
  const prompt = `${readFileSync(promptFile, 'utf8')}

---
你是背景 worker，沒有人能即時回答你的問題。
- 只在目前目錄（獨立 git worktree）改檔；不要切分支、不要 push、不要動主線。
- 完成或遇到需要使用者決策時，把結果寫到 ${resultFile}（完成／失敗／待決、做了什麼、要清的路徑），寫完就停。寫完結果檔才算完成。`
  writeJson(join(ws, 'job.json'), { name, cli, model, effort, timeout, worktree, resultFile, statusFile, stateFile, prompt })
  writeJson(statusFile, { state: 'running', pid: process.pid, cli, startedAt: new Date().toISOString() })
  return { ws, worktree, statusFile, resultFile }
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
      env: { ...scrubEnv(process.env), AGENT_DISPATCH_RESULT: job.resultFile } })
    writeFileSync(join(ws, 'log.txt'), r.out)
    const done = existsSync(job.resultFile)
    const q = !done && r.code !== 0 && !r.timedOut ? quotaInfo(r.out) : null
    const state = done ? 'done' : q ? 'quota' : 'failed'
    if (q) blockCli(job.stateFile, job.cli, q.resetAt, 'quota')
    if (q || r.timedOut) {  // 爭用（額度、逾時）→ 並行上限降 1（最低 1），1 小時後自動恢復
      const s = readState(job.stateFile)
      writeState(job.stateFile, { ...s, maxParallel: Math.max(1, parallelLimit(s, loadRouting()) - 1), parallelResetAt: Date.now() + 3_600_000 })
    }
    writeJson(job.statusFile, { ...status, state, code: r.code, timedOut: r.timedOut, endedAt: new Date().toISOString(),
      ...(state !== 'done' && { tail: r.out.slice(-2000) }) })
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

// 狀態檔寫 running 但程序已不在（被殺、重開機）→ 視為 failed
export function statusOf(ws) {
  const s = readJson(join(ws, 'status.json'))
  return s?.state === 'running' && !alive(s.pid) ? { ...s, state: 'failed', note: 'supervisor gone' } : s
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
