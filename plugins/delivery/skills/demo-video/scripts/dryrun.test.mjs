// dry-run：不配音、不錄影，只驗操作能跑完；失敗時印元素清單。配方用 node 靜態頁 app。
// 缺 Chrome／playwright-core 時跳過（同 e2e.test.mjs）。DEMO_VIDEO_E2E_REQUIRED=1 時缺依賴改為失敗。
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { findPlaywright } from './lib/deps.mjs'

const ENGINE = fileURLToPath(new URL('./demo-video.mjs', import.meta.url))
const has = (cmd, args) => spawnSync(cmd, args, { encoding: 'utf8' })
const CHROMES = process.env.CHROME_PATH ? [process.env.CHROME_PATH] : ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/opt/google/chrome/chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe']

function skipReason() {
  if (!CHROMES.some((c) => c && existsSync(c))) return '找不到系統 Chrome'
  if (!findPlaywright()) return '目前目錄找不到 playwright-core（先在目前目錄 npm install playwright-core）'
  return false
}

const PAGE = `<!doctype html><meta charset=utf-8><title>demo</title>
<body style="font:24px sans-serif;padding:60px;background:#fff"><h1 id=h>請假申請</h1>
<button id=go style="font-size:28px" onclick="document.getElementById('h').textContent='已送出';document.body.style.background='#2e7d32'">送出</button>
<input id=reason aria-label="事由" style="font-size:28px;display:block;margin-top:30px"></body>`

const ENV = `export default {
  build() {}, reset() {},
  start: { cmd: [process.execPath, new URL('./app.js', import.meta.url).pathname.replace(/^\\/([A-Za-z]:)/, '$1')], portEnv: 'PORT', readyPath: '/ready' },
}
`
const APP = `require('fs').writeFileSync(__dirname + '/server.pid', String(process.pid))
const page = ${JSON.stringify(PAGE)}
require('http').createServer((q, r) => { if (q.url === '/ready') { r.end('ok'); return } r.setHeader('content-type', 'text/html; charset=utf-8'); r.end(page) }).listen(Number(process.env.PORT), '127.0.0.1')
`

// 建配方目錄：<tmp>/env.mjs、<tmp>/app.js、<tmp>/v/video.mjs；回傳 { root, script, out }
function fixture(videoSrc) {
  const root = mkdtempSync(join(tmpdir(), 'dv-dry-'))
  mkdirSync(join(root, 'v'))
  writeFileSync(join(root, 'env.mjs'), ENV)
  writeFileSync(join(root, 'app.js'), APP)
  writeFileSync(join(root, 'v', 'video.mjs'), videoSrc)
  return { root, script: join(root, 'v', 'video.mjs'), out: join(root, 'v', 'out') }
}

const run = (args) => new Promise((resolve) => {
  const c = spawn(process.execPath, [ENGINE, ...args], { cwd: process.cwd() })
  let log = ''
  c.stdout.on('data', (d) => { log += d }); c.stderr.on('data', (d) => { log += d })
  c.on('close', (code) => resolve({ code, log }))
})

const guard = async (t) => {
  const reason = skipReason()
  if (!reason) return false
  if (process.env.DEMO_VIDEO_E2E_REQUIRED === '1') assert.fail(`DEMO_VIDEO_E2E_REQUIRED=1，但缺依賴：${reason}`)
  t.skip(reason)
  return true
}

const video = (segments, extra = '') => `
globalThis.__tts = 0
export default {
  name: 'dry', ${extra}
  tts: async () => { throw new Error('dry-run 不該配音') },
  segments: [${segments}],
}
`
const OK_SEGS = `
  { text: '先在事由欄位輸入文字，再按送出。', run: async (a) => { await a.type(a.p.getByLabel('事由'), '家庭'); await a.click(a.p.getByRole('button', { name: '送出' })) } },
  { text: '送出之後標題會改變。', run: async (a) => { await a.pause(100) } },
`

test('dry-run 不配音不錄影', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(OK_SEGS))
  const t0 = Date.now()
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 0, r.log) // tts 一被呼叫就 throw，exit 0 即代表 0 次
  assert.ok(Date.now() - t0 < 30000)
  assert.ok(!existsSync(join(f.out, 'frames')) && !existsSync(join(f.out, 'voice')))
  const lines = r.log.split('\n').filter((l) => /seg\d 語音估計 [\d.]+s 操作 [\d.]+s/.test(l))
  assert.equal(lines.length, 2, r.log)
})

test('操作超過估計時標 ⚠️', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`{ text: '一二三四五六七八九十一二三四五六七八九十', run: async (a) => { await a.pause(6200) } }`))
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 0, r.log)
  const line = r.log.split('\n').find((l) => l.includes('語音估計 5.0s'))
  assert.ok(line?.endsWith(' ⚠️'), r.log)
})

const BAD = video(`{ text: '按一個不存在的按鈕。', run: async (a) => { await a.click(a.p.getByRole('button', { name: '不存在的按鈕' })) } }`, 'timeoutMs: 1500,')

test('失敗時印可互動元素；失敗後可立即再跑', { timeout: 90000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(BAD)
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 1, r.log)
  assert.match(r.log, /FAIL seg\d/)
  assert.ok(r.log.includes('fail.png'))
  const lines = r.log.split('\n')
  const i = lines.findIndex((l) => l.includes('可互動元素：'))
  assert.ok(i >= 0 && lines.slice(i + 1).includes('送出'), r.log)
  assert.ok(existsSync(join(f.out, 'fail.png')))
  const r2 = await run(['dry-run', f.script])
  assert.equal(r2.code, 1, r2.log)
  assert.ok(!r2.log.includes('已有一個 demo-video 在跑'), r2.log)
  assert.match(r2.log, /FAIL seg\d/)
})

test('expect 不符視同失敗', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`{ text: '按送出。', expect: '不會出現的文字', run: async (a) => { await a.click(a.p.getByRole('button', { name: '送出' })) } }`))
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 1, r.log)
  assert.ok(r.log.includes('FAIL seg'), r.log)
  assert.ok(r.log.includes('expect 未符合：不會出現的文字'), r.log)
  assert.ok(existsSync(join(f.out, 'fail.png')))
})

test('expect 符合（字串與函式）時通過', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`
    { text: '按送出。', expect: '已送出', run: async (a) => { await a.click(a.p.getByRole('button', { name: '送出' })) } },
    { text: '再確認。', expect: (a) => a.p.getByRole('heading', { name: '已送出' }), run: async (a) => { await a.pause(50) } },`))
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 0, r.log)
})

test('配方沒有 login 時 a.as 報錯並 exit 1（AC-12）', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`{ text: '換人。', run: async (a) => { await a.as('user02') } }`))
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 1, r.log)
  assert.ok(r.log.includes('配方沒有 login，不能用 a.as'), r.log)
})

test('server 起不來時 build 失敗退出：exit 1、指出 server.log、沒有 mp4（AC-2）', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(`
import { execFileSync } from 'node:child_process'
export default {
  name: 'bad',
  tts: async (text, outFile) => { execFileSync('ffmpeg', ['-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-c:a', 'libmp3lame', outFile]) },
  segments: [{ text: '不會執行到。', run: async (a) => { await a.pause(10) } }],
}
`)
  writeFileSync(join(f.root, 'env.mjs'), `export default { build() {}, reset() {}, start: { cmd: ['不存在的執行檔'], portEnv: 'PORT', readyPath: '/ready' } }\n`)
  const r = await run(['build', f.script])
  assert.equal(r.code, 1, r.log)
  assert.ok(r.log.includes('server 未就緒') && r.log.includes('server.log'), r.log)
  assert.ok(!readdirSync(f.out).some((n) => n.endsWith('.mp4')), r.log)
})

const alive = (pid) => { try { process.kill(pid, 0); return true } catch (e) { return e.code !== 'ESRCH' } }
const serverPid = (f) => Number(readFileSync(join(f.root, 'server.pid'), 'utf8'))
const waitFor = async (cond, ms = 5000) => { for (let i = 0; i < ms / 50 && !cond(); i++) await new Promise((r) => setTimeout(r, 50)) }

test('a.upload 指到不存在的按鈕：FAIL seg、exit 1、鎖與 server 都收乾淨（C1）', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`{ text: '上傳檔案。', run: async (a) => { await a.upload(a.p.getByRole('button', { name: '不存在的按鈕' }), 'x.png') } }`, 'timeoutMs: 1000,'))
  const r = await run(['dry-run', f.script])
  assert.equal(r.code, 1, r.log)
  assert.ok(r.log.includes('FAIL seg'), r.log)
  assert.ok(existsSync(join(f.out, 'fail.png')))
  assert.equal(existsSync(join(f.root, '.data', '.lock')), false)
  assert.equal(alive(serverPid(f)), false)
})

test('引擎遇到 uncaught exception 也不留孤兒 server 與鎖檔（I1）', { timeout: 60000, skip: process.platform === 'win32' }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`{ text: '會炸掉。', run: async (a) => { setTimeout(() => { throw new Error('boom') }, 200); await a.pause(5000) } }`))
  const r = await run(['dry-run', f.script])
  assert.notEqual(r.code, 0, r.log)
  assert.ok(r.log.includes('boom'), r.log)
  await waitFor(() => !alive(serverPid(f)))
  assert.equal(alive(serverPid(f)), false)
  assert.equal(existsSync(join(f.root, '.data', '.lock')), false)
})

test('同一支影片同時 build：第二個立刻被拒，且不動第一個的 out（I2）', { timeout: 60000 }, async (t) => {
  if (await guard(t)) return
  const f = fixture(video(`{ text: '慢一點。', run: async (a) => { await a.pause(4000) } }`))
  mkdirSync(join(f.out, 'frames'), { recursive: true })
  const sentinel = join(f.out, 'frames', 'sentinel')
  writeFileSync(sentinel, 'x')
  const first = run(['dry-run', f.script])
  await waitFor(() => existsSync(join(f.root, '.data', '.lock')))
  const t0 = Date.now()
  const second = await run(['build', f.script])
  assert.equal(second.code, 1, second.log)
  assert.match(second.log, /已有一個 demo-video 在跑（pid \d+）/)
  assert.ok(Date.now() - t0 < 3500, '第二個應立刻失敗')
  assert.ok(existsSync(sentinel), '第一個的 out 不該被第二個清掉')
  assert.equal((await first).code, 0)
  assert.equal(existsSync(join(f.root, '.data', '.lock')), false)
})
