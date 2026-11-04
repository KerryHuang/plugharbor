import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildArgs, quotaInfo } from '../agent-mesh-check/scripts/clis.mjs'

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
