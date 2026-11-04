import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildArgs, quotaInfo } from '../agent-mesh-check/scripts/clis.mjs'
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
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

test('statePath 比照 mesh 的規則', () => {
  assert.equal(statePath({ XDG_STATE_HOME: '/s' }, 'linux'), join('/s', 'agent-dispatch', 'state.json'))
  assert.match(statePath({ LOCALAPPDATA: 'C:\\L' }, 'win32'), /agent-dispatch/)
})
