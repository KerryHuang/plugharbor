import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { withTtsCache } from './lib/tts-cache.mjs'

function setup() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'tts-cache-'))
  const calls = { n: 0 }
  const stub = async (text, outFile) => {
    calls.n++
    fs.writeFileSync(outFile, Buffer.from('fake-audio:' + text))
  }
  const dir = path.join(root, 'cache')
  const tts = withTtsCache(stub, { dir, provider: 'edge' })
  return { root, dir, calls, tts, out: path.join(root, 'out.mp3') }
}

test('第一次未命中，同文字第二次命中且不再呼叫 tts', async () => {
  const { calls, tts, out } = setup()
  assert.deepEqual(await tts('你好', out, { voice: 'v1' }), { hit: false })
  assert.equal(calls.n, 1)
  fs.rmSync(out)
  assert.deepEqual(await tts('你好', out, { voice: 'v1' }), { hit: true })
  assert.equal(calls.n, 1)
  assert.equal(fs.readFileSync(out, 'utf8'), 'fake-audio:你好')
})

test('改一個字就重新呼叫 tts', async () => {
  const { calls, tts, out } = setup()
  await tts('你好', out, { voice: 'v1' })
  assert.deepEqual(await tts('你們好', out, { voice: 'v1' }), { hit: false })
  assert.equal(calls.n, 2)
})

test('voice 不同視為未命中', async () => {
  const { calls, tts, out } = setup()
  await tts('你好', out, { voice: 'v1' })
  assert.deepEqual(await tts('你好', out, { voice: 'v2' }), { hit: false })
  assert.equal(calls.n, 2)
})

test('空檔視為未命中', async () => {
  const { dir, calls, tts, out } = setup()
  await tts('你好', out, { voice: 'v1' })
  for (const f of fs.readdirSync(dir)) fs.truncateSync(path.join(dir, f), 0)
  assert.deepEqual(await tts('你好', out, { voice: 'v1' }), { hit: false })
  assert.equal(calls.n, 2)
  assert.ok(fs.statSync(out).size > 0)
})
