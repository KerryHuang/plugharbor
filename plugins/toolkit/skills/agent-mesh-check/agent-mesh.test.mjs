import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, chmodSync, rmSync, mkdirSync, existsSync } from 'node:fs'
import { join, delimiter } from 'node:path'
import { tmpdir } from 'node:os'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { CLIS, resolveBin, buildArgs, scrubEnv, run, classify } from './scripts/clis.mjs'
import { pairs, resolveFrom, statePath, diffVersions, callerScript, sweepStale } from './scripts/mesh.mjs'

const ASK = fileURLToPath(new URL('../agent-dispatch/scripts/ask.mjs', import.meta.url))

test('CLIS 固定四個', () => assert.deepEqual(CLIS, ['claude', 'codex', 'agy', 'pi']))

test('resolveBin 找得到可執行檔、找不到回 null', () => {
  const dir = mkdtempSync(join(tmpdir(), 'mesh-bin-'))
  try {
    writeFileSync(join(dir, 'claude'), '#!/bin/sh\n')
    chmodSync(join(dir, 'claude'), 0o755)
    assert.equal(resolveBin('claude', { PATH: dir }, 'darwin'), join(dir, 'claude'))
    assert.equal(resolveBin('codex', { PATH: dir }, 'darwin'), null)
    writeFileSync(join(dir, 'codex.cmd'), '@echo off\n')
    assert.equal(resolveBin('codex', { Path: dir }, 'win32'), join(dir, 'codex.cmd'))
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test('buildArgs 各模式的權限參數', () => {
  const probe = buildArgs('codex', 'probe', 'X')
  assert.ok(probe.includes('--ignore-user-config') && probe.includes('read-only'))
  assert.ok(buildArgs('codex', 'driver', 'X').includes('danger-full-access'))
  const ask = buildArgs('codex', 'ask', 'X')
  assert.ok(ask.includes('read-only') && !ask.includes('--ignore-user-config'))
  assert.ok(buildArgs('pi', 'probe', 'X').includes('--no-tools'))
  assert.ok(buildArgs('agy', 'probe', 'X').includes('--sandbox') && !buildArgs('agy', 'probe', 'X').includes('plan'))
  assert.ok(buildArgs('claude', 'driver', 'X').includes('Bash'))
  for (const c of CLIS) for (const m of ['probe', 'driver', 'ask']) assert.ok(buildArgs(c, m, 'PROMPT').includes('PROMPT'))
})

test('scrubEnv 清掉巢狀 CLI 標記，保留 CODEX_HOME 與 PATH', () => {
  assert.deepEqual(scrubEnv({ CLAUDECODE: '1', CLAUDE_CODE_X: '1', CODEX_THREAD_ID: 't', CODEX_HOME: 'h', PI_X: '1', ANTIGRAVITY_AGENT: '1', HERDR_PANE_ID: 'p', PATH: 'p' }), { CODEX_HOME: 'h', PATH: 'p' })
})

test('classify 判定順序：timeout → 含預期字串 → auth → fail', () => {
  assert.equal(classify({ timedOut: true, out: 'PING-x-ok', code: null }, 'PING-x-ok'), 'timeout')
  assert.equal(classify({ out: 'hdr\nPING-x-ok\ntokens\nPING-x-ok', code: 0 }, 'PING-x-ok'), 'pass')
  assert.equal(classify({ out: 'Please login first', code: 1 }, 'PING-x-ok'), 'auth')
  assert.equal(classify({ out: 'boom', code: 1 }, 'PING-x-ok'), 'fail')
})

test('run 逾時會殺掉子程序', async () => {
  const t = Date.now()
  const r = await run(process.execPath, ['-e', 'setTimeout(()=>{},10000)'], { timeoutMs: 300 })
  assert.equal(r.timedOut, true)
  assert.ok(Date.now() - t < 2000)
})

test('pairs：入口為中心 vs --full', () => {
  const p = pairs(['claude', 'codex', 'pi'], 'pi', false)
  assert.equal(p.length, 4)
  assert.ok(p.some(([a, b]) => a === 'pi' && b === 'claude'))
  assert.ok(p.some(([a, b]) => a === 'claude' && b === 'pi'))
  assert.equal(pairs(CLIS, null, true).length, 12)
  assert.deepEqual(pairs(['claude'], 'pi', false), [])
})

test('環境標記判斷入口與 statePath', () => {
  const det = env => resolveFrom(null, env).from
  assert.equal(det({ CLAUDECODE: '1' }), 'claude')
  assert.equal(det({}), null)
  assert.equal(det({ PI_CODING_AGENT: 'true' }), 'pi')
  assert.equal(det({ ANTIGRAVITY_AGENT: '1' }), 'agy')
  assert.equal(det({ CODEX_THREAD_ID: 't' }), 'codex')
  assert.equal(det({ CLAUDECODE: '1', PI_CODING_AGENT: 'true' }), null)
  assert.ok(statePath({ LOCALAPPDATA: 'C:\\Users\\k\\AppData\\Local' }, 'win32').startsWith('C:\\Users\\k\\AppData\\Local'))
  assert.equal(statePath({ XDG_STATE_HOME: '/x' }, 'darwin'), join('/x', 'agent-mesh', 'last.json'))
})

test('resolveFrom：單一標記蓋過自報，多個標記才聽 --from', () => {
  assert.equal(resolveFrom('claude', { PI_CODING_AGENT: 'true' }).from, 'pi')
  assert.match(resolveFrom('claude', { PI_CODING_AGENT: 'true' }).note, /改用 pi/)
  assert.equal(resolveFrom('pi', { CLAUDECODE: '1', PI_CODING_AGENT: 'true' }).from, 'pi')
  assert.equal(resolveFrom(null, { CLAUDECODE: '1', PI_CODING_AGENT: 'true' }).from, null)
  assert.equal(resolveFrom('codex', {}).from, 'codex')
})

test('diffVersions 只列有變的', () => {
  assert.deepEqual(diffVersions({ codex: '0.163', pi: '1.4' }, { codex: '0.170', pi: '1.4' }), [{ cli: 'codex', from: '0.163', to: '0.170' }])
  assert.deepEqual(diffVersions(null, { codex: '1' }), [])
})

test('ask.mjs 未知的對象名稱回 2', () => {
  const r = spawnSync(process.execPath, [ASK, '--to', 'nosuchcli', 'x'], { encoding: 'utf8' })
  assert.equal(r.status, 2)
})

test('ask.mjs 對 PATH 上找不到的 CLI 回 127', () => {
  const dir = mkdtempSync(join(tmpdir(), 'mesh-ask-'))
  try {
    const r = spawnSync(process.execPath, [ASK, '--to', 'claude', join(dir, 'missing.md')], { encoding: 'utf8', env: { ...process.env, PATH: dir + delimiter } })
    assert.equal(r.status, 127)
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test('callerScript 產生可執行的 B 呼叫腳本，路徑與 prompt 含引號也安全', { skip: process.platform === 'win32' }, () => {
  const dir = mkdtempSync(join(tmpdir(), "mesh call '"))
  try {
    // 假的 B：印出收到的 prompt（pi 的 probe 參數是 -p <prompt> ...）
    const fake = join(dir, 'fake-pi')
    writeFileSync(fake, '#!/usr/bin/env node\nprocess.stdout.write(process.argv[3])\n')
    chmodSync(fake, 0o755)
    const file = join(dir, 'call.mjs')
    writeFileSync(file, callerScript(fake, 'pi', `say "it's" ok`, 10000))
    const r = spawnSync(process.execPath, [file], { encoding: 'utf8' })
    assert.equal(r.status, 0, r.stderr)
    assert.equal(r.stdout, `say "it's" ok`)
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

test('sweepStale 只清超過一小時的 agent-mesh- 殘留', () => {
  const dir = mkdtempSync(join(tmpdir(), 'mesh-sweep-'))
  try {
    for (const n of ['agent-mesh-old', 'other-old']) mkdirSync(join(dir, n))
    sweepStale(dir, Date.now())
    assert.equal(existsSync(join(dir, 'agent-mesh-old')), true)
    sweepStale(dir, Date.now() + 2 * 3_600_000)
    assert.equal(existsSync(join(dir, 'agent-mesh-old')), false)
    assert.equal(existsSync(join(dir, 'other-old')), true)
  } finally { rmSync(dir, { recursive: true, force: true }) }
})
