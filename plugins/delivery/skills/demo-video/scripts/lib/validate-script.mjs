// 建置前驗腳本：一次列出全部錯誤，不用等到配音、錄影跑一半才發現。欄位定義見 references/script-format.md。
import { assertSafeName } from './media.mjs'

const SEGMENT = "{ text: '一句旁白。', run: async (a) => { await a.pause(1000) } }"
const isText = (v) => typeof v === 'string' && v.trim() !== ''

export function validateScript(cfg, { base } = {}) {
  if (cfg === null || typeof cfg !== 'object') {
    return [{ path: 'export default', message: '腳本沒有 export default 一個物件', example: `export default { base: 'http://127.0.0.1:5190/', segments: [${SEGMENT}] }` }]
  }
  const errs = []
  const add = (path, message, example) => errs.push({ path, message, example })
  if (cfg.name !== undefined) {
    try { assertSafeName(cfg.name) } catch (e) { add('name', e.message, "name: 'leave-request'") }
  }
  if (!base && !cfg.base) add('base', '腳本沒有 base，也沒給 --base', "base: 'http://127.0.0.1:5190/'")
  if (cfg.viewport !== undefined && !(cfg.viewport?.width > 0 && cfg.viewport.width * 9 === cfg.viewport.height * 16)) {
    add('viewport', '必須是 16:9', 'viewport: { width: 1280, height: 720 }')
  }
  for (const k of ['tts', 'setup']) {
    if (cfg[k] !== undefined && typeof cfg[k] !== 'function') add(k, '必須是函式', `${k}: async (...) => {}`)
  }
  if (!Array.isArray(cfg.segments) || cfg.segments.length === 0) {
    add('segments', '必須是非空陣列', `segments: [${SEGMENT}]`)
    return errs
  }
  cfg.segments.forEach((s, i) => {
    if (!isText(s?.text)) add(`segments[${i}].text`, '缺少旁白文字', SEGMENT)
    if (typeof s?.run !== 'function') add(`segments[${i}].run`, '必須是函式', SEGMENT)
  })
  return errs
}

export function formatScriptErrors(errs) {
  const lines = errs.flatMap((e) => [`✗ ${e.path}：${e.message}`, `  正確範例：${e.example}`])
  return [...lines, `✗ ${errs.length} 個錯誤；沒有開始建置`].join('\n')
}
