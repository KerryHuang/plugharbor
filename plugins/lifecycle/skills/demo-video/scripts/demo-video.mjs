#!/usr/bin/env node
// demo-video 引擎。
//   node demo-video.mjs build  <video.mjs> [--out <dir>] [--base <url>]   配音 → 錄影 → 字幕 → 合成 → 驗證
//   node demo-video.mjs verify <out-dir>                                  只重跑驗證
// 需在裝有 playwright-core 的工作目錄下執行。腳本格式見 references/script-format.md。
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { loadPlaywright } from './lib/deps.mjs'
import { createActor, installCursor, nudgeCursor } from './lib/actor.mjs'
import { buildCues, toSrt } from './lib/subtitles.mjs'
import { formatScriptErrors, validateScript } from './lib/validate-script.mjs'
import { assertSafeName, buildFilterGraph, checkStreams, compose, contactSheet, probeDuration, segmentVolume, sh } from './lib/media.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SILENT_DB = -50 // 區間內最大音量低於此值視為靜音

// 預設語音：edge-tts（非正式授權 API，對外發布前先看 SKILL.md 的授權提醒）
async function defaultTts(text, outFile, { voice }) {
  sh('uvx', ['edge-tts', '--voice', voice, '--text', text, '--write-media', outFile])
}

export async function build(scriptPath, { out = 'out', base } = {}) {
  const cfg = (await import(pathToFileURL(resolve(scriptPath)).href)).default
  const errs = validateScript(cfg, { base })
  if (errs.length) throw Object.assign(new Error(formatScriptErrors(errs)), { scriptInvalid: true })
  const name = assertSafeName(cfg.name ?? 'video')
  const url = base ?? cfg.base
  const voice = cfg.voice ?? 'zh-TW-HsiaoChenNeural'
  const tts = cfg.tts ?? defaultTts
  const gapMs = cfg.gapMs ?? 450 // 語音檔尾端本來就帶約 1 秒靜音，段落間隔不要再加多
  const segments = cfg.segments
  const OUT = resolve(out)
  for (const d of ['frames', 'voice', 'caps', 'verify']) rmSync(join(OUT, d), { recursive: true, force: true })
  for (const d of ['frames', 'voice', 'caps']) mkdirSync(join(OUT, d), { recursive: true })

  // 1. 配音
  for (const [i, s] of segments.entries()) {
    s.audio = join(OUT, 'voice', `${i}.mp3`)
    await tts(s.text, s.audio, { voice })
    s.dur = probeDuration(s.audio)
  }

  // 2. 依語音長度錄操作
  const { chromium } = loadPlaywright()
  // 與 ensure-tools.sh 一致：CHROME_PATH 有設就用它（任何 Chromium 系），否則用系統安裝的 Google Chrome
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH, headless: true } : { channel: 'chrome', headless: true })
  try {
    const ctx = await browser.newContext({ viewport: cfg.viewport ?? { width: 1280, height: 720 }, deviceScaleFactor: 1.5, locale: cfg.locale ?? 'zh-TW' })
    const p = await ctx.newPage()
    p.setDefaultTimeout(cfg.timeoutMs ?? 8000)
    await installCursor(p)
    const a = createActor(p)

    const cdp = await ctx.newCDPSession(p)
    const frames = []
    cdp.on('Page.screencastFrame', async ({ data, metadata, sessionId }) => {
      const rel = `frames/${String(frames.length).padStart(6, '0')}.jpg` // 清單一律用相對於清單檔的 / 路徑，Windows 與含引號的 OUT 都不受影響
      const f = join(OUT, rel)
      frames.push({ rel, t: metadata.timestamp })
      writeFileSync(f, Buffer.from(data, 'base64'))
      cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {})
    })
    if (cfg.setup) await cfg.setup(p, a, url)
    else await p.goto(url)
    await sleep(500)
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 })
    await nudgeCursor(p)

    for (const [i, s] of segments.entries()) {
      const t0 = Date.now()
      s.t0Ms = t0 // 時間軸以實際錄影為準：音訊與字幕都用這個時間
      try {
        await s.run(a)
      } catch (e) {
        // 失敗時留下證據再結束：截圖、網址、畫面文字
        await p.screenshot({ path: join(OUT, 'fail.png') }).catch(() => {})
        console.log(`FAIL seg${i} ${p.url()}\n${String(e.message).slice(0, 300)}`)
        console.log('畫面文字：' + (await p.locator('body').innerText().catch(() => '')).slice(0, 400).replace(/\n/g, ' | '))
        console.log(`截圖：${join(OUT, 'fail.png')}`)
        process.exitCode = 1
        return null
      }
      const used = Date.now() - t0
      const need = s.dur * 1000 + gapMs
      s.over = used > need
      console.log(`seg${i} voice ${s.dur.toFixed(1)}s actions ${(used / 1000).toFixed(1)}s${s.over ? ' OVER' : ''}`)
      if (used < need) await sleep(need - used)
    }
    await sleep(800)
    await cdp.send('Page.stopScreencast')
    const endT = Date.now() / 1000

    // 3. 影格轉影片清單
    const start = frames[0].t
    const total = endT - start
    // 最後一格只給一個影格長度；片尾靜止的部分由合成時的 tpad 補滿（唯一機制，test 會驗證拿掉它就失敗）
    let list = ''
    frames.forEach((fr, i) => {
      const d = i + 1 < frames.length ? frames[i + 1].t - fr.t : 1 / 30
      list += `file '${fr.rel}'\nduration ${Math.max(d, 0.001).toFixed(4)}\n`
    })
    list += `file '${frames.at(-1).rel}'\n`
    writeFileSync(join(OUT, 'frames.txt'), list)

    // 4. 字幕：旁白稿切句、估時；SRT 與燒進畫面的透明 PNG
    const starts = segments.map((s) => s.t0Ms / 1000 - start)
    const cues = segments.flatMap((s, i) => buildCues(s.text, starts[i], s.dur))
    writeFileSync(join(OUT, `${name}.srt`), toSrt(cues))
    // ffmpeg 不一定有 libass／drawtext：字幕在瀏覽器渲染成透明 PNG 再 overlay
    const capPage = await (await browser.newContext({ viewport: { width: 1920, height: 1080 } })).newPage()
    const font = cfg.subtitleFont ?? "'PingFang TC','Noto Sans CJK TC','Microsoft JhengHei',system-ui"
    for (const [i, c] of cues.entries()) {
      await capPage.setContent(`<html><body style="margin:0;background:transparent"><div style="position:fixed;left:0;right:0;bottom:44px;text-align:center"><span id="t" style="display:inline-block;font:500 44px/1.35 ${font};color:#fff;background:rgba(0,0,0,.74);padding:10px 28px;border-radius:10px"></span></div></body></html>`)
      await capPage.evaluate((x) => { document.getElementById('t').textContent = x }, c.text)
      await capPage.screenshot({ path: join(OUT, 'caps', `${i}.png`), omitBackground: true })
    }

    // 5. 合成
    compose({
      framesTxt: join(OUT, 'frames.txt'),
      audios: segments.map((s) => s.audio),
      capPngs: cues.map((_, i) => join(OUT, 'caps', `${i}.png`)),
      filter: buildFilterGraph({ total, starts, cues }),
      lastLabel: `v${cues.length}`,
      total,
      outFile: join(OUT, `${name}.mp4`),
    })
    writeFileSync(join(OUT, 'timeline.json'), JSON.stringify({ name, total, segs: segments.map((s, i) => ({ t: starts[i], dur: s.dur, over: s.over, text: s.text })), cues }, null, 1))
    console.log(`frames ${frames.length} total ${total.toFixed(1)}s cues ${cues.length}`)
  } finally {
    await browser.close()
  }
  return verify(OUT)
}

// 驗證：影像軌／音軌長度分別檢查、每段旁白區間量音量、contact sheet。回傳 { ok }。
export function verify(outDir) {
  const OUT = resolve(outDir)
  const tl = JSON.parse(readFileSync(join(OUT, 'timeline.json'), 'utf8'))
  assertSafeName(tl.name)
  const mp4 = join(OUT, `${tl.name}.mp4`)
  const problems = []

  const s = checkStreams(mp4, tl.total)
  console.log(`影像軌 ${s.video.toFixed(1)}s｜音軌 ${s.audio.toFixed(1)}s｜應為 ${tl.total.toFixed(1)}s（容器 ${probeDuration(mp4).toFixed(1)}s，僅供參考）`)
  problems.push(...s.problems)

  tl.segs.forEach((g, i) => {
    const v = segmentVolume(mp4, g.t, g.dur)
    const silent = !Number.isFinite(v.max) || v.max < SILENT_DB
    console.log(`seg${i} 音量 mean ${v.mean} dB｜max ${v.max} dB${silent ? ' 靜音' : ''}${g.over ? '｜操作超過語音（OVER）' : ''}`)
    if (silent) problems.push(`seg${i}（${g.t.toFixed(1)}s 起 ${g.dur.toFixed(1)}s）幾乎無聲`)
  })

  const sheet = join(OUT, 'verify', 'contact.jpg')
  mkdirSync(join(OUT, 'verify'), { recursive: true })
  const times = [0.3, ...tl.segs.map((g) => g.t + g.dur / 2), tl.total - 0.5]
  contactSheet(mp4, times, sheet, join(OUT, 'verify', 'frames'))
  console.log(`contact sheet：${sheet}（由 agent 開圖看過；每格依序為：開頭、各段中點、結尾）`)

  if (problems.length) {
    console.log('機器檢查失敗：\n- ' + problems.join('\n- '))
    process.exitCode = 1
    return { ok: false, problems }
  }
  console.log('機器檢查通過。語音品質、發音、字幕對齊未驗證——需要人試聽，現在狀態是等使用者試聽，不是完工。')
  return { ok: true, problems }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [cmd, target, ...rest] = process.argv.slice(2)
  const opt = (k) => { const i = rest.indexOf(k); return i >= 0 ? rest[i + 1] : undefined }
  if (cmd === 'build' && target) {
    await build(target, { out: opt('--out'), base: opt('--base') }).catch((e) => {
      if (!e.scriptInvalid) throw e
      console.error(e.message)
      process.exit(1)
    })
  }
  else if (cmd === 'verify' && target) verify(target)
  else { console.error('用法：demo-video.mjs build <video.mjs> [--out dir] [--base url] | verify <out-dir>'); process.exit(2) }
}
