import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { findEnv, loadEnv, startEnv } from './lib/env.mjs'

const CLI = join(dirname(fileURLToPath(import.meta.url)), 'demo-video.mjs')
const APP = `require('http').createServer((q,r)=>{r.statusCode=q.url==='/ready'?200:404;r.end('ok')}).listen(Number(process.env.PORT),'127.0.0.1')`
const tmp = () => mkdtempSync(join(tmpdir(), 'dv-env-'))
const alive = (pid) => { try { process.kill(pid, 0); return true } catch (e) { return e.code !== 'ESRCH' } }
const recipe = (start, extra = {}) => ({ build() {}, reset() {}, start: { portEnv: 'PORT', readyPath: '/ready', ...start }, ...extra })
const listen = (port, host = '127.0.0.1') => new Promise((res) => {
  const s = createServer((q, r) => r.end('mine')).listen(port, host, () => res(s))
})
const ctx = () => { const root = tmp(); const logs = []; return { root, logs, opts: { videoRoot: root, outDir: join(root, 'out'), log: (m) => logs.push(m) } } }

test('預設埠被佔用時改用空埠', async () => {
  const { logs, opts } = ctx()
  const mine = createServer((q, r) => { r.statusCode = 200; r.end('mine') })
  await new Promise((r) => mine.listen(0, '127.0.0.1', r))
  const P = mine.address().port
  const h = await startEnv(recipe({ port: P, cmd: [process.execPath, '-e', APP] }), opts)
  try {
    const m = logs.join('\n').match(/就緒：pid (\d+)，埠 (\d+)/)
    assert.ok(m)
    assert.notEqual(Number(m[2]), P)
    assert.equal(Number(m[1]), h.pid)
    await h.stop()
    assert.throws(() => process.kill(h.pid, 0), { code: 'ESRCH' })
    assert.equal((await fetch(`http://127.0.0.1:${P}/ready`)).status, 200)
  } finally { await h.stop(); mine.close() }
})

for (const [name, start] of [
  ['執行檔不存在', { cmd: ['不存在的執行檔'] }],
  ['不 listen 的程序', { cmd: [process.execPath, '-e', 'setInterval(()=>{},1000)'], readyTimeoutMs: 1500 }],
]) {
  test(`server 起不來時失敗退出：${name}`, async () => {
    const { root, opts } = ctx()
    await assert.rejects(startEnv(recipe(start), opts), (e) => /server 未就緒/.test(e.message) && e.message.includes('server.log'))
    assert.equal(existsSync(join(root, '.data', '.lock')), false)
  })
}

test('不 listen 的程序：子程序已被收掉', async () => {
  const { root, opts } = ctx()
  const pidFile = join(root, 'pid')
  const code = `require('fs').writeFileSync(${JSON.stringify(pidFile)},String(process.pid));setInterval(()=>{},1000)`
  await assert.rejects(startEnv(recipe({ cmd: [process.execPath, '-e', code], readyTimeoutMs: 1500 }), opts), /server 未就緒/)
  assert.equal(alive(Number(readFileSync(pidFile, 'utf8'))), false)
})

test('PID 不符不算就緒', async () => {
  const { opts } = ctx()
  let squatter
  const r = recipe({ cmd: [process.execPath, '-e', 'setInterval(()=>{},1000)'], readyTimeoutMs: 1500 }, {
    async reset({ env }) { squatter = await listen(Number(env.PORT)) },
  })
  try { await assert.rejects(startEnv(r, opts), /server 未就緒/) } finally { squatter?.close() }
})

test('同時兩個被拒；死 pid 的鎖可接手', async () => {
  const { root, opts } = ctx()
  const r = recipe({ cmd: [process.execPath, '-e', APP] })
  const h = await startEnv(r, opts)
  try {
    await assert.rejects(startEnv(r, opts), /已有一個 demo-video 在跑（pid \d+）/)
  } finally { await h.stop() }
  mkdirSync(join(root, '.data'), { recursive: true })
  writeFileSync(join(root, '.data', '.lock'), '99999999')
  const h2 = await startEnv(r, opts)
  await h2.stop()
})

test('缺必填欄位列出全部', async () => {
  const dir = tmp()
  const p = join(dir, 'env.mjs')
  writeFileSync(p, `export default { start: { cmd: ['x'], portEnv: 'PORT', readyPath: '/' } }`)
  await assert.rejects(loadEnv(p), (e) => e.message.includes('✗ build') && e.message.includes('✗ reset'))
})

test('findEnv 只看腳本上一層的 env.mjs', () => {
  const dir = tmp()
  mkdirSync(join(dir, 'a'))
  assert.equal(findEnv(join(dir, 'a', 'video.mjs')), null)
  writeFileSync(join(dir, 'env.mjs'), 'export default {}')
  assert.equal(findEnv(join(dir, 'a', 'video.mjs')), join(dir, 'env.mjs'))
})

test('reset 拋錯時不留下 server', async () => {
  const { root, opts } = ctx()
  const r = recipe({ cmd: [process.execPath, '-e', APP] }, { reset() { throw new Error('壞了') } })
  await assert.rejects(startEnv(r, opts), /配方 reset 失敗：壞了/)
  assert.equal(existsSync(join(root, '.data', '.lock')), false)
})

test('cmd 陣列含空白路徑可啟動', async () => {
  const { root, opts } = ctx()
  const dir = join(root, 'has space')
  mkdirSync(dir)
  writeFileSync(join(dir, 'app.js'), APP)
  const h = await startEnv(recipe({ cmd: [process.execPath, join(dir, 'app.js')] }), opts)
  await h.stop()
})

test('SIGINT 會收掉 server', async () => {
  const root = tmp()
  const pidFile = join(root, 'app.pid')
  const app = `require('fs').writeFileSync(${JSON.stringify(pidFile)},String(process.pid));setTimeout(()=>{${APP}},20000)`
  writeFileSync(join(root, 'env.mjs'), `export default { build(){}, reset(){}, start: { cmd: [process.execPath, '-e', ${JSON.stringify(app)}], portEnv: 'PORT', readyPath: '/ready' } }`)
  const p = spawn(process.execPath, [CLI, 'env-check', root], { stdio: ['ignore', 'pipe', 'pipe'] })
  let out = ''
  p.stdout.on('data', (d) => { out += d })
  const until = async (f) => { for (let i = 0; i < 100 && !f(); i++) await new Promise((r) => setTimeout(r, 100)); assert.ok(f()) }
  await until(() => out.includes('reset 完成') && existsSync(pidFile) && readFileSync(pidFile, 'utf8'))
  const code = new Promise((r) => p.on('exit', r))
  p.kill('SIGINT')
  assert.equal(await code, 130)
  assert.equal(alive(Number(readFileSync(pidFile, 'utf8'))), false)
})
