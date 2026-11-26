#!/usr/bin/env node
// 背景 worker：沒有 herdr（也沒有可用的 Ghostty 分割）時的長任務模式。
// 每個 worker 一個工作目錄 <ws>：wt/（獨立 git worktree，分支 dispatch/<name>）、job.json、status.json、result.md、log.txt。
// 條件（SKILL.md 有寫）：只派不需要中途問人的工作；只在 worktree 改檔；不改主線、不 push；合併前由使用者審。
//   node bg.mjs start (--repo <r> | --worktree <既有 worktree>) --name <n> (--to <cli> | --type <類型>) [--model <m>] [--effort <e>] [--agent <plugin>:<agent>] [--timeout <秒>] --ws <dir> [--state <檔>] [--mesh <檔>] <prompt 檔>
//   node bg.mjs start --continue <上一輪 ws> --name <n> --ws <dir> [--model] [--effort] <prompt 檔>   修正輪：同一個 worktree、沿用上一輪的模型與等級；claude 系接續上一輪 session
//   node bg.mjs status --ws <dir>        只讀狀態，不等待
//   node bg.mjs wait --ws <dir> [--timeout <秒>]   阻塞到狀態不再是 running（沒有完工通知的平台用）
//   node bg.mjs ghostty-split --cwd <dir> "<指令>"   印出新分割的 id（macOS、在 Ghostty 裡）
//   node bg.mjs ghostty-close <id>
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync, rmSync, statSync } from 'node:fs'
import { join, dirname, resolve } from 'node:path'
import { spawn, execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { resolveBin, buildArgs, cliEnv, run, blockInfo, quotaInfo } from '../../agent-mesh-check/scripts/clis.mjs'
import { statePath as meshStatePath } from '../../agent-mesh-check/scripts/mesh.mjs'
import { loadRouting, statePath, readState, writeState, blockCli, parallelLimit, sleepSync, candidates, readMesh } from './route.mjs'

const self = fileURLToPath(import.meta.url)
const readJson = f => { try { return JSON.parse(readFileSync(f, 'utf8')) } catch { return null } }
const writeJson = (f, v) => writeFileSync(f, JSON.stringify(v, null, 2) + '\n')

// 能力偵測：herdr → Ghostty 分割（spike 結論見 references/background-worker.md）→ 背景
export function detectEnv(env = process.env, { ghostty = false } = {}) {
  if (env.HC_TERMINAL_ID || (env.HERDR_ENV === '1' && env.HERDR_PANE_ID)) return 'herdr'
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

const CLAUDE_FAMILY = ['claude', 'claude-api']  // 同一支 claude、共用 session 檔：換計費方式仍能 --resume
const missing = cli => cli === 'claude-api' ? '未設定 AGENT_DISPATCH_CLAUDE_API_KEY_CMD（claude-api 的 key 來源）' : `${cli} 不在 PATH 上（未安裝？）`
export const routeLine = (c, reason) => `[bg] 交給 ${c.cli}（${c.model ?? '預設模型'}／${c.effort ?? '預設等級'}），理由：${reason}`

// 候選：--to 指定一家（不改派）；--type 查表（濾掉沒裝、未通過 agent-mesh-check、封鎖中），額度／key 失效時監督程序依序改派。
// inherit：--continue 沿用上一輪實際跑的 { cli, model, effort }，只套在同一家的候選；明確帶的 --model／--effort 優先
function pickCandidates({ cli, type, model, effort, stateFile, mesh, inherit }) {
  const ov = c => {
    const h = inherit?.cli === c.cli ? inherit : {}
    return { ...c, ...((model ?? h.model) && { model: model ?? h.model }), ...((effort ?? h.effort) && { effort: effort ?? h.effort }) }
  }
  if (cli) {
    if (!resolveBin(cli)) throw new Error(missing(cli))
    return { list: [ov({ cli })], reason: '使用者指定' }
  }
  const list = candidates({ type, routing: loadRouting(), state: readState(stateFile),
    available: readMesh(mesh ?? meshStatePath(process.env)) }).filter(c => resolveBin(c.cli)).map(ov)
  if (!list.length) throw Object.assign(new Error('沒有可用的候選（未安裝、未通過 agent-mesh-check 或額度封鎖中）'), { code: 'NO_CANDIDATE' })
  return { list, reason: type }
}

const isWorktree = dir => { try { return execFileSync('git', ['-C', dir, 'rev-parse', '--is-inside-work-tree'], { encoding: 'utf8', stdio: 'pipe' }).trim() === 'true' } catch { return false } }

// 建 worktree（或用 --worktree／--continue 指定的既有 worktree）、寫 job.json 與 running 狀態；超過並行上限就拋錯。不啟動程序（start 才啟動）。
// 參數與 prompt 檔先驗完才建 worktree，失敗不留孤兒 worktree／分支。
// continueFrom：上一輪的 ws。沿用它的 worktree 與派工方式（--to／--type，可再覆寫；沒覆寫時也沿用實際跑的模型與等級，--model／--effort 可逐項覆寫）；上一輪由 claude 系跑完的，接續它的 session。
export function prepare({ repo, name, cli, type, model, effort, agent, promptFile, ws, state, mesh, timeout = 3600, worktree: existing, continueFrom, lockWaitMs }) {
  ws = resolve(ws)
  if (!(Number.isFinite(timeout) && timeout > 0)) throw new Error(`--timeout 要是正數（秒），收到 ${timeout}`)
  if (agent && !/^\w[\w.-]*(:[\w.-]+)?$/.test(agent)) throw new Error(`--agent 格式要是 <plugin>:<agent>（或單獨 <agent>），收到 ${agent}`)
  let resumeSession = null, resumeAgentApplied = false, inherit = null
  if (continueFrom) {
    const pj = readJson(join(resolve(continueFrom), 'job.json')), ps = readJson(join(resolve(continueFrom), 'status.json'))
    if (!pj || !ps) throw new Error(`--continue 讀不到上一輪的 job.json／status.json：${continueFrom}`)
    if (ps.state === 'running') throw new Error(`上一輪還在跑（${continueFrom}），等它結束再續派`)
    existing ??= pj.worktree
    if (!cli && !type) { cli = pj.to ?? (pj.type ? undefined : pj.cli); type = pj.type; inherit = { cli: ps.cli, model: ps.model, effort: ps.effort } }  // 舊版 job.json 只有 cli
    const changed = agent !== undefined && agent !== (pj.agent ?? undefined)
    agent ??= pj.agent ?? undefined  // 沿用上一輪的 Agent 定義，--agent 可覆寫
    // resume 時 claude 不重新套 --agent：session 沿用上一輪的定義，帶了不存在的名稱也不報錯（實測）。換 agent 就開新 session
    if (CLAUDE_FAMILY.includes(ps.cli) && ps.sessionId && !changed) { resumeSession = ps.sessionId; resumeAgentApplied = !!ps.agentApplied }
  }
  if (!cli && !type) throw new Error('要指定 --to <cli> 或 --type <類型>')
  // 每輪都要新的工作目錄：沿用舊的會把上一輪的 result.md 當成本輪完成
  if (['job.json', 'status.json', 'result.md'].some(f => existsSync(join(ws, f)))) throw new Error(`工作目錄已用過，每輪要新的 --ws：${ws}`)
  if (existing && !isWorktree(existing)) throw new Error(`--worktree 不是 git worktree：${existing}`)
  if (!existing && !repo) throw new Error('要指定 --repo（新建 worktree）或 --worktree（用既有的）')
  const stateFile = state ?? statePath()
  const { list, reason } = pickCandidates({ cli, type, model, effort, stateFile, mesh, inherit })
  const body = readFileSync(promptFile, 'utf8')
  return withLock(dirname(ws), () => {
    const limit = parallelLimit(readState(stateFile), loadRouting())
    if (running(dirname(ws)) >= limit) throw new Error(`並行已達上限 ${limit}，等其他 worker 結束再派`)
    mkdirSync(ws, { recursive: true })
    const worktree = existing ? resolve(existing) : join(ws, 'wt')
    if (!existing) execFileSync('git', ['-C', resolve(repo), 'worktree', 'add', '-q', worktree, '-b', `dispatch/${name}`], { stdio: 'pipe' })
    const resultFile = join(ws, 'result.md')
    const statusFile = join(ws, 'status.json')
    // 開頭固定一行：prompt 檔以 ---（frontmatter）開頭時不會被 CLI 當成選項
    const prompt = `背景 worker 任務（規則見最後一段）：

${body}

---
你是背景 worker，沒有人能即時回答你的問題。
- 只在目前目錄（git worktree）改檔；不要切分支、不要 push、不要動主線（git 的 push／fetch 在這裡已被關閉）。
- 完成或遇到需要使用者決策時，把結果寫到 ${resultFile}（完成／失敗／待決、做了什麼、要清的路徑），寫完就停。寫完結果檔才算完成。`
    const line = routeLine(list[0], reason)
    writeJson(join(ws, 'job.json'), { name, to: cli ?? null, type: cli ? null : type, candidates: list, reason, timeout, worktree, resultFile, statusFile, stateFile, prompt, resumeSession, resumeAgentApplied, agent: agent ?? null })
    writeJson(statusFile, { state: 'running', pid: process.pid, cli: list[0].cli, model: list[0].model, effort: list[0].effort, line, startedAt: new Date().toISOString() })
    return { ws, worktree, statusFile, resultFile, line }
  }, lockWaitMs)
}

// worker 程序的環境：清巢狀標記與推送用 token、依 cli 處理 API key（cliEnv；claude-api 取 key 失敗回 null），並用 GIT_CONFIG_* 只對 worker 關掉 git 的所有遠端傳輸，
// push 一律失敗（fetch 也會失敗）。protocol.<名>.allow 優先於 protocol.allow，常見的幾種都蓋掉。不寫進 repo 設定，主 repo 不受影響。
const GIT_PROTOCOLS = ['', 'file.', 'git.', 'ssh.', 'http.', 'https.', 'ext.']
export function workerEnv(env, resultFile, cli = 'claude') {
  const base = cliEnv(cli, env)
  if (!base) return null
  const out = { ...base, AGENT_DISPATCH_RESULT: resultFile }
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

// 改派時給下一家的提示：worktree 裡可能有前一家沒做完的改動
const RETRY_NOTE = prev => `\n\n注意：前一位 worker（${prev}）被額度或 API key 問題中斷，worktree 可能留有它沒做完的改動；先看 git status 與 git log 再接手。`
// 非 claude 系不支援 --agent：退回「prompt 叫它讀定義檔照做」，status.json 的 agentNote 記下
const AGENT_NOTE = a => `\n\n注意：派工指定的 Agent 定義是 ${a}，但這次沒能用 --agent 套上；請讀 prompt 裡指明的定義檔並照它做，沒指明就找 agents/${a.split(':').at(-1)}.md。`
const AGENT_MISSING = /--agent '[^']*' not found/  // 該 plugin 在這個 worktree 沒啟用：同一家去掉 --agent、改走 prompt 退路
const NO_SESSION = /no conversation found/i

// 監督者：依序跑候選 CLI、等它結束、依結果檔寫最終狀態、發通知。start 以 detached 方式起這個模式。
// 結果檔存在就是 done（輸出裡碰巧談到 429 不算額度錯誤）；額度用盡或 key 失效就封鎖那一家、改派下一個候選（--to 指定的不改派）。
// 續派（job.resumeSession）：claude 系接續上一輪的 session；session 不見了就同一家開新 session 重跑一次。
// 監督程序自己出錯也寫 failed，不留 running。
export async function supervise(ws) {
  const job = readJson(join(ws, 'job.json'))
  const list = job.candidates ?? [{ cli: job.cli, model: job.model, effort: job.effort }]  // 舊版 job.json
  let status = { ...readJson(job.statusFile), pid: process.pid }
  writeJson(job.statusFile, status)
  const attempts = [], log = []
  let contention = false, last = null, resumable = !!job.resumeSession, agentOffCli = null
  try {
    for (let i = 0; i < list.length; i++) {
      const c = list[i]
      const env = workerEnv(process.env, job.resultFile, c.cli)
      if (!env) {  // key 只在這裡的記憶體；失敗訊息不含 key 指令的輸出
        attempts.push({ cli: c.cli, outcome: 'key' })
        last = { state: 'failed', tail: `${c.cli} 取 key 失敗（檢查 AGENT_DISPATCH_CLAUDE_API_KEY_CMD）` }
        // 封 1 小時：否則 pick 一直挑它、重派一直 failed。狀態檔寫不進去也繼續改派下一家
        try { blockCli(job.stateFile, c.cli, Date.now() + 3_600_000, 'key') } catch (e) { last.stateError = String(e?.message ?? e) }
        continue
      }
      const claude = CLAUDE_FAMILY.includes(c.cli)
      const resume = claude && resumable ? job.resumeSession : null
      const sessionId = claude && !resume ? randomUUID() : null
      const agent = job.agent ?? null
      const agentNative = !!agent && claude && agentOffCli !== c.cli && !resume
      const agentApplied = resume ? !!(agent && job.resumeAgentApplied) : agentNative
      const prompt = (attempts.length ? job.prompt + RETRY_NOTE(attempts.at(-1).cli) : job.prompt) + (agent && !agentApplied && !resume ? AGENT_NOTE(agent) : '')
      const line = attempts.length ? `${routeLine(c, job.reason)}；改派自 ${attempts.map(a => `${a.cli}（${a.outcome}）`).join('、')}` : status.line
      status = { ...status, cli: c.cli, model: c.model, effort: c.effort, line, sessionId: resume ?? sessionId, resumed: !!resume, attempts, agent, agentApplied, agentNote: !agent || agentApplied ? undefined : resume ? '接續上一輪 session，上一輪未套上定義' : `${c.cli} ${claude ? '找不到該 Agent 定義（plugin 未啟用？）' : '不支援 --agent'}，已改在 prompt 叫它讀定義檔`, startedAt: new Date().toISOString() }
      writeJson(job.statusFile, status)
      const r = await run(resolveBin(c.cli), buildArgs(c.cli, 'worker', prompt, { ...c, resultFile: job.resultFile, sessionId, resume, agent: agentNative ? agent : undefined }), {
        cwd: job.worktree, timeoutMs: job.timeout * 1000, env })
      log.push(`===== ${c.cli}（${c.model ?? '預設模型'}／${c.effort ?? '預設等級'}）${resume ? `resume ${resume}` : ''} =====\n${r.out}`)
      writeFileSync(join(ws, 'log.txt'), log.join('\n'))
      const done = existsSync(job.resultFile)
      if (!done && agentNative && r.code !== 0 && !r.timedOut && AGENT_MISSING.test(r.out.slice(0, 2000))) { agentOffCli = c.cli; i--; continue }
      if (!done && resume && NO_SESSION.test(r.out.slice(-2000))) { resumable = false; i--; continue }  // 同一家改開新 session
      const q = !done && r.code !== 0 && !r.timedOut ? blockInfo(c.cli, r.out) : null
      last = { state: done ? 'done' : q ? 'quota' : 'failed', code: r.code, timedOut: r.timedOut, ...(!done && { tail: r.out.slice(-2000) }) }
      if (r.timedOut) contention = true
      if (!q) break
      contention = true
      attempts.push({ cli: c.cli, outcome: quotaInfo(r.out) ? 'quota' : 'auth' })
      try { blockCli(job.stateFile, c.cli, q.resetAt, attempts.at(-1).outcome) } catch (e) { last.stateError = String(e?.message ?? e) }
      if (job.to) break  // 指定對象：不改派，照實回 quota
    }
    // 先寫最終狀態：之後改共用狀態檔（降並行）失敗也不能把 done 翻成 failed
    const final = { ...status, ...last, attempts, endedAt: new Date().toISOString() }
    writeJson(job.statusFile, final)
    try {
      if (contention) {  // 爭用（額度、逾時）→ 並行上限降 1（最低 1），1 小時後自動恢復
        const s = readState(job.stateFile)
        writeState(job.stateFile, { ...s, maxParallel: Math.max(1, parallelLimit(s, loadRouting()) - 1), parallelResetAt: Date.now() + 3_600_000 })
      }
    } catch (e) { writeJson(job.statusFile, { ...final, stateError: String(e?.message ?? e) }) }
    notify(`worker ${job.name}：${final.state}（${final.cli}）`, final.state === 'done' ? job.resultFile : '看 status.json 與 log.txt')
    return final.state
  } catch (e) {
    writeJson(job.statusFile, { ...status, state: 'failed', error: String(e?.message ?? e), attempts, endedAt: new Date().toISOString() })
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
    const key = { '--repo': 'repo', '--name': 'name', '--to': 'cli', '--type': 'type', '--model': 'model', '--effort': 'effort', '--agent': 'agent',
      '--timeout': 'timeout', '--ws': 'ws', '--state': 'state', '--mesh': 'mesh', '--cwd': 'cwd', '--worktree': 'worktree', '--continue': 'continueFrom' }[rest[i]]
    if (key) o[key] = rest[++i]; else file = rest[i]
  }
  if (rest.includes('--agent') && !o.agent) { console.error('--agent 要帶值：<plugin>:<agent>'); return 2 }
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
  if (cmd === 'start' && o.name && o.ws && file && (o.continueFrom || ((o.repo || o.worktree) && (o.cli || o.type)))) {
    try {
      const j = start({ ...o, timeout: o.timeout ? Number(o.timeout) : undefined, promptFile: file })
      console.log(j.line)  // 第一行固定「交給 <cli>（<模型>／<等級>），理由：…」；改派後的實際對象看 status 的 line
      console.log(`已啟動背景 worker ${o.name}：worktree ${j.worktree}；狀態 ${j.statusFile}；結果 ${j.resultFile}`)
      return 0
    } catch (e) { console.error(e.message); return e.code === 'NO_CANDIDATE' ? 75 : 1 }
  }
  console.error(`用法：node bg.mjs start (--repo <r> | --worktree <既有 worktree>) --name <n> (--to <cli> | --type <類型>) [--model] [--effort] [--agent] [--timeout] --ws <dir> [--state] [--mesh] <prompt 檔>
      node bg.mjs start --continue <上一輪 ws> --name <n> --ws <dir> [--to | --type] [--model] [--effort] <prompt 檔>（沒帶就沿用上一輪的模型與等級）
      node bg.mjs status --ws <dir>
      node bg.mjs wait --ws <dir> [--timeout <秒>]
      node bg.mjs ghostty-split --cwd <dir> "<指令>"
      node bg.mjs ghostty-close <id>`)
  return 2
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  Promise.resolve(cli(process.argv.slice(2))).then(code => { process.exitCode = code })
}
