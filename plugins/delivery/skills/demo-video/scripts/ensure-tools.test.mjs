import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const SH = join(dirname(fileURLToPath(import.meta.url)), 'ensure-tools.sh')
const run = (dir) => spawnSync('bash', [SH, '--dir', dir, '--check'], { encoding: 'utf8' }).stdout
const repo = (gitignore) => {
  const root = mkdtempSync(join(tmpdir(), 'dv-tools-'))
  spawnSync('git', ['init', '-q', root])
  writeFileSync(join(root, '.gitignore'), gitignore)
  return root
}

test('gitignore 缺項時提示相對 repo 根的模式，且不改 .gitignore', () => {
  const root = repo('*.log\n')
  const out = run(join(root, 'video'))
  assert.match(out, /gitignore\s+⚠ 請在 \.gitignore 補上：/)
  for (const p of ['video/**/out/', 'video/.data/', 'video/**/.tts-cache/', 'video/.build/', 'video/node_modules/']) assert.ok(out.includes(p), p)
  assert.equal(readFileSync(join(root, '.gitignore'), 'utf8'), '*.log\n')
})

test('gitignore 補齊後不再提示', () => {
  const root = repo('video/**/out/\nvideo/.data/\nvideo/**/.tts-cache/\nvideo/.build/\nvideo/node_modules/\n')
  assert.doesNotMatch(run(join(root, 'video')), /請在 \.gitignore 補上/)
})

test('不在 git repo 時略過', () => {
  const dir = mkdtempSync(join(tmpdir(), 'dv-tools-nogit-'))
  assert.match(run(join(dir, 'video')), /gitignore\s+⚠ 不在 git repo，略過/)
})
