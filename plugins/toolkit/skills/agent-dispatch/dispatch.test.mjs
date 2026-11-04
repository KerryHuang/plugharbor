import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildArgs, quotaInfo } from '../agent-mesh-check/scripts/clis.mjs'
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, delimiter } from 'node:path'
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
  assert.deepEqual(quotaInfo(`Error: usage limit reached. Resets at ${t}`), { resetAt: Date.parse(t) })
})

test('quotaInfo 沒有重置時間預設 1 小時', () => {
  assert.deepEqual(quotaInfo('rate limit exceeded', 1000), { resetAt: 1000 + 3_600_000 })
})

test('quotaInfo 解析相對時間', () => {
  assert.deepEqual(quotaInfo('quota hit, try again in 15 minutes', 0), { resetAt: 15 * 60_000 })
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

// 假 CLI：環境變數 SHIM_<名稱>=quota 時印額度錯誤；=long 時印 20000 字；否則印「answer from <名稱>」
function shimDir() {
  const d = mkdtempSync(join(tmpdir(), 'ad-bin-'))
  for (const name of ['claude', 'codex']) {
    const f = join(d, name)
    writeFileSync(f, `#!${process.execPath}
const mode = process.env['SHIM_${name.toUpperCase()}']
if (mode === 'quota') { console.log('Error: usage limit reached, try again in 2 hours'); process.exit(1) }
if (mode === 'long') { process.stdout.write('y'.repeat(20000)); process.exit(0) }
console.log('answer from ${name} ' + process.argv.slice(2).join(' '))
`)
    chmodSync(f, 0o755)
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
import { detectEnv, prepare, supervise, running, ghosttyAvailable, ghosttySplitScript } from './scripts/bg.mjs'
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
  writeFileSync(f, `#!${process.execPath}
const fs = require('node:fs')
fs.writeFileSync('changed.txt', 'by worker')
if (process.env.SHIM_RESULT === '0') { console.log('crashed before writing result'); process.exit(1) }
fs.writeFileSync(process.env.AGENT_DISPATCH_RESULT, '完成：改了 changed.txt')
`)
  chmodSync(f, 0o755)
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
