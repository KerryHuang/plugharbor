import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { mirror } from './sync-codex-mirror.mjs'

test('mirror 不刪 plugharbor install-project 複製模式的複本（含 .plugharbor-root）', () => {
  const root = mkdtempSync(join(tmpdir(), 'mirror-'))
  try {
    const src = join(root, 'src'), dest = join(root, 'dest')
    mkdirSync(join(src, 'mine'), { recursive: true })
    writeFileSync(join(src, 'mine', 'SKILL.md'), 'mine')
    mkdirSync(join(dest, 'explore'), { recursive: true })
    writeFileSync(join(dest, 'explore', 'SKILL.md'), 'plugharbor copy')
    writeFileSync(join(dest, 'explore', '.plugharbor-root'), '/clone/plugins/lifecycle')
    mkdirSync(join(dest, 'stale'), { recursive: true })
    writeFileSync(join(dest, 'stale', 'SKILL.md'), 'old mirror')
    mirror(src, dest)
    assert.ok(existsSync(join(dest, 'mine', 'SKILL.md')), '來源的 skill 要鏡像過去')
    assert.ok(existsSync(join(dest, 'explore', 'SKILL.md')), 'plugharbor 複本不能被刪')
    assert.ok(existsSync(join(dest, 'explore', '.plugharbor-root')))
    assert.ok(!existsSync(join(dest, 'stale')), '來源已刪的鏡像副本照舊清掉')
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})
