#!/usr/bin/env node
// 派工路由：任務類型 × 難度查 ../references/routing.json → 有序候選，濾掉沒裝／沒登入（agent-mesh-check 的 last.json）
// 與額度封鎖中（狀態檔）的 CLI。也判斷要不要跨家族審查、挑審查者。
// CLI 入口：node route.mjs block <cli> <到期 ISO 時間> [理由] —— 使用者手動標記「這家先省著用」。
import { readFileSync, writeFileSync, mkdirSync, renameSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { homedir } from 'node:os'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { CLIS } from '../../agent-mesh-check/scripts/clis.mjs'

const here = dirname(fileURLToPath(import.meta.url))

export function loadRouting(path = join(here, '..', 'references', 'routing.json')) {
  return JSON.parse(readFileSync(path, 'utf8'))
}

// 比照 agent-mesh-check 的 statePath，資料夾改 agent-dispatch
export function statePath(env = process.env, platform = process.platform) {
  if (env.XDG_STATE_HOME) return join(env.XDG_STATE_HOME, 'agent-dispatch', 'state.json')
  if (platform === 'win32') return join(env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local'), 'agent-dispatch', 'state.json')
  return join(homedir(), '.local', 'state', 'agent-dispatch', 'state.json')
}

export function readState(file) {
  try {
    const s = JSON.parse(readFileSync(file, 'utf8'))
    return s && typeof s === 'object' && s.blocks && typeof s.blocks === 'object' ? s : { ...s, blocks: {} }
  } catch { return { blocks: {} } }
}

export const sleepSync = ms => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)

// 先寫暫存檔再 rename：並行的 worker 同時改也不會讀到半個檔。
// Windows 上目標檔正被別的程序開著時 rename 會 EPERM／EBUSY，短暫重試幾次。
export function writeState(file, state, { rename = renameSync } = {}) {
  mkdirSync(dirname(file), { recursive: true })
  const tmp = `${file}.${process.pid}.tmp`
  writeFileSync(tmp, JSON.stringify(state, null, 2) + '\n')
  for (let i = 0; ; i++) {
    try { rename(tmp, file); return } catch (e) {
      if (i >= 5 || !['EPERM', 'EBUSY'].includes(e.code)) throw e
      sleepSync(50 * (i + 1))
    }
  }
}

export function blockCli(file, cli, until, reason) {
  const s = readState(file)
  s.blocks[cli] = { until, reason }
  writeState(file, s)
}

// agent-mesh-check last.json：只排除 layer 2（自己回話）明確沒過的；結果裡沒有的（之後才裝、當時沒裝）視為可用。
// 沒資料回 null＝未知，不濾。
export function meshAvailable(last) {
  if (!last || !Array.isArray(last.results)) return null
  const self = last.results.filter(r => r.layer === 2)
  const failed = new Set(self.filter(r => r.status !== 'pass').map(r => r.a))
  for (const r of self) if (r.status === 'pass') failed.delete(r.a)
  return new Set(CLIS.filter(c => !failed.has(c)))
}

export function readMesh(file) {
  try { return meshAvailable(JSON.parse(readFileSync(file, 'utf8'))) } catch { return null }
}

export function candidates({ type, tier, routing, state, available, now = Date.now(), exclude = [] }) {
  const t = tier ?? routing.types[type]
  if (!routing.tiers[t]) throw new Error(`未知的任務類型或等級：${type ?? tier}`)
  return routing.tiers[t].filter(c =>
    (!available || available.has(c.cli)) &&
    !((state.blocks[c.cli]?.until ?? 0) > now) &&
    !exclude.includes(c.cli))
}

export function needsCrossReview({ paths = [], lines = 0 }, routing) {
  const { pathPatterns, maxLines } = routing.crossReview
  // Windows 路徑（src\api\x）先換成 /，路徑樣式只寫 / 一種
  return lines > maxLines || paths.some(p => pathPatterns.some(re => new RegExp(re, 'i').test(p.replace(/\\/g, '/'))))
}

// 審查者：top 候選裡第一個不同家族的；湊不到就退回同家（crossFamily:false，回報要寫明）
export function reviewer({ author, routing, state, available, now = Date.now() }) {
  const pool = candidates({ tier: 'top', routing, state, available, now })
  const fam = routing.family[author]
  const other = pool.find(c => routing.family[c.cli] !== fam)
  if (other) return { ...other, crossFamily: true }
  const same = pool.find(c => c.cli !== author) ?? pool[0]
  return same ? { ...same, crossFamily: false } : null
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [cmd, cli, until, ...why] = process.argv.slice(2)
  const t = Date.parse(until ?? '')
  if (cmd === 'pick') {
    // 唯讀查表：node route.mjs pick <類型> [--state 檔] [--mesh 檔] → 印出有序候選 JSON，不派工
    const opt = k => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : undefined }
    const { statePath: meshStatePath } = await import('../../agent-mesh-check/scripts/mesh.mjs')
    try {
      console.log(JSON.stringify(candidates({ type: cli, routing: loadRouting(), state: readState(opt('--state') ?? statePath()),
        available: readMesh(opt('--mesh') ?? meshStatePath(process.env)) })))
    } catch (e) {
      console.error(e.message)
      process.exitCode = 2
    }
  } else if (cmd !== 'block' || !cli || Number.isNaN(t)) {
    console.error('用法：node route.mjs block <cli> <到期時間，ISO 格式> [理由]｜node route.mjs pick <任務類型>')
    process.exitCode = 2
  } else if (!CLIS.includes(cli)) {
    console.error(`未知的 CLI：${cli}（可用：${CLIS.join('、')}）`)
    process.exitCode = 2
  } else {
    const f = statePath()
    blockCli(f, cli, t, why.join(' ') || 'manual')
    console.log(`已標記 ${cli} 到 ${new Date(t).toISOString()} 前不派（${f}）`)
  }
}
// 並行上限：爭用時調降的值只在 parallelResetAt 之前有效，到期回到路由表的值
export const parallelLimit = (state, routing, now = Date.now()) =>
  state.maxParallel && (state.parallelResetAt ?? 0) > now ? state.maxParallel : routing.maxParallel
