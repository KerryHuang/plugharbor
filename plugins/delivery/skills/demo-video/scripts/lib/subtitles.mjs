// 字幕：由旁白稿切句、估時、輸出 SRT。不做語音辨識。

const BREAK = /(?<=[，。！？；])/
const STOP = /[，。！？；]$/

// 標點代表停頓：每個標點多算 2 個字的時間
export const weight = (part) => part.length + (STOP.test(part) ? 2 : 0)

// 超過 maxChars 的句子均分成幾段，避免字幕寬過畫面
function wrap(part, maxChars) {
  const body = part.replace(STOP, '')
  const tail = part.slice(body.length)
  const n = Math.ceil(body.length / maxChars)
  if (n <= 1) return [part]
  const size = Math.ceil(body.length / n)
  const out = []
  for (let i = 0; i < n; i++) out.push(body.slice(i * size, (i + 1) * size))
  out[n - 1] += tail
  return out
}

export function splitSentences(text, maxChars = 26) {
  return text.split(BREAK).map((s) => s.trim()).filter(Boolean).flatMap((p) => wrap(p, maxChars))
}

// 一段旁白 → 字幕。t0 是這段音訊實際放進影片的秒數，dur 是語音長度；時間按字數（含標點加權）分配。
export function buildCues(text, t0, dur, maxChars = 26) {
  const parts = splitSentences(text, maxChars)
  const sum = parts.reduce((n, x) => n + weight(x), 0)
  let t = t0
  return parts.map((x) => {
    const d = (dur * weight(x)) / sum
    const cue = { text: x.replace(STOP, ''), from: t, to: t + d }
    t += d
    return cue
  })
}

export function srtTime(sec) {
  const ms = Math.round(sec * 1000)
  const pad = (n, l = 2) => String(n).padStart(l, '0')
  return `${pad(Math.floor(ms / 3600000))}:${pad(Math.floor(ms / 60000) % 60)}:${pad(Math.floor(ms / 1000) % 60)},${pad(ms % 1000, 3)}`
}

export const toSrt = (cues) =>
  cues.map((c, i) => `${i + 1}\n${srtTime(c.from)} --> ${srtTime(c.to)}\n${c.text}\n`).join('\n')
