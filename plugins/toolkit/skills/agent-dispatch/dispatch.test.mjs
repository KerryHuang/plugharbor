import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildArgs, quotaInfo, run, scrubEnv } from '../agent-mesh-check/scripts/clis.mjs'
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, delimiter, basename } from 'node:path'
import { loadRouting, readState, blockCli, meshAvailable, candidates, needsCrossReview, reviewer, statePath } from './scripts/route.mjs'

const has = (args, ...seq) => {
  const i = args.indexOf(seq[0])
  return i >= 0 && seq.every((s, k) => args[i + k] === s)
}

test('buildArgs 不給 opts 時與既有輸出相同', () => {
  assert.deepEqual(buildArgs('claude', 'ask', 'p'), ['-p', 'p', '--tools', ''])
  assert.deepEqual(buildArgs('codex', 'ask', 'p'), ['exec', '--ephemeral', '--skip-git-repo-check', '-s', 'read-only', 'p'])
  assert.deepEqual(buildArgs('agy', 'ask', 'p'), ['-p', 'p', '--sandbox', '--disable-slash-commands'])
  assert.deepEqual(buildArgs('pi', 'ask', 'p'), ['-p', 'p', '--no-tools', '--no-session'])
})

test('buildArgs 帶 model 與 effort：claude', () => {
  const a = buildArgs('claude', 'ask', 'p', { model: 'opus', effort: 'high' })
  assert.ok(has(a, '--model', 'opus') && has(a, '--effort', 'high'))
})

test('buildArgs 帶 model 與 effort：codex 參數在 prompt 之前', () => {
  const a = buildArgs('codex', 'ask', 'p', { model: 'gpt-5.5', effort: 'high' })
  assert.ok(has(a, '-m', 'gpt-5.5') && has(a, '-c', 'model_reasoning_effort=high'))
  assert.equal(a.at(-1), 'p')
})

test('buildArgs 帶 model 與 effort：agy', () => {
  const a = buildArgs('agy', 'ask', 'p', { model: 'x', effort: 'high' })
  assert.ok(has(a, '--model', 'x') && has(a, '--effort', 'high'))
})

test('buildArgs 帶 model 與 effort：pi 用 model:thinking，沒 model 用 --thinking', () => {
  assert.ok(has(buildArgs('pi', 'ask', 'p', { model: 'x', effort: 'high' }), '--model', 'x:high'))
  assert.ok(has(buildArgs('pi', 'ask', 'p', { effort: 'high' }), '--thinking', 'high'))
})

test('quotaInfo 解析 ISO 重置時間', () => {
  const t = '2026-11-04T10:00:00Z'
  assert.deepEqual(quotaInfo(`Error: usage limit reached. Resets at ${t}`, Date.parse('2026-11-04T09:00:00Z')), { resetAt: Date.parse(t) })
})

test('quotaInfo 沒有重置時間預設 1 小時', () => {
  assert.deepEqual(quotaInfo('rate limit exceeded', 1000), { resetAt: 1000 + 3_600_000 })
})

test('quotaInfo 解析相對時間', () => {
  assert.deepEqual(quotaInfo('quota hit, try again in 15 minutes', 0), { resetAt: 15 * 60_000 })
})

test('run：npm 的 .cmd shim 改直接用 node 執行，多行參數與 %VAR% 原樣傳遞', async () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-cmd-'))
  mkdirSync(join(d, 'node_modules', 'x', 'bin'), { recursive: true })
  writeFileSync(join(d, 'node_modules', 'x', 'bin', 'x.js'), 'process.stdout.write(JSON.stringify(process.argv.slice(2)))')
  writeFileSync(join(d, 'x.cmd'), '@ECHO off\r\nSETLOCAL\r\nendLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  "%dp0%\\node_modules\\x\\bin\\x.js" %*\r\n')
  const r = await run(join(d, 'x.cmd'), ['line1\nline2', '%PATH%'])
  assert.equal(r.out, JSON.stringify(['line1\nline2', '%PATH%']))
})

test('run：解析不了的 .cmd 遇到多行參數直接失敗，不默默截斷', async () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-cmd-'))
  writeFileSync(join(d, 'y.cmd'), '@echo off\r\nsomething.exe %*\r\n')
  const r = await run(join(d, 'y.cmd'), ['a\nb'])
  assert.equal(r.code, null)
  assert.match(r.out, /多行/)
})

test('quotaInfo：只看輸出尾段，前面 prompt 或 log 裡談到 rate limit 不算', () => {
  const out = 'The handler returns 429 when the rate limit is hit.\n' + 'x'.repeat(3000) + '\nError: model not found'
  assert.equal(quotaInfo(out, 0), null)
})

test('quotaInfo：相對時間優先於 log 前綴的 ISO 時間', () => {
  const now = Date.parse('2026-11-04T09:00:00Z')
  assert.deepEqual(quotaInfo('[2026-11-04T10:00:00] usage limit. Try again in 2 hours.', now), { resetAt: now + 2 * 3_600_000 })
})

test('quotaInfo：重置時間不在未來 7 天內就用預設 1 小時', () => {
  const now = Date.parse('2026-11-04T09:00:00Z')
  assert.deepEqual(quotaInfo('usage limit reached, resets 2099-01-01T00:00Z', now), { resetAt: now + 3_600_000 })
  assert.deepEqual(quotaInfo('usage limit reached, resets 2026-11-01T00:00Z', now), { resetAt: now + 3_600_000 })
})

test('quotaInfo 正常輸出回 null', () => {
  assert.equal(quotaInfo('all good'), null)
})

// ── 路由表 ──
const routing = loadRouting()
const firstOf = { 'plan': 'codex', 'architecture': 'codex', 'review-critical': 'codex',
  'implement': 'claude', 'research': 'claude', 'qa': 'claude', 'debug': 'claude',
  'docs': 'agy', 'format': 'agy', 'mechanical': 'agy' }
const none = { blocks: {} }

for (const [type, cli] of Object.entries(firstOf)) {
  test(`candidates：${type} 第一名是 ${cli}`, () => {
    const c = candidates({ type, routing, state: none, available: null, now: 0 })
    assert.equal(c[0].cli, cli)
    assert.equal(c.length, 4)
    assert.equal(c.at(-1).cli, 'pi')
    assert.ok(c.every(x => x.model && x.effort))
  })
}

test('candidates：封鎖中的 CLI 排除，過期的照常出現', () => {
  const state = { blocks: { codex: { until: 100 }, agy: { until: 10 } } }
  const c = candidates({ tier: 'top', routing, state, available: null, now: 50 }).map(x => x.cli)
  assert.ok(!c.includes('codex') && c.includes('agy'))
})

test('candidates：只剩可用的 CLI，exclude 也排除', () => {
  assert.deepEqual(candidates({ tier: 'top', routing, state: none, available: new Set(['claude']), now: 0 }).map(x => x.cli), ['claude'])
  assert.ok(!candidates({ tier: 'top', routing, state: none, available: null, now: 0, exclude: ['codex'] }).some(x => x.cli === 'codex'))
})

test('candidates：未知類型拋錯', () => {
  assert.throws(() => candidates({ type: 'nope', routing, state: none, available: null, now: 0 }))
})

test('needsCrossReview 依路徑樣式與行數門檻', () => {
  assert.equal(needsCrossReview({ paths: ['src/auth/login.ts'], lines: 10 }, routing), true)
  assert.equal(needsCrossReview({ paths: ['README.md'], lines: 301 }, routing), true)
  assert.equal(needsCrossReview({ paths: ['README.md'], lines: 20 }, routing), false)
})

test('reviewer 優先挑不同家族，湊不到退回同家', () => {
  const r = reviewer({ author: 'claude', routing, state: none, available: null, now: 0 })
  assert.equal(r.cli, 'codex'); assert.equal(r.crossFamily, true)
  const s = reviewer({ author: 'claude', routing, state: none, available: new Set(['claude', 'pi']), now: 0 })
  assert.equal(s.crossFamily, false)
})

test('readState：不存在或壞掉回空', () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-'))
  assert.deepEqual(readState(join(d, 'none.json')), { blocks: {} })
  writeFileSync(join(d, 'bad.json'), '{oops')
  assert.deepEqual(readState(join(d, 'bad.json')), { blocks: {} })
})

test('blockCli 寫入後讀得回來', () => {
  const f = join(mkdtempSync(join(tmpdir(), 'ad-')), 'sub', 'state.json')
  blockCli(f, 'codex', 123, 'quota')
  assert.deepEqual(readState(f).blocks.codex, { until: 123, reason: 'quota' })
  JSON.parse(readFileSync(f, 'utf8'))
})

test('meshAvailable：取 layer 2 pass；沒資料回 null', () => {
  assert.equal(meshAvailable(undefined), null)
  const last = { results: [{ layer: 2, a: 'claude', status: 'pass' }, { layer: 2, a: 'agy', status: 'auth' }, { layer: 1, a: 'pi', status: 'pass' }] }
  assert.deepEqual([...meshAvailable(last)], ['claude'])
})

// ── ask.mjs：改派與長結果 ──
import { spawnSync } from 'node:child_process'
import { chmodSync, existsSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { summarize } from './scripts/ask.mjs'

const ASK = fileURLToPath(new URL('./scripts/ask.mjs', import.meta.url))

// 假 CLI：POSIX 寫成可執行的 shebang 腳本；Windows 不能直接執行沒有副檔名的檔，改寫 npm 風格的 .cmd＋.js
function writeShim(f, code) {
  if (process.platform === 'win32') {
    writeFileSync(`${f}.js`, code)
    writeFileSync(`${f}.cmd`, `@"%~dp0\\${basename(f)}.js" %*\r\n`)
    return
  }
  writeFileSync(f, `#!${process.execPath}\n${code}`)
  chmodSync(f, 0o755)
}

// 假 CLI：環境變數 SHIM_<名稱>=quota 時印額度錯誤；=long 時印 20000 字；否則印「answer from <名稱>」
function shimDir() {
  const d = mkdtempSync(join(tmpdir(), 'ad-bin-'))
  for (const name of ['claude', 'codex']) {
    const f = join(d, name)
    writeShim(f, `
const mode = process.env['SHIM_${name.toUpperCase()}']
if (mode === 'quota') { console.log('Error: usage limit reached, try again in 2 hours'); process.exit(1) }
if (mode === 'long') { process.stdout.write('y'.repeat(20000)); process.exit(0) }
console.log('answer from ${name} ' + process.argv.slice(2).join(' '))
`)
  }
  return d
}

function ask(args, env = {}) {
  const work = mkdtempSync(join(tmpdir(), 'ad-ask-'))
  const prompt = join(work, 'p.md'); writeFileSync(prompt, 'question')
  const state = join(work, 'state.json')
  const r = spawnSync(process.execPath, [ASK, '--state', state, '--mesh', join(work, 'none.json'), ...args, prompt], {
    encoding: 'utf8', env: { ...process.env, PATH: shimDir(), ...env } })
  return { ...r, state: readState(state), work, prompt }
}

test('summarize：超過上限只留開頭並指向結果檔', () => {
  const s = summarize('x'.repeat(20000), 16000, 4000, '/r.md')
  assert.ok(s.length < 4200)
  assert.ok(s.endsWith('全文 20000 字元，見 /r.md'))
  assert.equal(summarize('x'.repeat(15000), 16000, 4000, '/r.md'), 'x'.repeat(15000))
})

test('ask：codex 額度用盡 → 封鎖並改派 claude', () => {
  const r = ask(['--type', 'review-critical'], { SHIM_CODEX: 'quota' })
  assert.equal(r.status, 0, r.stderr)
  assert.match(r.stdout, /^\[ask\] 交給 claude（opus／high），理由：review-critical/)
  assert.match(r.stdout, /answer from claude/)
  assert.match(r.stderr, /改派 claude/)
  assert.ok(r.state.blocks.codex.until > Date.now() + 3_500_000)
})

test('ask：所有候選都不能用 → exit 75 並印最早解封時間', () => {
  const r = ask(['--type', 'review-critical'], { SHIM_CODEX: 'quota', SHIM_CLAUDE: 'quota' })
  assert.equal(r.status, 75)
  assert.match(r.stderr, /最早.*解封/)
})

test('ask：--to 不查表，但額度錯誤照樣封鎖', () => {
  const r = ask(['--to', 'codex'], { SHIM_CODEX: 'quota' })
  assert.notEqual(r.status, 0)
  assert.ok(r.state.blocks.codex)
})

test('ask：--model 與 --effort 覆寫查表結果並傳給 CLI', () => {
  const r = ask(['--to', 'claude', '--model', 'sonnet', '--effort', 'low'])
  assert.match(r.stdout, /--model sonnet --effort low/)
})

test('ask：長輸出寫進結果檔，stdout 只放摘要', () => {
  const r = ask(['--to', 'claude'], { SHIM_CLAUDE: 'long' })
  assert.equal(r.status, 0)
  const out = `${r.prompt}.out.md`
  assert.ok(existsSync(out))
  assert.equal(readFileSync(out, 'utf8').length, 20000)
  assert.ok(r.stdout.length < 4500)
  assert.match(r.stdout, /全文 20000 字元/)
})

// ── 背景 worker ──
import { detectEnv, prepare, supervise, running, ghosttyAvailable, ghosttySplitScript, start, statusOf, wait } from './scripts/bg.mjs'
import { parallelLimit } from './scripts/route.mjs'
import { execFileSync } from 'node:child_process'

test('detectEnv：herdr 優先，其次 ghostty，最後背景', () => {
  assert.equal(detectEnv({ HERDR_ENV: '1' }, { ghostty: true }), 'herdr')
  assert.equal(detectEnv({}, { ghostty: true }), 'ghostty')
  assert.equal(detectEnv({}, { ghostty: false }), 'background')
})

test('ghosttyAvailable：只在 macOS 而且在 Ghostty 裡', () => {
  assert.equal(ghosttyAvailable({ TERM_PROGRAM: 'ghostty' }, 'darwin'), true)
  assert.equal(ghosttyAvailable({ TERM_PROGRAM: 'ghostty' }, 'linux'), false)
  assert.equal(ghosttyAvailable({ TERM_PROGRAM: 'herdr' }, 'darwin'), false)
})

test('ghosttySplitScript：引號與反斜線都跳脫，帶工作目錄與環境變數', () => {
  const s = ghosttySplitScript({ cwd: '/a b/"c"', command: 'claude "hi"', env: ['AGENT_DISPATCH_RESULT=/r d/x.md'] })
  assert.match(s, /set initial working directory of cfg to "\/a b\/\\"c\\""/)
  assert.match(s, /set command of cfg to "claude \\"hi\\""/)
  assert.match(s, /set environment variables of cfg to \{"AGENT_DISPATCH_RESULT=\/r d\/x\.md"\}/)
  assert.match(s, /split \(focused terminal of selected tab of front window\) direction right with configuration cfg/)
})

// 假 driver CLI：在 cwd 改一個檔；SHIM_RESULT=0 時不寫結果檔並 exit 1
function driverShim() {
  const d = mkdtempSync(join(tmpdir(), 'ad-drv-'))
  const f = join(d, 'claude')
  writeShim(f, `
const fs = require('node:fs')
fs.writeFileSync('changed.txt', 'by worker')
if (process.env.SHIM_RESULT === '0') { console.log('crashed before writing result'); process.exit(1) }
if (process.env.SHIM_RESULT === 'quota') { console.log('Error: usage limit reached'); process.exit(1) }
if (process.env.SHIM_RESULT === '429') { fs.writeFileSync(process.env.AGENT_DISPATCH_RESULT, '完成'); console.log('handler returns 429 on rate limit'); process.exit(1) }
fs.writeFileSync(process.env.AGENT_DISPATCH_RESULT, '完成：改了 changed.txt')
`)
  return d
}

function tmpRepo() {
  const repo = mkdtempSync(join(tmpdir(), 'ad repo '))
  const git = (...a) => execFileSync('git', ['-C', repo, ...a], { stdio: 'pipe' })
  git('init', '-q'); writeFileSync(join(repo, 'a.txt'), 'a')
  git('add', 'a.txt'); git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'init')
  return repo
}

async function runJob(env) {
  const repo = tmpRepo()
  const root = mkdtempSync(join(tmpdir(), 'ad ws '))
  const prompt = join(root, 'p.md'); writeFileSync(prompt, 'do it')
  const old = { PATH: process.env.PATH, ...Object.fromEntries(Object.keys(env).map(k => [k, process.env[k]])) }
  // shim 放最前面：蓋過真的 claude，git 仍找得到
  Object.assign(process.env, { PATH: driverShim() + delimiter + process.env.PATH, AGENT_DISPATCH_NO_NOTIFY: '1', ...env })
  try {
    const job = prepare({ repo, name: 't1', cli: 'claude', promptFile: prompt, ws: join(root, 't1'), state: join(root, 'state.json') })
    await supervise(job.ws)
    return { repo, job, status: JSON.parse(readFileSync(job.statusFile, 'utf8')) }
  } finally {
    for (const [k, v] of Object.entries(old)) v === undefined ? delete process.env[k] : (process.env[k] = v)
  }
}

test('背景 worker：在 worktree 改檔、寫結果檔，狀態 done，主 repo 不動', async () => {
  const { repo, job, status } = await runJob({})
  assert.equal(status.state, 'done')
  assert.ok(existsSync(join(job.worktree, 'changed.txt')))
  assert.ok(!existsSync(join(repo, 'changed.txt')))
  assert.equal(execFileSync('git', ['-C', repo, 'status', '--porcelain'], { encoding: 'utf8' }), '')
})

test('背景 worker：沒寫結果檔就結束 → failed 並附輸出尾段', async () => {
  const { status } = await runJob({ SHIM_RESULT: '0' })
  assert.equal(status.state, 'failed')
  assert.match(status.tail, /crashed before writing result/)
})

test('背景 worker：已有 4 個執行中 → prepare 拋並行上限', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-par-'))
  for (let i = 0; i < 4; i++) {
    const d = join(root, `j${i}`); mkdirSync(d)
    writeFileSync(join(d, 'status.json'), JSON.stringify({ state: 'running', pid: process.pid }))
  }
  assert.equal(running(root), 4)
  assert.throws(() => prepare({ repo: tmpRepo(), name: 'x', cli: 'claude', promptFile: promptStub(), ws: join(root, 'x'), state: join(root, 's.json') }), /並行已達上限 4/)
})

function promptStub() { const p = join(mkdtempSync(join(tmpdir(), 'ad-p-')), 'p.md'); writeFileSync(p, 'x'); return p }

test('statePath 比照 mesh 的規則', () => {
  assert.equal(statePath({ XDG_STATE_HOME: '/s' }, 'linux'), join('/s', 'agent-dispatch', 'state.json'))
  assert.match(statePath({ LOCALAPPDATA: 'C:\\L' }, 'win32'), /agent-dispatch/)
})

test('buildArgs worker 模式：claude 自動接受編輯，pi 開讀寫工具，codex／agy 同 driver', () => {
  const c = buildArgs('claude', 'worker', 'P')
  assert.deepEqual(c.slice(0, 2), ['-p', 'P'])
  assert.ok(c.join(' ').includes('--permission-mode acceptEdits'))
  assert.ok(c.join(' ').includes('--allowedTools Bash'))
  assert.ok(buildArgs('pi', 'worker', 'P').join(' ').includes('--tools read,bash,edit,write'))
  assert.deepEqual(buildArgs('codex', 'worker', 'P'), buildArgs('codex', 'driver', 'P'))
  assert.deepEqual(buildArgs('agy', 'worker', 'P'), buildArgs('agy', 'driver', 'P'))
})

test('buildArgs worker 模式：claude 把結果檔所在目錄加進可寫範圍（cwd 是 wt/，結果檔在上一層）', () => {
  const c = buildArgs('claude', 'worker', 'P', { resultFile: '/ws/job1/result.md', model: 'haiku' })
  const i = c.indexOf('--add-dir')
  assert.ok(i > 0, c.join(' '))
  assert.equal(c[i + 1], '/ws/job1')
  assert.equal(i + 2, c.length, '--add-dir 吃多個值，放最後才不會吞掉後面的參數')
  assert.ok(!buildArgs('claude', 'worker', 'P').includes('--add-dir'))
  assert.ok(!buildArgs('claude', 'ask', 'P', { resultFile: '/ws/job1/result.md' }).includes('--add-dir'))
})

test('scrubEnv 清掉 AGENT_DISPATCH_RESULT，巢狀派工不會被 Stop hook 當成 worker', () => {
  assert.equal(scrubEnv({ AGENT_DISPATCH_RESULT: '/r.md', PATH: '/b' }).AGENT_DISPATCH_RESULT, undefined)
})

test('背景 worker：結果檔已寫，輸出碰巧有 429 → 仍判 done，不封鎖', async () => {
  const { job, status } = await runJob({ SHIM_RESULT: '429' })
  assert.equal(status.state, 'done')
  assert.equal(readState(job.statusFile.replace(/[^/\\]+[/\\]status\.json$/, 'state.json')).blocks.claude, undefined)
})

test('背景 worker：額度用盡 → 並行上限降 1 並記 1 小時後恢復；到期後回到路由表的值', async () => {
  const t0 = Date.now()
  const { job } = await runJob({ SHIM_RESULT: 'quota' })
  const s = readState(job.statusFile.replace(/[^/\\]+[/\\]status\.json$/, 'state.json'))
  assert.equal(s.maxParallel, 3)
  assert.ok(s.parallelResetAt > t0 + 3_500_000 && s.parallelResetAt <= Date.now() + 3_600_000)
  const routing = loadRouting()
  assert.equal(parallelLimit(s, routing, t0), 3)
  assert.equal(parallelLimit(s, routing, s.parallelResetAt + 1), routing.maxParallel)
  assert.equal(parallelLimit({ blocks: {} }, routing), routing.maxParallel)
})

test('背景 worker：監督程序內出錯 → 寫 failed 與錯誤訊息，不留 running', async () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-sup-'))
  const ws = join(root, 'w'); mkdirSync(ws)
  const statusFile = join(ws, 'status.json')
  writeFileSync(statusFile, JSON.stringify({ state: 'running', pid: process.pid }))
  writeFileSync(join(ws, 'job.json'), JSON.stringify({ name: 'w', cli: 'no-such-cli', timeout: 5, worktree: ws,
    resultFile: join(ws, 'result.md'), statusFile, stateFile: join(root, 's.json'), prompt: 'x' }))
  assert.equal(await supervise(ws), 'failed')
  const st = JSON.parse(readFileSync(statusFile, 'utf8'))
  assert.equal(st.state, 'failed')
  assert.ok(st.error)
})

function deadPid() { return spawnSync(process.execPath, ['-e', '']).pid }

test('statusOf：running 但程序已不在 → failed（supervisor gone）', () => {
  const ws = mkdtempSync(join(tmpdir(), 'ad-st-'))
  writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'running', pid: deadPid() }))
  assert.equal(statusOf(ws).state, 'failed')
  assert.match(statusOf(ws).note, /supervisor gone/)
  writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'running', pid: process.pid }))
  assert.equal(statusOf(ws).state, 'running')
})

test('wait：等到狀態不再是 running；逾時回 timeout', async () => {
  const ws = mkdtempSync(join(tmpdir(), 'ad-wait-'))
  writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'running', pid: process.pid }))
  assert.equal((await wait(ws, { timeoutMs: 300, intervalMs: 50 })).state, 'timeout')
  setTimeout(() => writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'done', pid: process.pid })), 150)
  assert.equal((await wait(ws, { timeoutMs: 5000, intervalMs: 50 })).state, 'done')
})

test('start：狀態檔立刻記監督程序的 pid，不是 start 自己的', async () => {
  const repo = tmpRepo()
  const root = mkdtempSync(join(tmpdir(), 'ad st '))
  const prompt = join(root, 'p.md'); writeFileSync(prompt, 'do it')
  const old = process.env.PATH, oldN = process.env.AGENT_DISPATCH_NO_NOTIFY
  Object.assign(process.env, { PATH: driverShim() + delimiter + old, AGENT_DISPATCH_NO_NOTIFY: '1' })
  try {
    const job = start({ repo, name: 's1', cli: 'claude', promptFile: prompt, ws: join(root, 's1'), state: join(root, 'state.json') })
    assert.notEqual(JSON.parse(readFileSync(job.statusFile, 'utf8')).pid, process.pid)
    assert.equal((await wait(job.ws, { timeoutMs: 20000, intervalMs: 100 })).state, 'done')
  } finally {
    process.env.PATH = old
    oldN === undefined ? delete process.env.AGENT_DISPATCH_NO_NOTIFY : (process.env.AGENT_DISPATCH_NO_NOTIFY = oldN)
  }
})
