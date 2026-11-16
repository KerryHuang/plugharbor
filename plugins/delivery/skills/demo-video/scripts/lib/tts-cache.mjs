// 配音快取：同一 provider、voice、文字只合成一次。

import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

export function withTtsCache(tts, { dir, provider }) {
  return async (text, outFile, opts = {}) => {
    const key = createHash('sha256').update(`${provider}\0${opts.voice}\0${text}`).digest('hex')
    const cached = path.join(dir, `${key}.mp3`)
    // 空檔視為未命中
    if (fs.existsSync(cached) && fs.statSync(cached).size > 0) {
      fs.copyFileSync(cached, outFile)
      return { hit: true }
    }
    await tts(text, outFile, opts)
    fs.mkdirSync(dir, { recursive: true })
    // 先寫暫存再 rename，避免寫到一半留下壞檔
    const tmp = `${cached}.tmp-${process.pid}`
    fs.copyFileSync(outFile, tmp)
    fs.renameSync(tmp, cached)
    return { hit: false }
  }
}
