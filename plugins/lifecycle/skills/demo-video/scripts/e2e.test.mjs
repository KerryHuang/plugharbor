// 端到端回歸：本機靜態頁＋假 TTS 跑完整流程，最後一段畫面完全靜止，影像軌與音軌長度必須一致。
// 不依賴網路。缺 ffmpeg／libmp3lame／Chrome／playwright-core 時跳過（playwright-core 需裝在執行 node --test 的目前目錄）。
// 設 DEMO_VIDEO_E2E_REQUIRED=1（CI 專用步驟用）時，缺依賴改為失敗，避免「零執行卻成功」。
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { findPlaywright } from './lib/deps.mjs'
import { checkStreams } from './lib/media.mjs'

const ENGINE = fileURLToPath(new URL('./demo-video.mjs', import.meta.url))
const has = (cmd, args) => spawnSync(cmd, args, { encoding: 'utf8' })
// 與引擎、ensure-tools.sh 一致：CHROME_PATH 有設只認它，否則認系統安裝的 Google Chrome
const CHROMES = process.env.CHROME_PATH ? [process.env.CHROME_PATH] : ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/opt/google/chrome/chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe']

function skipReason() {
  if (has('ffmpeg', ['-version']).status !== 0 || has('ffprobe', ['-version']).status !== 0) return '沒有 ffmpeg／ffprobe'
  if (!has('ffmpeg', ['-hide_banner', '-encoders']).stdout?.includes('libmp3lame')) return 'ffmpeg 沒有 libmp3lame（假 TTS 要用）'
  if (!CHROMES.some((c) => c && existsSync(c))) return '找不到系統 Chrome'
  if (!findPlaywright()) return '目前目錄找不到 playwright-core（先在目前目錄 npm install playwright-core）'
  return false
}

// 按送出後整頁變成深綠色：操作前後的影格差異大，不會被編碼雜訊影響
const PAGE = `<!doctype html><meta charset=utf-8><title>demo</title>
<body style="font:24px sans-serif;padding:60px;background:#fff"><h1 id=h>請假申請</h1>
<button id=go style="font-size:28px" onclick="document.getElementById('h').textContent='已送出';document.body.style.background='#2e7d32'">送出</button>
<input id=reason aria-label="事由" style="font-size:28px;display:block;margin-top:30px"></body>`

const VIDEO = `
import { execFileSync } from 'node:child_process'
export default {
  name: 'e2e',
  tts: async (text, outFile) => {
    const d = Math.max(2, text.length * 0.3)
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=' + d, '-c:a', 'libmp3lame', outFile])
  },
  segments: [
    { text: '先在事由欄位輸入文字，再按送出。', run: async (a) => {
      await a.type(a.p.getByLabel('事由'), '家庭因素')
      await a.click(a.p.getByRole('button', { name: '送出' }))
    } },
    { text: '最後這一段畫面完全不動，旁白要講比較久，影像軌也必須撐到最後一秒，不能提早結束。', run: async (a) => { await a.pause(100) } },
  ],
}
`

// 影片某時間點的縮小灰階影格（64×36）
function grayFrame(file, t) {
  const r = spawnSync('ffmpeg', ['-v', 'error', '-ss', t.toFixed(2), '-i', file, '-frames:v', '1', '-vf', 'scale=64:36,format=gray', '-f', 'rawvideo', '-'], { maxBuffer: 1 << 20 })
  assert.equal(r.stdout.length, 64 * 36, `抓不到 ${t}s 的影格：${r.stderr}`)
  return r.stdout
}
const mean = (b) => b.reduce((s, x) => s + x, 0) / b.length
const meanAbsDiff = (a, b) => a.reduce((s, x, i) => s + Math.abs(x - b[i]), 0) / a.length

test('靜止的最後一段：影像軌與音軌長度一致，且畫面內容確實隨操作變化', { timeout: 180000 }, async (t) => {
  const reason = skipReason()
  if (reason) {
    if (process.env.DEMO_VIDEO_E2E_REQUIRED === '1') assert.fail(`DEMO_VIDEO_E2E_REQUIRED=1，但缺依賴：${reason}`)
    return t.skip(reason)
  }
  const dir = mkdtempSync(join(tmpdir(), 'demo-video-e2e-'))
  writeFileSync(join(dir, 'video.mjs'), VIDEO)
  const server = createServer((_, res) => { res.setHeader('content-type', 'text/html; charset=utf-8'); res.end(PAGE) })
  await new Promise((r) => server.listen(0, '127.0.0.1', r))
  try {
    const base = `http://127.0.0.1:${server.address().port}/`
    const out = join(dir, "o'ut dir") // 含單引號與空白的輸出路徑也要能用
    // 要非同步 spawn：spawnSync 會卡住同一個 process 裡的 http server
    const r = await new Promise((resolve) => {
      const c = spawn('node', [ENGINE, 'build', join(dir, 'video.mjs'), '--out', out, '--base', base], { cwd: process.cwd() })
      let log = ''
      c.stdout.on('data', (d) => { log += d }); c.stderr.on('data', (d) => { log += d })
      c.on('close', (code) => resolve({ code, log }))
    })
    assert.equal(r.code, 0, r.log)
    assert.ok(existsSync(join(out, 'e2e.mp4')) && existsSync(join(out, 'e2e.srt')), r.log)
    const { total } = JSON.parse(readFileSync(join(out, 'timeline.json'), 'utf8'))
    const s = checkStreams(join(out, 'e2e.mp4'), total)
    assert.deepEqual(s.problems, [], `影像 ${s.video} 音軌 ${s.audio} 預期 ${total}`)
    assert.ok(Math.abs(s.video - s.audio) <= 0.2)
    assert.match(r.log, /等使用者試聽/)

    // 畫面內容：不能只有長度對。操作前（白頁）、操作後（綠頁）要明顯不同；片尾靜止段仍有畫面，且與操作後一致、不是黑畫面
    const tl = JSON.parse(readFileSync(join(out, 'timeline.json'), 'utf8'))
    const mp4 = join(out, 'e2e.mp4')
    const before = grayFrame(mp4, 0.3)
    const after = grayFrame(mp4, tl.segs[1].t + 0.5)
    const tail = grayFrame(mp4, total - 0.3)
    assert.ok(meanAbsDiff(before, after) > 60, `操作前後影格差異太小：${meanAbsDiff(before, after).toFixed(1)}（畫面疑似凍結）`)
    assert.ok(mean(tail) > 40, `片尾影格近乎全黑：mean ${mean(tail).toFixed(1)}`)
    assert.ok(meanAbsDiff(after, tail) < 15, `片尾影格與操作後差異過大：${meanAbsDiff(after, tail).toFixed(1)}`)
  } finally {
    server.close()
  }
})
