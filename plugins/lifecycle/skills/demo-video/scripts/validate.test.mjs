import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { formatScriptErrors, validateScript } from './lib/validate-script.mjs'

const ENGINE = fileURLToPath(new URL('./demo-video.mjs', import.meta.url))
const ok = () => ({ base: 'http://127.0.0.1/', segments: [{ text: '一句旁白。', run: async () => {} }] })
const paths = (cfg, opts) => validateScript(cfg, opts).map((e) => e.path)

test('合法腳本沒有錯誤', () => {
  assert.deepEqual(validateScript(ok()), [])
})

test('沒有 default export 時只報這一條', () => {
  assert.deepEqual(paths(undefined), ['export default'])
})

test('一次列出全部錯誤，而且每條都有範例', () => {
  const errs = validateScript({ name: 'a/b', segments: [{ text: '' }, { text: '好', run: 'x' }], viewport: { width: 1000, height: 1000 }, tts: 'x', setup: 1 })
  assert.deepEqual(errs.map((e) => e.path), ['name', 'base', 'viewport', 'tts', 'setup', 'segments[0].text', 'segments[0].run', 'segments[1].run'])
  assert.ok(errs.every((e) => e.message && e.example))
})

test('--base 可以代替腳本的 base', () => {
  const cfg = ok()
  delete cfg.base
  assert.deepEqual(paths(cfg), ['base'])
  assert.deepEqual(paths(cfg, { base: 'http://127.0.0.1/' }), [])
})

test('segments 不是非空陣列時報一條', () => {
  assert.deepEqual(paths({ ...ok(), segments: [] }), ['segments'])
  assert.deepEqual(paths({ ...ok(), segments: 'x' }), ['segments'])
})

test('輸出格式：路徑、範例、總數', () => {
  const text = formatScriptErrors(validateScript({ segments: [] }))
  assert.match(text, /^✗ base：/m)
  assert.match(text, /^ {2}正確範例：/m)
  assert.match(text, /^✗ 2 個錯誤；沒有開始建置$/m)
})

test('build 遇到壞腳本：列全部錯誤、exit 1、不動輸出目錄、沒有 stack trace', () => {
  const dir = mkdtempSync(join(tmpdir(), 'demo-video-validate-'))
  const script = join(dir, 'video.mjs')
  writeFileSync(script, "export default { segments: [{ text: '' }] }\n")
  const out = join(dir, 'out')
  mkdirSync(join(out, 'voice'), { recursive: true })
  writeFileSync(join(out, 'voice', 'keep.mp3'), 'x')
  const r = spawnSync(process.execPath, [ENGINE, 'build', script, '--out', out], { encoding: 'utf8' })
  assert.equal(r.status, 1)
  assert.match(r.stderr, /^✗ base：/m)
  assert.match(r.stderr, /^✗ segments\[0\]\.text：/m)
  assert.doesNotMatch(r.stderr, /\n\s+at /)
  assert.ok(existsSync(join(out, 'voice', 'keep.mp3')), '驗證失敗時不該清輸出目錄')
})
