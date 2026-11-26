import { test } from 'node:test'
import assert from 'node:assert/strict'
import { CLIS, buildArgs, quotaInfo, run, scrubEnv, resolveBin, cliEnv, blockInfo, hasKeyCmd } from '../agent-mesh-check/scripts/clis.mjs'
import { mkdtempSync, writeFileSync, readFileSync, utimesSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, delimiter, basename, dirname } from 'node:path'
import { loadRouting, readState, writeState, blockCli, meshAvailable, candidates, needsCrossReview, reviewer, statePath } from './scripts/route.mjs'

const has = (args, ...seq) => {
  const i = args.indexOf(seq[0])
  return i >= 0 && seq.every((s, k) => args[i + k] === s)
}

test('buildArgs 不給 opts 時與既有輸出相同', () => {
  assert.deepEqual(buildArgs('claude', 'ask', 'p'), ['-p', 'p', '--tools', 'Read,Grep,Glob'])
  assert.deepEqual(buildArgs('codex', 'ask', 'p'), ['exec', '--ephemeral', '--skip-git-repo-check', '-s', 'read-only', 'p'])
  assert.deepEqual(buildArgs('agy', 'ask', 'p'), ['-p', 'p', '--sandbox', '--disable-slash-commands'])
  assert.deepEqual(buildArgs('pi', 'ask', 'p'), ['-p', 'p', '--tools', 'read,grep,find,ls', '--no-mcp', '--no-session'])
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
  assert.deepEqual(quotaInfo('Error: quota hit, try again in 15 minutes', 0), { resetAt: 15 * 60_000 })
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

test('quotaInfo：workspace 沒額度（要人儲值）沒有重置時間時封鎖 24 小時', () => {
  const out = 'ERROR: Your workspace is out of credits. Ask your workspace owner to refill in order to continue.'
  assert.deepEqual(quotaInfo(out, 1000), { resetAt: 1000 + 24 * 3_600_000 })
})

test('quotaInfo：沒額度但有給重置時間時照重置時間', () => {
  assert.deepEqual(quotaInfo('Error: insufficient credits, try again in 30 minutes', 0), { resetAt: 30 * 60_000 })
})

test('quotaInfo 正常輸出回 null', () => {
  assert.equal(quotaInfo('all good'), null)
})

// ── claude-api：同一支 claude、改用 API key 計費 ──
const KEY_CMD = 'AGENT_DISPATCH_CLAUDE_API_KEY_CMD'

test('quotaInfo：API 額度不足（credit balance is too low）封鎖 24 小時', () => {
  const out = 'API Error: 400 Your credit balance is too low to access the Anthropic API'
  assert.deepEqual(quotaInfo(out, 1000), { resetAt: 1000 + 24 * 3_600_000 })
})

test('quotaInfo：claude 實際輸出單行 "Credit balance is too low"（沒有 error 字樣）→ 封鎖 24 小時', () => {
  assert.deepEqual(quotaInfo('Credit balance is too low', 1000), { resetAt: 1000 + 24 * 3_600_000 })
  assert.deepEqual(blockInfo('claude-api', 'Credit balance is too low\n', 1000), { resetAt: 1000 + 24 * 3_600_000 })
})

test('quotaInfo：too low 沒有 credit／quota 字樣 → 不封鎖', () => {
  assert.equal(quotaInfo('warning: the font size is too low', 1000), null)
  assert.equal(blockInfo('claude-api', 'volume too low', 1000), null)
})

test('blockInfo：claude-api 的 "Your ANTHROPIC_API_KEY belongs to a disabled organization" → 封鎖 24 小時；claude 不封', () => {
  const out = 'Your ANTHROPIC_API_KEY belongs to a disabled organization · Update or unset the environment variable'
  assert.deepEqual(blockInfo('claude-api', out, 1000), { resetAt: 1000 + 24 * 3_600_000 })
  assert.equal(blockInfo('claude', out, 1000), null)
})

test('hasKeyCmd：有值且 trim 後非空才算有設', () => {
  assert.equal(hasKeyCmd({}), false)
  assert.equal(hasKeyCmd({ [KEY_CMD]: '' }), false)
  assert.equal(hasKeyCmd({ [KEY_CMD]: '  \t ' }), false)
  assert.equal(hasKeyCmd({ [KEY_CMD]: 'echo k' }), true)
})

test('key 來源只有空白：到處都視為沒設（claude 保留繼承的 key、claude-api 不可解析、候選排除 claude-api）', () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-ws-'))
  writeFileSync(join(d, 'claude'), '#!/bin/sh\n'); chmodSync(join(d, 'claude'), 0o755)
  const env = { PATH: d, ANTHROPIC_API_KEY: 'sk-mine', [KEY_CMD]: '  ' }
  assert.equal(resolveBin('claude-api', env), null)
  assert.equal(cliEnv('claude', env).ANTHROPIC_API_KEY, 'sk-mine')
  assert.equal(cliEnv('claude-api', env), null)
  const routing = loadRouting()
  for (const tier of ['standard', 'cheap', 'top'])
    assert.ok(!candidates({ tier, routing, state: { blocks: {} }, available: null, now: 0, env }).some(c => c.cli === 'claude-api'), tier)
})

test('buildArgs claude-api 與 claude 相同', () => {
  for (const m of ['probe', 'driver', 'ask', 'worker']) {
    const o = { model: 'opus', effort: 'high', resultFile: '/tmp/x/r.md' }
    assert.deepEqual(buildArgs('claude-api', m, 'P', o), buildArgs('claude', m, 'P', o))
  }
})

test('resolveBin claude-api：沒設 key 來源回 null（即使 PATH 上有同名執行檔）', () => {
  const d = mkdtempSync(join(tmpdir(), 'cabin-'))
  for (const n of ['claude', 'claude-api']) { writeFileSync(join(d, n), '#!/bin/sh\n'); chmodSync(join(d, n), 0o755) }
  assert.equal(resolveBin('claude-api', { PATH: d }), null)
  assert.equal(resolveBin('claude-api', { PATH: d, [KEY_CMD]: '' }), null)
})

test('resolveBin claude-api：有設時回 claude 的路徑，不是同名的 claude-api 包裝', () => {
  const d = mkdtempSync(join(tmpdir(), 'cabin-'))
  for (const n of ['claude', 'claude-api']) { writeFileSync(join(d, n), '#!/bin/sh\n'); chmodSync(join(d, n), 0o755) }
  assert.equal(resolveBin('claude-api', { PATH: d, [KEY_CMD]: 'echo k' }), join(d, 'claude'))
})

test('resolveBin claude-api：platform 傳給 claude 的查找', () => {
  const d = mkdtempSync(join(tmpdir(), 'cabin-'))
  writeFileSync(join(d, 'claude.cmd'), '')
  assert.equal(resolveBin('claude-api', { PATH: d, [KEY_CMD]: 'echo k' }, 'win32'), join(d, 'claude.cmd'))
})

test('cliEnv claude-api：key 指令輸出 "sk-test\n" → 設 ANTHROPIC_API_KEY，不留 AUTH_TOKEN 與 key 指令', () => {
  const e = cliEnv('claude-api', { PATH: '/bin', ANTHROPIC_AUTH_TOKEN: 'oauth', [KEY_CMD]: 'echo sk-test' })
  assert.equal(e.ANTHROPIC_API_KEY, 'sk-test')
  assert.equal(e.ANTHROPIC_AUTH_TOKEN, undefined)
  assert.equal(e[KEY_CMD], undefined)
  assert.equal(e.PATH, '/bin')
})

test('cliEnv claude-api：指令 exit 1、只印空白、逾時、沒設都回 null', () => {
  const base = { PATH: process.env.PATH }
  assert.equal(cliEnv('claude-api', { ...base, [KEY_CMD]: 'echo leaked; exit 1' }), null)
  assert.equal(cliEnv('claude-api', { ...base, [KEY_CMD]: 'echo "   "' }), null)
  const t0 = Date.now()
  assert.equal(cliEnv('claude-api', { ...base, [KEY_CMD]: 'sleep 30' }, { timeoutMs: 500 }), null)
  assert.ok(Date.now() - t0 < 10_000)
  assert.equal(cliEnv('claude-api', base), null)
})

test('cliEnv claude：有設 key 來源時刪掉繼承的 ANTHROPIC_API_KEY 與 ANTHROPIC_AUTH_TOKEN', () => {
  const e = cliEnv('claude', { ANTHROPIC_API_KEY: 'k', ANTHROPIC_AUTH_TOKEN: 't', HOME: '/h', [KEY_CMD]: 'echo x' })
  assert.deepEqual(e, { HOME: '/h' })
})

test('cliEnv claude：沒設 key 來源時保留 ANTHROPIC_API_KEY', () => {
  const e = cliEnv('claude', { ANTHROPIC_API_KEY: 'k', ANTHROPIC_AUTH_TOKEN: 't' })
  assert.deepEqual(e, { ANTHROPIC_API_KEY: 'k', ANTHROPIC_AUTH_TOKEN: 't' })
})

test('cliEnv 其他 CLI：不留 key 指令，其餘等同 scrubEnv', () => {
  const env = { ANTHROPIC_API_KEY: 'k', GH_TOKEN: 'g', [KEY_CMD]: 'echo x' }
  assert.deepEqual(cliEnv('codex', env), { ANTHROPIC_API_KEY: 'k' })
})

test('blockInfo：claude-api 尾段 "Invalid API key" → 封鎖 24 小時', () => {
  assert.deepEqual(blockInfo('claude-api', 'Invalid API key · Fix external API key', 1000), { resetAt: 1000 + 24 * 3_600_000 })
})

test('blockInfo：claude 同樣輸出 → null', () => {
  assert.equal(blockInfo('claude', 'Invalid API key · Fix external API key', 1000), null)
})

test('blockInfo：Invalid API key 只出現在前段、尾 20 行沒有 → null', () => {
  const out = ['Invalid API key', ...Array.from({ length: 25 }, (_, i) => `line ${i}`)].join('\n')
  assert.equal(blockInfo('claude-api', out, 1000), null)
})

test('blockInfo：額度錯誤優先照 quotaInfo', () => {
  assert.deepEqual(blockInfo('claude-api', 'Error: rate limit reached, try again in 5 minutes', 0), { resetAt: 300_000 })
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

const withKey = { AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'echo k' }
const pick = (tier, env) => candidates({ tier, routing, state: none, available: null, now: 0, env })

test('routing：standard 與 cheap 的 claude-api 緊接在 claude 之前，model/effort 相同', () => {
  for (const tier of ['standard', 'cheap']) {
    const list = routing.tiers[tier]
    const i = list.findIndex(c => c.cli === 'claude-api')
    assert.ok(i >= 0, tier)
    assert.equal(list[i + 1].cli, 'claude')
    assert.equal(list[i].model, list[i + 1].model)
    assert.equal(list[i].effort, list[i + 1].effort)
  }
})

test('routing：top 的 claude-api 緊接在 claude 之後，family 為 anthropic', () => {
  const list = routing.tiers.top
  const i = list.findIndex(c => c.cli === 'claude')
  assert.equal(list[i + 1].cli, 'claude-api')
  assert.equal(list[i + 1].model, list[i].model)
  assert.equal(list[i + 1].effort, list[i].effort)
  assert.equal(routing.family['claude-api'], 'anthropic')
})

test('reviewer(claude-api) 不挑 claude 或 pi（同家族）', () => {
  const r = reviewer({ author: 'claude-api', routing, state: none, available: null, now: 0, env: withKey })
  assert.equal(r.cli, 'codex'); assert.equal(r.crossFamily, true)
  const s = reviewer({ author: 'claude-api', routing, state: { blocks: { codex: { until: 100 } } }, available: null, now: 0, env: withKey })
  assert.equal(s.cli, 'agy'); assert.equal(s.crossFamily, true)
})

test('candidates：沒設 key 來源時不含 claude-api，結果與改動前相同（standard／cheap／top 三級）', () => {
  for (const env of [{}, { AGENT_DISPATCH_CLAUDE_API_KEY_CMD: '' }])
    for (const tier of ['standard', 'cheap', 'top']) {
      const c = pick(tier, env).map(x => x.cli)
      assert.ok(!c.includes('claude-api'), tier)
      assert.deepEqual(c, routing.tiers[tier].map(x => x.cli).filter(x => x !== 'claude-api'))
      assert.equal(c.length, 4)
    }
})

test('candidates：有設時含 claude-api', () => {
  for (const tier of ['standard', 'cheap', 'top']) assert.ok(pick(tier, withKey).some(x => x.cli === 'claude-api'), tier)
})

test('reviewer：沒設 key 來源、author codex、claude 被封鎖 → 不挑 claude-api', () => {
  const state = { blocks: { claude: { until: 100 } } }
  const r = reviewer({ author: 'codex', routing, state, available: null, now: 0, env: {} })
  assert.notEqual(r.cli, 'claude-api'); assert.notEqual(r.cli, 'claude')
  const r2 = reviewer({ author: 'codex', routing, state, available: new Set(['codex', 'claude-api', 'pi']), now: 0, env: {} })
  assert.equal(r2.cli, 'pi')
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

test('reviewer 退回同家：預設 sonnet／high，final 才維持 top 等級', () => {
  const avail = new Set(['claude', 'pi'])
  const s = reviewer({ author: 'claude', routing, state: none, available: avail, now: 0 })
  assert.equal(s.crossFamily, false); assert.match(s.model, /sonnet/); assert.equal(s.effort, 'high')
  const f = reviewer({ author: 'claude', routing, state: none, available: avail, now: 0, final: true })
  assert.equal(f.crossFamily, false); assert.match(f.model, /opus/)
  const x = reviewer({ author: 'claude', routing, state: none, available: null, now: 0 })
  assert.equal(x.cli, 'codex'); assert.equal(x.effort, 'high')  // 跨家族不受影響
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

test('meshAvailable：只排除第 2 層明確沒過的；結果裡沒有的（之後才裝）視為可用；沒資料回 null', () => {
  assert.equal(meshAvailable(undefined), null)
  const last = { results: [{ layer: 2, a: 'claude', status: 'pass' }, { layer: 2, a: 'agy', status: 'auth' }, { layer: 1, a: 'pi', status: 'skip' }] }
  assert.deepEqual([...meshAvailable(last)].sort(), ['claude', 'claude-api', 'codex', 'pi'])
})

// ── ask.mjs：改派與長結果 ──
import { spawnSync } from 'node:child_process'
import { chmodSync, existsSync, mkdirSync, renameSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { summarize, fmt } from './scripts/ask.mjs'

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
if (mode === 'stall') { console.log('plan: reading files'); setTimeout(() => {}, 30000); return }
if (mode === 'chatty') { let n = 0; const t = setInterval(() => { console.log('tick ' + (++n)); if (n === 5) { clearInterval(t) } }, 300); return }
if (mode === 'long') { process.stdout.write('y'.repeat(20000)); process.exit(0) }
if (mode === 'log') {  // codex exec：stderr 是整段執行紀錄，-o 指定的檔只放最後答案
  const i = process.argv.indexOf('-o')
  if (i > 0) require('node:fs').writeFileSync(process.argv[i + 1], 'final answer')
  process.stderr.write('hook log '.repeat(3000)); console.log('final answer'); process.exit(0)
}
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

// 假 claude（key 驗證）：環境有 ANTHROPIC_API_KEY=sk-bad 時印 Invalid API key 並 exit 1；沒有時印 ok。PATH 只放這個目錄，不會叫到真的 agy／codex
function keyShimDir() {
  const d = mkdtempSync(join(tmpdir(), 'ad-key-'))
  writeShim(join(d, 'claude'), `
if (process.env.ANTHROPIC_API_KEY === 'sk-bad') { console.log('Invalid API key'); process.exit(1) }
console.log('ok')
`)
  return process.platform === 'win32' ? d + delimiter + process.env.PATH : d
}

test('ask：claude-api key 失效 → 封鎖 24 小時（auth）並改派 claude，claude 拿不到 key', () => {
  const r = ask(['--type', 'docs'], { PATH: keyShimDir(), AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'echo sk-bad', ANTHROPIC_API_KEY: 'sk-bad' })
  assert.equal(r.status, 0, r.stderr)
  assert.match(r.stdout, /\[ask\] 交給 claude（/)
  assert.match(r.stdout, /ok/)
  assert.match(r.stderr, /改派 claude/)
  assert.equal(r.state.blocks['claude-api'].reason, 'auth')
  assert.ok(r.state.blocks['claude-api'].until > Date.now() + 23 * 3_600_000)
  assert.ok(!(r.stdout + r.stderr).includes('sk-bad'))
})

test('ask：claude-api 取 key 失敗 → 封鎖 1 小時（key）、略過並改派 claude', () => {
  const r = ask(['--type', 'docs'], { PATH: keyShimDir(), AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'exit 1' })
  assert.equal(r.status, 0, r.stderr)
  assert.match(r.stderr, /claude-api 取 key 失敗，略過/)
  assert.match(r.stdout, /\[ask\] 交給 claude（/)
  assert.equal(r.state.blocks['claude-api'].reason, 'key')
  const left = r.state.blocks['claude-api'].until - Date.now()
  assert.ok(left > 59 * 60_000 && left <= 3_600_000, String(left))
})

test('ask：--to claude-api 沒設 key 來源 → exit 127 並說明', () => {
  const r = ask(['--to', 'claude-api'], { PATH: keyShimDir(), AGENT_DISPATCH_CLAUDE_API_KEY_CMD: '' })
  assert.equal(r.status, 127)
  assert.match(r.stderr, /AGENT_DISPATCH_CLAUDE_API_KEY_CMD/)
})

test('ask：--to claude-api 取 key 失敗 → exit 127', () => {
  const r = ask(['--to', 'claude-api'], { PATH: keyShimDir(), AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'exit 1' })
  assert.equal(r.status, 127)
  assert.match(r.stderr, /取 key 失敗/)
})

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

test('ask：codex 只回最後答案，執行紀錄另存（產品化 session 2026-11-14 結果檔 39 萬字元）', () => {
  const r = ask(['--to', 'codex'], { SHIM_CODEX: 'log' })
  assert.equal(r.status, 0, r.stderr)
  assert.match(r.stdout, /final answer/)
  assert.doesNotMatch(r.stdout, /hook log/)
  assert.match(r.stdout, /執行紀錄 \d+ 字元，見 .*p\.md\.out\.md/)
  assert.match(readFileSync(`${r.prompt}.out.md`, 'utf8'), /hook log/)
  const ans = readFileSync(`${r.prompt}.answer.md`, 'utf8')
  assert.match(ans, /final answer/)
  assert.doesNotMatch(ans, /hook log/)
})

test('buildArgs：codex 給 lastFile 時加 -o，仍在 prompt 之前', () => {
  const a = buildArgs('codex', 'ask', 'p', { lastFile: '/t/last.md' })
  assert.ok(has(a, '-o', '/t/last.md'))
  assert.equal(a.at(-1), 'p')
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
import { detectEnv, prepare, supervise, running, ghosttyAvailable, ghosttySplitScript, start, statusOf, wait, workerEnv } from './scripts/bg.mjs'
import { parallelLimit } from './scripts/route.mjs'
import { execFileSync } from 'node:child_process'

test('detectEnv：herdr 優先，其次 ghostty，最後背景', () => {
  assert.equal(detectEnv({ HERDR_ENV: '1', HERDR_PANE_ID: 'w:p1' }, { ghostty: true }), 'herdr')
  assert.equal(detectEnv({ HC_TERMINAL_ID: 't1' }, { ghostty: true }), 'herdr')
  assert.equal(detectEnv({ HERDR_ENV: '1' }, { ghostty: true }), 'ghostty')
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
  const body = `
const fs = require('node:fs')
fs.writeFileSync('changed.txt', 'by worker')
if (process.env.SHIM_ARGS) fs.appendFileSync(process.env.SHIM_ARGS, JSON.stringify(process.argv.slice(2)) + '\\n')
if (process.env.SHIM_RESULT === 'api-quota' && process.env.ANTHROPIC_API_KEY) { console.log('Credit balance is too low'); process.exit(1) }
if (process.env.SHIM_RESULT === 'no-agent' && process.argv.includes('--agent')) { console.log("--agent 'x:y' not found. Available agents: claude"); process.exit(1) }
if (process.env.SHIM_RESULT === 'no-session' && process.argv.includes('--resume')) { console.log('No conversation found with session ID: x'); process.exit(1) }
if (process.env.SHIM_RESULT === 'push') {
  const r = require('node:child_process').spawnSync('git', ['push', 'origin', 'HEAD:refs/heads/leak'], { encoding: 'utf8' })
  fs.writeFileSync(process.env.AGENT_DISPATCH_RESULT, JSON.stringify({ push: r.status, gh: process.env.GH_TOKEN ?? null }))
  process.exit(0)
}
if (process.env.SHIM_RESULT === '0') { console.log('crashed before writing result'); process.exit(1) }
if (process.env.SHIM_RESULT === 'quota') { console.log('Error: usage limit reached'); process.exit(1) }
if (process.env.SHIM_RESULT === '429') { fs.writeFileSync(process.env.AGENT_DISPATCH_RESULT, '完成'); console.log('handler returns 429 on rate limit'); process.exit(1) }
fs.writeFileSync(process.env.AGENT_DISPATCH_RESULT, '完成：改了 changed.txt；key=' + (process.env.ANTHROPIC_API_KEY ? 'set' : 'none'))
`
  for (const n of ['claude', 'codex']) writeShim(join(d, n), body)  // codex 同一份：測不支援 --agent 的退路
  return d
}

function tmpRepo() {
  const repo = mkdtempSync(join(tmpdir(), 'ad repo '))
  const git = (...a) => execFileSync('git', ['-C', repo, ...a], { stdio: 'pipe' })
  git('init', '-q'); writeFileSync(join(repo, 'a.txt'), 'a')
  git('add', 'a.txt'); git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'init')
  return repo
}

async function runJob(env, { state, setup, cli = 'claude', type, mesh, agent } = {}) {
  const repo = tmpRepo()
  setup?.(repo)
  const root = mkdtempSync(join(tmpdir(), 'ad ws '))
  const prompt = join(root, 'p.md'); writeFileSync(prompt, 'do it')
  const old = { PATH: process.env.PATH, ...Object.fromEntries(Object.keys(env).map(k => [k, process.env[k]])) }
  // shim 放最前面：蓋過真的 claude，git 仍找得到
  Object.assign(process.env, { PATH: driverShim() + delimiter + process.env.PATH, AGENT_DISPATCH_NO_NOTIFY: '1', ...env })
  try {
    const job = prepare({ repo, name: 't1', cli: type ? undefined : cli, type, agent, mesh: mesh ?? join(root, 'no-mesh.json'), promptFile: prompt, ws: join(root, 't1'), state: state ?? join(root, 'state.json') })
    await supervise(job.ws)
    return { repo, root, job, status: JSON.parse(readFileSync(job.statusFile, 'utf8')) }
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
  // prepare 先檢查 CLI 在不在 PATH；CI 沒裝 claude，放假 CLI 才測得到並行上限
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    assert.throws(() => prepare({ repo: tmpRepo(), name: 'x', cli: 'claude', promptFile: promptStub(), ws: join(root, 'x'), state: join(root, 's.json') }), /並行已達上限 4/)
  } finally { process.env.PATH = old }
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

test('workerEnv：設了 key 來源時 claude 的環境沒有 ANTHROPIC_API_KEY，也沒有 key 指令', () => {
  const e = workerEnv({ PATH: '/b', ANTHROPIC_API_KEY: 'sk-main', AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'echo sk-x' }, '/r.md', 'claude')
  assert.equal(e.ANTHROPIC_API_KEY, undefined)
  assert.equal(e.AGENT_DISPATCH_CLAUDE_API_KEY_CMD, undefined)
  assert.equal(e.AGENT_DISPATCH_RESULT, '/r.md')
})

test('workerEnv：claude-api 取得 key；取 key 失敗回 null', () => {
  assert.equal(workerEnv({ PATH: '/b', AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'echo sk-x' }, '/r.md', 'claude-api').ANTHROPIC_API_KEY, 'sk-x')
  assert.equal(workerEnv({ PATH: '/b', AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'exit 1' }, '/r.md', 'claude-api'), null)
})

test('prepare：claude-api 沒設 key 來源 → 錯誤訊息點名 AGENT_DISPATCH_CLAUDE_API_KEY_CMD', () => {
  const old = process.env.AGENT_DISPATCH_CLAUDE_API_KEY_CMD
  delete process.env.AGENT_DISPATCH_CLAUDE_API_KEY_CMD
  try {
    const root = mkdtempSync(join(tmpdir(), 'ad-nk-'))
    assert.throws(() => prepare({ repo: tmpRepo(), name: 'x', cli: 'claude-api', promptFile: promptStub(), ws: join(root, 'x'), state: join(root, 's.json') }), /AGENT_DISPATCH_CLAUDE_API_KEY_CMD/)
  } finally { if (old !== undefined) process.env.AGENT_DISPATCH_CLAUDE_API_KEY_CMD = old }
})

test('背景 worker：claude-api 取 key 失敗 → failed、tail 寫取 key 失敗，job.json 與 status.json 沒有 key', async () => {
  const { job, status } = await runJob({ AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'exit 1' }, { cli: 'claude-api' })
  assert.equal(status.state, 'failed')
  assert.match(status.tail, /取 key 失敗/)
  const st = readState(job.statusFile.replace(/[^/\\]+[/\\]status\.json$/, 'state.json'))
  assert.equal(st.blocks['claude-api'].reason, 'key')
  assert.ok(st.blocks['claude-api'].until > Date.now() + 59 * 60_000)
  assert.ok(!existsSync(join(job.worktree, 'changed.txt')))  // 沒跑 worker
})

test('背景 worker：claude-api 取得 key 傳給 worker，key 不進 job.json 與 status.json', async () => {
  const { job, status } = await runJob({ AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'echo sk-secret' }, { cli: 'claude-api' })
  assert.equal(status.state, 'done')
  assert.match(readFileSync(job.resultFile, 'utf8'), /key=set/)
  const files = ['job.json', 'status.json', 'log.txt'].map(f => readFileSync(join(job.ws, f), 'utf8')).join('')
  assert.ok(!files.includes('sk-secret'))
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

// ── 審查修正（第 2–12 項）──
const ROUTE = fileURLToPath(new URL('./scripts/route.mjs', import.meta.url))
const branches = repo => execFileSync('git', ['-C', repo, 'branch', '--list', 'dispatch/*'], { encoding: 'utf8' }).trim()

test('buildArgs：prompt 以 - 開頭時，四家各模式組出的 prompt 參數都不以 - 開頭', () => {
  for (const c of CLIS) for (const m of ['probe', 'driver', 'ask', 'worker']) {
    const a = buildArgs(c, m, '---\nname: x\n---')
    const p = a.find(x => x.includes('name: x'))
    assert.ok(p && !p.startsWith('-'), `${c} ${m}: ${JSON.stringify(a)}`)
  }
  assert.equal(buildArgs('claude', 'ask', 'plain')[1], 'plain')
})

test('prepare：prompt 檔以 --- 開頭，worker prompt 不以 - 開頭', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-fm-'))
  const p = join(root, 'p.md'); writeFileSync(p, '---\ntitle: x\n---\nbody')
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    const job = prepare({ repo: tmpRepo(), name: 'fm', cli: 'claude', promptFile: p, ws: join(root, 'fm'), state: join(root, 's.json') })
    const { prompt } = JSON.parse(readFileSync(join(job.ws, 'job.json'), 'utf8'))
    assert.ok(!prompt.startsWith('-'))
    assert.ok(prompt.includes('---\ntitle: x'))
  } finally { process.env.PATH = old }
})

test('scrubEnv 濾掉推送用 token，AGENT_DISPATCH_KEEP_ENV 可放行', () => {
  const env = { GH_TOKEN: 'a', GITHUB_TOKEN: 'b', GITLAB_TOKEN: 'c', GLAB_TOKEN: 'd', PATH: '/b' }
  assert.deepEqual(scrubEnv(env), { PATH: '/b' })
  const kept = scrubEnv({ ...env, AGENT_DISPATCH_KEEP_ENV: 'GH_TOKEN, GLAB_TOKEN' })
  assert.equal(kept.GH_TOKEN, 'a'); assert.equal(kept.GLAB_TOKEN, 'd'); assert.equal(kept.GITHUB_TOKEN, undefined)
})

test('背景 worker：env 沒有 GH_TOKEN，worker 裡的 git push 被擋、bare repo 沒收到', async () => {
  const bare = mkdtempSync(join(tmpdir(), 'ad-bare-'))
  execFileSync('git', ['init', '-q', '--bare', bare])
  const { status, job } = await runJob({ SHIM_RESULT: 'push', GH_TOKEN: 'secret' }, { setup: repo => {
    execFileSync('git', ['-C', repo, 'remote', 'add', 'origin', bare])
    execFileSync('git', ['-C', repo, 'config', 'remote.origin.pushurl', bare])  // 明設 pushurl 也要擋
  } })
  assert.equal(status.state, 'done')
  const r = JSON.parse(readFileSync(job.resultFile, 'utf8'))
  assert.equal(r.gh, null)
  assert.notEqual(r.push, 0)
  assert.equal(execFileSync('git', ['-C', bare, 'for-each-ref'], { encoding: 'utf8' }), '')
})

test('prepare：上層目錄的鎖被占用且未過期 → 拋錯；過期的鎖會被清掉、用完釋放', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-lock-'))
  const lock = join(root, '.agent-dispatch.lock'); mkdirSync(lock)
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    const args = n => ({ repo: tmpRepo(), name: n, cli: 'claude', promptFile: promptStub(), ws: join(root, n), state: join(root, 's.json'), lockWaitMs: 200 })
    assert.throws(() => prepare(args('a')), /鎖/)
    const past = new Date(Date.now() - 120_000); utimesSync(lock, past, past)
    prepare(args('b'))
    assert.ok(!existsSync(lock))
  } finally { process.env.PATH = old }
})

test('writeState：rename 遇到 EPERM／EBUSY 會重試', () => {
  const f = join(mkdtempSync(join(tmpdir(), 'ad-ws-')), 'state.json')
  let n = 0
  const flaky = (a, b) => { if (n++ < 2) throw Object.assign(new Error('busy'), { code: n === 1 ? 'EPERM' : 'EBUSY' }); return renameSync(a, b) }
  writeState(f, { blocks: {}, x: 1 }, { rename: flaky })
  assert.equal(readState(f).x, 1)
  assert.equal(n, 3)
})

test('背景 worker：狀態檔寫不進去也不會把 quota 翻成 failed', async () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-ro-'))
  const notDir = join(d, 'file'); writeFileSync(notDir, 'x')
  const { status } = await runJob({ SHIM_RESULT: 'quota' }, { state: join(notDir, 'state.json') })
  assert.equal(status.state, 'quota')
})

test('statusOf：running 但已超過 startedAt＋timeout＋緩衝 → failed（stale），pid 重用也不會永遠 running', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-stale-'))
  const ws = join(root, 'w'); mkdirSync(ws)
  writeFileSync(join(ws, 'job.json'), JSON.stringify({ timeout: 1 }))
  writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'running', pid: process.pid, startedAt: new Date(Date.now() - 120_000).toISOString() }))
  assert.equal(statusOf(ws).state, 'failed')
  assert.match(statusOf(ws).note, /stale/)
  assert.equal(running(root), 0)
  writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'running', pid: process.pid, startedAt: new Date().toISOString() }))
  assert.equal(statusOf(ws).state, 'running')
})

test('prepare：prompt 檔讀不到或 timeout 不合法 → 拋錯且不留 worktree／分支', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-bad-'))
  const repo = tmpRepo()
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    assert.throws(() => prepare({ repo, name: 'm', cli: 'claude', promptFile: join(root, 'missing.md'), ws: join(root, 'm'), state: join(root, 's.json') }))
    assert.throws(() => prepare({ repo, name: 'n', cli: 'claude', promptFile: promptStub(), ws: join(root, 'n'), state: join(root, 's.json'), timeout: NaN }), /timeout/)
    assert.equal(branches(repo), '')
    assert.ok(!existsSync(join(root, 'm', 'wt')) && !existsSync(join(root, 'n', 'wt')))
  } finally { process.env.PATH = old }
})

test('ask：--timeout 不是正數 → exit 2', () => {
  assert.equal(ask(['--to', 'claude', '--timeout', 'abc']).status, 2)
  assert.equal(ask(['--to', 'claude', '--timeout', '0']).status, 2)
})

test('needsCrossReview：Windows 反斜線路徑也命中', () => {
  assert.equal(needsCrossReview({ paths: ['src\\api\\x.ts'], lines: 1 }, routing), true)
})

test('quotaInfo：尾段談到 credits／quota 但沒有錯誤上下文 → null', () => {
  assert.equal(quotaInfo('Done.\nCredits used: 12\nquota remaining 80%', 0), null)
})

test('quotaInfo：只看最後 20 行', () => {
  assert.equal(quotaInfo('Error: rate limit exceeded\n' + 'ok\n'.repeat(25), 0), null)
  assert.ok(quotaInfo('ok\n'.repeat(25) + 'Error: usage limit reached', 0))
})

test('route.mjs block：未知的 CLI 名稱回 2、不寫狀態', () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-blk-'))
  const r = spawnSync(process.execPath, [ROUTE, 'block', 'nosuch', '2099-01-01T00:00:00Z'], { encoding: 'utf8', env: { ...process.env, XDG_STATE_HOME: d } })
  assert.equal(r.status, 2)
  assert.ok(!existsSync(join(d, 'agent-dispatch', 'state.json')))
})

test('route.mjs pick 印出該類型的候選，濾掉封鎖中的 CLI', () => {
  const d = mkdtempSync(join(tmpdir(), 'pick-'))
  const state = join(d, 'state.json')
  writeFileSync(state, JSON.stringify({ blocks: { codex: { until: Date.now() + 3_600_000 } } }))
  const r = spawnSync(process.execPath, [ROUTE, 'pick', 'review-critical',
    '--state', state, '--mesh', join(d, 'none.json')], { encoding: 'utf8' })
  assert.equal(r.status, 0, r.stderr)
  const list = JSON.parse(r.stdout)
  assert.equal(list[0].cli, 'claude')
  assert.ok(!list.some(c => c.cli === 'codex'))
})

test('route.mjs pick 未知類型 exit 2', () => {
  const r = spawnSync(process.execPath, [ROUTE, 'pick', 'nope'], { encoding: 'utf8' })
  assert.equal(r.status, 2)
})

test('誤把 reviewer 當類型：錯誤訊息列出可用類型並指向 reviewer 子命令', () => {
  const r = spawnSync(process.execPath, [ROUTE, 'pick', 'reviewer'], { encoding: 'utf8' })
  assert.equal(r.status, 2)
  assert.match(r.stderr, /review-critical/)
  assert.match(r.stderr, /route\.mjs reviewer <作者 CLI>/)
})

test('route.mjs reviewer 挑跟作者不同家族的審查者', () => {
  const d = mkdtempSync(join(tmpdir(), 'rev-'))
  const state = join(d, 'state.json')
  writeFileSync(state, JSON.stringify({ blocks: { codex: { until: Date.now() + 3_600_000 } } }))
  const r = spawnSync(process.execPath, [ROUTE, 'reviewer', 'claude', '--state', state, '--mesh', join(d, 'none.json')], { encoding: 'utf8' })
  assert.equal(r.status, 0, r.stderr)
  const got = JSON.parse(r.stdout)
  assert.equal(got.cli, 'agy')
  assert.equal(got.crossFamily, true)
})

test('fmt 印本地時間並標時區（UTC 不標會被誤讀成本地）', () => {
  const tz = process.env.TZ
  try {
    process.env.TZ = 'Asia/Taipei'
    assert.equal(fmt(Date.UTC(2026, 10, 14, 8, 41)), '2026-11-14 16:41（UTC+8）')
    process.env.TZ = 'UTC'
    assert.equal(fmt(Date.UTC(2026, 10, 14, 8, 41)), '2026-11-14 08:41（UTC+0）')
  } finally {
    if (tz === undefined) delete process.env.TZ; else process.env.TZ = tz
  }
})

test('ask：--idle-timeout 連續無輸出 → exit 124、輸出存 .out.md、不改派', () => {
  const r = ask(['--to', 'codex', '--idle-timeout', '1', '--timeout', '20'], { SHIM_CODEX: 'stall' })
  assert.equal(r.status, 124, r.stderr)
  assert.match(r.stderr, /codex 連續 1 秒無輸出，判定卡住，已中斷/)
  assert.match(readFileSync(`${r.prompt}.out.md`, 'utf8'), /plan: reading files/)
})

test('ask：持續有輸出不觸發 --idle-timeout', () => {
  const r = ask(['--to', 'codex', '--idle-timeout', '1', '--timeout', '20'], { SHIM_CODEX: 'chatty' })
  assert.equal(r.status, 0, r.stderr)
  assert.match(r.stdout, /tick 5/)
})

// ── 背景 worker：--type 改派、--worktree、--continue 續派 ──
const argsLog = () => join(mkdtempSync(join(tmpdir(), 'ad-args-')), 'args.jsonl')
const readArgs = f => readFileSync(f, 'utf8').trim().split('\n').map(l => JSON.parse(l))
const KEY = { AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'echo sk-test' }

test('buildArgs worker：claude 系帶 --session-id／--resume，仍在 --add-dir 之前', () => {
  const a = buildArgs('claude-api', 'worker', 'P', { resultFile: '/ws/j/result.md', sessionId: 'S1' })
  assert.ok(has(a, '--session-id', 'S1'))
  assert.equal(a.indexOf('--add-dir'), a.length - 2)
  assert.ok(has(buildArgs('claude', 'worker', 'P', { resume: 'S2' }), '--resume', 'S2'))
  assert.ok(!buildArgs('claude', 'worker', 'P').includes('--session-id'))
})

test('背景 worker --type：claude-api 額度用盡 → 封鎖、改派 claude 做完，status 記實際對象與改派紀錄', async () => {
  const f = argsLog()
  const { job, status, root } = await runJob({ ...KEY, SHIM_RESULT: 'api-quota', SHIM_ARGS: f }, { type: 'implement' })
  assert.match(readFileSync(join(job.ws, 'job.json'), 'utf8'), /"type": "implement"/)
  assert.equal(status.state, 'done')
  assert.equal(status.cli, 'claude')
  assert.deepEqual(status.attempts, [{ cli: 'claude-api', outcome: 'quota' }])
  assert.match(status.line, /^\[bg\] 交給 claude（sonnet／medium），理由：implement；改派自 claude-api（quota）/)
  assert.ok(readState(join(root, 'state.json')).blocks['claude-api'].until > Date.now())
  const [first, second] = readArgs(f)
  assert.ok(first.includes('--session-id') && second.includes('--session-id'))
  assert.notEqual(first[first.indexOf('--session-id') + 1], second[second.indexOf('--session-id') + 1])
  assert.match(second[1], /前一位 worker（claude-api）被額度或 API key 問題中斷/)
  assert.match(readFileSync(join(job.ws, 'log.txt'), 'utf8'), /===== claude-api[\s\S]*===== claude（/)
})

test('背景 worker --to claude-api：額度用盡不改派，回 quota', async () => {
  const { status } = await runJob({ ...KEY, SHIM_RESULT: 'api-quota' }, { cli: 'claude-api' })
  assert.equal(status.state, 'quota')
  assert.equal(status.cli, 'claude-api')
})

test('prepare --type：候選全被濾掉 → NO_CANDIDATE，不建 worktree', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-nc-'))
  const repo = tmpRepo()
  const old = process.env.PATH
  process.env.PATH = mkdtempSync(join(tmpdir(), 'ad-empty-'))
  try {
    assert.throws(() => prepare({ repo, name: 'nc', type: 'implement', promptFile: promptStub(), ws: join(root, 'nc'), state: join(root, 's.json'), mesh: join(root, 'm.json') }),
      e => e.code === 'NO_CANDIDATE')
  } finally { process.env.PATH = old }
  assert.equal(branches(repo), '')
})

test('prepare --worktree：用既有 worktree、不開新分支；不是 worktree 就拋錯', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-ewt-'))
  const repo = tmpRepo()
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    assert.throws(() => prepare({ worktree: root, name: 'x', cli: 'claude', promptFile: promptStub(), ws: join(root, 'x'), state: join(root, 's.json') }), /不是 git worktree/)
    const job = prepare({ worktree: repo, name: 'y', cli: 'claude', promptFile: promptStub(), ws: join(root, 'y'), state: join(root, 's.json') })
    assert.equal(job.worktree, repo)
    assert.equal(branches(repo), '')
  } finally { process.env.PATH = old }
})

async function continueJob(env, prev, extra = {}) {
  const old = { PATH: process.env.PATH, ...Object.fromEntries(Object.keys(env).map(k => [k, process.env[k]])) }
  Object.assign(process.env, { PATH: driverShim() + delimiter + process.env.PATH, AGENT_DISPATCH_NO_NOTIFY: '1', ...env })
  try {
    const job = prepare({ continueFrom: prev.ws, name: 'fix1', promptFile: promptStub(), ws: join(dirname(prev.ws), 'fix1'), state: prev.stateFile, mesh: join(dirname(prev.ws), 'no-mesh.json'), ...extra })
    await supervise(job.ws)
    return { job, status: JSON.parse(readFileSync(job.statusFile, 'utf8')) }
  } finally {
    for (const [k, v] of Object.entries(old)) v === undefined ? delete process.env[k] : (process.env[k] = v)
  }
}

test('背景 worker --continue：同一個 worktree、接續上一輪的 claude session、沿用派工方式', async () => {
  const f = argsLog()
  const { job: prev, status: ps, repo } = await runJob({ SHIM_ARGS: f })
  const { job, status } = await continueJob({ SHIM_ARGS: f }, { ...prev, stateFile: JSON.parse(readFileSync(join(prev.ws, 'job.json'), 'utf8')).stateFile })
  assert.equal(status.state, 'done')
  assert.equal(job.worktree, prev.worktree)
  assert.equal(status.resumed, true)
  assert.equal(status.sessionId, ps.sessionId)
  const second = readArgs(f)[1]
  assert.ok(has(second, '--resume', ps.sessionId) && !second.includes('--session-id'))
  assert.match(branches(repo), /^\+? ?dispatch\/t1$/)  // 沒有多開分支（+ 表示在別的 worktree 檢出）
})

test('背景 worker --continue：session 不見了 → 同一家開新 session 重跑', async () => {
  const f = argsLog()
  const { job: prev } = await runJob({})
  const { status } = await continueJob({ SHIM_RESULT: 'no-session', SHIM_ARGS: f }, { ...prev, stateFile: JSON.parse(readFileSync(join(prev.ws, 'job.json'), 'utf8')).stateFile })
  assert.equal(status.state, 'done')
  assert.equal(status.resumed, false)
  const [a, b] = readArgs(f)
  assert.ok(a.includes('--resume') && b.includes('--session-id'))
})

test('prepare --continue：沒帶 --model／--effort 就沿用上一輪實際跑的；有帶的那一項才覆寫；換 --type 不沿用', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-cme-'))
  const repo = tmpRepo()
  const prev = join(root, 'p'); mkdirSync(prev)
  writeFileSync(join(prev, 'job.json'), JSON.stringify({ type: 'implement', worktree: repo }))
  writeFileSync(join(prev, 'status.json'), JSON.stringify({ state: 'done', cli: 'claude', model: 'opus', effort: 'high' }))
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  const top = (ws, extra = {}) => JSON.parse(readFileSync(join(prepare({ continueFrom: prev, name: 'f', promptFile: promptStub(), ws: join(root, ws), state: join(root, 's.json'), mesh: join(root, 'm.json'), ...extra }).ws, 'job.json'), 'utf8')).candidates.find(c => c.cli === 'claude')
  try {
    assert.deepEqual(top('a'), { cli: 'claude', model: 'opus', effort: 'high' })
    assert.deepEqual(top('b', { effort: 'low' }), { cli: 'claude', model: 'opus', effort: 'low' })
    assert.notEqual(top('c', { type: 'docs' })?.model, 'opus')
  } finally { process.env.PATH = old }
})

test('prepare --continue：上一輪還在跑 → 拋錯', () => {
  const ws = mkdtempSync(join(tmpdir(), 'ad-cr-'))
  writeFileSync(join(ws, 'job.json'), JSON.stringify({ worktree: ws, to: 'claude' }))
  writeFileSync(join(ws, 'status.json'), JSON.stringify({ state: 'running', pid: process.pid }))
  assert.throws(() => prepare({ continueFrom: ws, name: 'f', promptFile: promptStub(), ws: join(ws, 'f') }), /還在跑/)
})

test('prepare：工作目錄已用過（有 result.md／job.json）→ 拋錯；--continue 不能沿用上一輪的 ws', async () => {
  const { job: prev } = await runJob({})
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    assert.throws(() => prepare({ continueFrom: prev.ws, name: 'f', promptFile: promptStub(), ws: prev.ws }), /工作目錄已用過/)
  } finally { process.env.PATH = old }
})

test('prepare --continue：舊版 job.json 只有 cli → 沿用該 cli', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-old-'))
  const repo = tmpRepo()
  const prev = join(root, 'p'); mkdirSync(prev)
  writeFileSync(join(prev, 'job.json'), JSON.stringify({ cli: 'claude', worktree: repo }))
  writeFileSync(join(prev, 'status.json'), JSON.stringify({ state: 'done', cli: 'claude' }))
  const old = process.env.PATH
  process.env.PATH = driverShim() + delimiter + old
  try {
    const job = prepare({ continueFrom: prev, name: 'f', promptFile: promptStub(), ws: join(root, 'f'), state: join(root, 's.json') })
    assert.equal(JSON.parse(readFileSync(join(job.ws, 'job.json'), 'utf8')).to, 'claude')
  } finally { process.env.PATH = old }
})

test('背景 worker --type：claude-api 取 key 失敗且狀態檔寫不進去 → 仍改派下一家做完', async () => {
  const d = mkdtempSync(join(tmpdir(), 'ad-ro2-'))
  const notDir = join(d, 'file'); writeFileSync(notDir, 'x')
  const { status } = await runJob({ AGENT_DISPATCH_CLAUDE_API_KEY_CMD: 'exit 1' }, { type: 'implement', state: join(notDir, 'state.json') })
  assert.equal(status.state, 'done')
  assert.equal(status.cli, 'claude')
  assert.deepEqual(status.attempts, [{ cli: 'claude-api', outcome: 'key' }])
})

// ── --agent 透傳 ──
test('buildArgs worker：claude 系帶 --agent、在 --add-dir 之前；其他模式與其他 CLI 不帶', () => {
  const a = buildArgs('claude', 'worker', 'P', { resultFile: '/ws/j/result.md', agent: 'lifecycle:developer', model: 'sonnet' })
  assert.ok(has(a, '--agent', 'lifecycle:developer'))
  assert.ok(has(a, '--model', 'sonnet'))  // --model 與 --agent 並存，由 CLI 以 --model 為準
  assert.equal(a.indexOf('--add-dir'), a.length - 2)
  assert.ok(!buildArgs('claude', 'worker', 'P').includes('--agent'))
  assert.ok(!buildArgs('claude', 'ask', 'P', { agent: 'x:y' }).includes('--agent'))
  assert.ok(!buildArgs('codex', 'worker', 'P', { agent: 'x:y' }).join(' ').includes('x:y'))
})

test('prepare --agent：格式錯誤在建 worktree 之前就拋錯', () => {
  const root = mkdtempSync(join(tmpdir(), 'ad-ag-'))
  const repo = tmpRepo()
  assert.throws(() => prepare({ repo, name: 'x', cli: 'claude', agent: 'a b;rm', promptFile: promptStub(), ws: join(root, 'x'), state: join(root, 's.json') }), /--agent 格式/)
  assert.equal(branches(repo), '')
})

test('背景 worker --agent：claude 帶 --agent，status 記 agentApplied', async () => {
  const f = argsLog()
  const { status, job } = await runJob({ SHIM_ARGS: f }, { agent: 'lifecycle:developer' })
  assert.equal(status.state, 'done')
  assert.equal(status.agent, 'lifecycle:developer')
  assert.equal(status.agentApplied, true)
  assert.equal(status.agentNote, undefined)
  assert.ok(has(readArgs(f)[0], '--agent', 'lifecycle:developer'))
  assert.match(readFileSync(join(job.ws, 'job.json'), 'utf8'), /"agent": "lifecycle:developer"/)
})

test('背景 worker --agent：codex 不支援 → 不帶旗標、prompt 叫它讀定義檔、status 記說明', async () => {
  const f = argsLog()
  const { status } = await runJob({ SHIM_ARGS: f }, { cli: 'codex', agent: 'lifecycle:developer' })
  assert.equal(status.state, 'done')
  assert.equal(status.agentApplied, false)
  assert.match(status.agentNote, /codex 不支援 --agent/)
  const a = readArgs(f)[0]
  assert.ok(!a.includes('--agent'))
  assert.match(a.at(-1), /Agent 定義是 lifecycle:developer[\s\S]*agents\/developer\.md/)
})

test('背景 worker --continue：resume 時不重帶 --agent（沿用 session、agentApplied 承接）；換 agent 就開新 session', async () => {
  const f = argsLog()
  const { job: prev } = await runJob({ SHIM_ARGS: f }, { agent: 'lifecycle:developer' })
  const stateFile = JSON.parse(readFileSync(join(prev.ws, 'job.json'), 'utf8')).stateFile
  const { status: s1 } = await continueJob({ SHIM_ARGS: f }, { ...prev, stateFile })
  const second = readArgs(f)[1]
  assert.ok(has(second, '--resume', JSON.parse(readFileSync(prev.statusFile, 'utf8')).sessionId) && !second.includes('--agent'))
  assert.equal(s1.agent, 'lifecycle:developer')
  assert.equal(s1.agentApplied, true)
  const { status: s2 } = await continueJob({ SHIM_ARGS: f }, { ...prev, stateFile }, { agent: 'lifecycle:reviewer', ws: join(dirname(prev.ws), 'fix2') })
  const third = readArgs(f)[2]
  assert.ok(has(third, '--agent', 'lifecycle:reviewer') && !third.includes('--resume') && third.includes('--session-id'))
  assert.equal(s2.agent, 'lifecycle:reviewer')
})

test('背景 worker --agent 退路：只影響觸發的那一家，改派的下一家重新嘗試 --agent', async () => {
  const f = argsLog()
  const { status } = await runJob({ SHIM_RESULT: 'no-agent', SHIM_ARGS: f, ...KEY }, { type: 'implement', agent: 'x:y' })
  const calls = readArgs(f)
  assert.ok(calls[0].includes('--agent') && !calls[1].includes('--agent'))
  assert.equal(status.state, 'done')
})

test('背景 worker --agent：claude 找不到該 Agent 定義 → 同一家去掉 --agent、prompt 退路、status 記說明', async () => {
  const f = argsLog()
  const { status } = await runJob({ SHIM_RESULT: 'no-agent', SHIM_ARGS: f }, { agent: 'x:y' })
  assert.equal(status.state, 'done')
  assert.equal(status.agentApplied, false)
  assert.match(status.agentNote, /找不到該 Agent 定義/)
  const [first, second] = readArgs(f)
  assert.ok(first.includes('--agent') && !second.includes('--agent'))
  assert.match(second[1], /Agent 定義是 x:y/)
})
