// ffmpeg / ffprobe 封裝：合成與驗證。
import { execFileSync, spawnSync } from 'node:child_process'
import { mkdirSync, rmSync } from 'node:fs'
import { join } from 'node:path'

// 輸出檔名只接受單純檔名：不含路徑分隔、不是 . 或 ..，避免 name 帶出 OUT 外面覆寫檔案
export function assertSafeName(name) {
  if (typeof name !== 'string' || !name || name === '.' || name === '..' || /[\\/\0]/.test(name)) {
    throw new Error(`name 只能是單純檔名（不含 / \\ 與 ..），收到：${JSON.stringify(name)}`)
  }
  return name
}

export const sh = (cmd, args) => execFileSync(cmd, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })

export const probeDuration = (file) =>
  Number(sh('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file]))

// 影像軌與音軌各自的長度，不看容器長度（容器長度會取最長那條，影像軌提早結束時看不出來）
export function parseStreamDurations(csv) {
  const out = { video: NaN, audio: NaN }
  for (const line of csv.trim().split('\n')) {
    const [type, dur] = line.split(',')
    if (type in out) out[type] = Number(dur)
  }
  return out
}

export function checkStreams(file, expected, tol = 0.2) {
  const d = parseStreamDurations(sh('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,duration', '-of', 'csv=p=0', file]))
  const problems = []
  for (const k of ['video', 'audio']) {
    if (!Number.isFinite(d[k])) problems.push(`${k} 軌讀不到長度`)
    else if (Math.abs(d[k] - expected) > tol) problems.push(`${k} 軌 ${d[k].toFixed(1)}s，應為 ${expected.toFixed(1)}s`)
  }
  if (Number.isFinite(d.video) && Number.isFinite(d.audio) && Math.abs(d.video - d.audio) > tol) {
    problems.push(`影像 ${d.video.toFixed(1)}s 與音軌 ${d.audio.toFixed(1)}s 不一致（播放器會在較短那條結束時失去畫面或聲音）`)
  }
  return { ...d, problems }
}

export function segmentVolume(file, from, dur) {
  const r = spawnSync('ffmpeg', ['-v', 'info', '-ss', String(from), '-t', String(dur), '-i', file, '-vn', '-af', 'volumedetect', '-f', 'null', '-'], { encoding: 'utf8' })
  const num = (name) => { const m = new RegExp(`${name}: (-?[\\d.]+|-inf) dB`).exec(r.stderr); return m ? Number(m[1]) : NaN }
  return { mean: num('mean_volume'), max: num('max_volume') }
}

// 每段取中點一格，外加開頭與結尾，拼成一張 contact sheet 給人（或 agent）看
export function contactSheet(file, times, outFile, workDir) {
  rmSync(workDir, { recursive: true, force: true })
  mkdirSync(workDir, { recursive: true })
  times.forEach((t, i) => sh('ffmpeg', ['-y', '-v', 'error', '-ss', t.toFixed(2), '-i', file, '-frames:v', '1', '-vf', 'scale=640:-2', join(workDir, `f${String(i).padStart(3, '0')}.jpg`)]))
  const rows = Math.ceil(times.length / 3)
  sh('ffmpeg', ['-y', '-v', 'error', '-framerate', '1', '-i', join(workDir, 'f%03d.jpg'), '-vf', `tile=3x${rows}:padding=6:color=white`, '-frames:v', '1', outFile])
}

// filter_complex：輸入 0 是影格 concat，1..n 是各段音訊，n+1.. 是字幕 PNG。
export function buildFilterGraph({ total, starts, cues }) {
  const t = total.toFixed(2)
  const n = starts.length
  // 畫面靜止時沒有新影格，影像軌會比音軌短：tpad 用最後一格補到全片長，trim 截齊。
  let g = `[0:v]scale=1920:1080,tpad=stop_mode=clone:stop_duration=${t},fps=30,trim=duration=${t},format=yuv420p[v0];`
  g += starts.map((s, i) => `[${i + 1}:a]adelay=${Math.round(s * 1000)}:all=1[a${i}]`).join(';')
  g += `;${starts.map((_, i) => `[a${i}]`).join('')}amix=inputs=${n}:normalize=0:duration=longest,apad,atrim=0:${t}[a]`
  cues.forEach((c, i) => { g += `;[v${i}][${n + 1 + i}:v]overlay=enable='between(t,${c.from.toFixed(3)},${c.to.toFixed(3)})'[v${i + 1}]` })
  return g
}

export function compose({ framesTxt, audios, capPngs, filter, lastLabel, total, outFile }) {
  const args = ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', framesTxt]
  audios.forEach((f) => args.push('-i', f))
  capPngs.forEach((f) => args.push('-i', f))
  args.push('-filter_complex', filter, '-map', `[${lastLabel}]`, '-map', '[a]', '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-t', total.toFixed(2), outFile)
  sh('ffmpeg', args)
}
