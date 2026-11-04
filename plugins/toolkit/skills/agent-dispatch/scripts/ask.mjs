#!/usr/bin/env node
// 派工短問答：把 prompt 檔交給另一個 agent CLI 以唯讀模式跑一輪。
// 對象：--to 指定，或 --type／--tier 查 ../references/routing.json 依序挑；額度用盡就封鎖該家、改派下一家。
// 第一行固定印「[ask] 交給 <cli>（<模型>／<等級>），理由：…」；輸出超過 16000 字元時全文寫進結果檔，只印摘要。
// exit：目標 CLI 的 exit code；逾時 124；PATH 上找不到 127；用法錯誤 2；所有候選都不能用 75。
import { readFileSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { CLIS, resolveBin, buildArgs, scrubEnv, run, quotaInfo } from '../../agent-mesh-check/scripts/clis.mjs'
import { statePath as meshStatePath } from '../../agent-mesh-check/scripts/mesh.mjs'
import { loadRouting, statePath, readState, blockCli, readMesh, candidates } from './route.mjs'

const usage = `用法：node ask.mjs (--to <${CLIS.join('|')}> | --type <類型> | --tier <top|standard|cheap>)
  [--model <模型>] [--effort <low|medium|high|xhigh|max>] [--timeout <秒，預設 600>] [--cwd <目錄>]
  [--out <結果檔，預設 <prompt 檔>.out.md>] [--state <狀態檔>] [--mesh <agent-mesh last.json>] <prompt 檔>`

const fmt = t => new Date(t).toISOString().replace('T', ' ').slice(0, 16)

export function summarize(text, limit = 16000, head = 4000, file) {
  if (text.length <= limit) return text
  return `${text.slice(0, head)}\n…（以下省略）\n全文 ${text.length} 字元，見 ${file}`
}

async function main(argv) {
  const o = { timeout: 600, cwd: process.cwd() }
  let file = null
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--help' || a === '-h') { console.log(usage); return 0 }
    const key = { '--to': 'to', '--type': 'type', '--tier': 'tier', '--model': 'model', '--effort': 'effort',
      '--timeout': 'timeout', '--cwd': 'cwd', '--out': 'out', '--state': 'state', '--mesh': 'mesh' }[a]
    if (key) o[key] = argv[++i]
    else if (!file) file = a
    else { console.error(usage); return 2 }
  }
  if (!file || (o.to ? !CLIS.includes(o.to) : !(o.type || o.tier))) { console.error(usage); return 2 }
  if (o.to && !resolveBin(o.to)) { console.error(`${o.to} 不在 PATH 上（未安裝？）`); return 127 }
  let prompt
  try { prompt = readFileSync(file, 'utf8') } catch (e) { console.error(`讀不到 prompt 檔：${e.message}`); return 2 }

  const stateFile = o.state ?? statePath()
  const routing = loadRouting()
  let list, reason
  if (o.to) {
    // 指定對象：不查表；模型與等級照 --model／--effort，沒給就不帶參數（用該 CLI 自己的預設）
    list = [{ cli: o.to }]; reason = '使用者指定'
  } else {
    try {
      list = candidates({ type: o.type, tier: o.tier, routing, state: readState(stateFile),
        available: readMesh(o.mesh ?? meshStatePath(process.env)), now: Date.now() })
    } catch (e) { console.error(e.message); return 2 }
    reason = o.type ?? o.tier
  }

  // 參數擋不住寫檔的 CLI（agy）只能靠指示；四家一律加，行為一致。
  const guarded = `唯讀任務：不要建立、修改或刪除任何檔案，不要執行有副作用的指令；只讀取與回答。\n\n${prompt}`
  for (let i = 0; i < list.length; i++) {
    const c = { ...list[i], ...(o.model && { model: o.model }), ...(o.effort && { effort: o.effort }) }
    const bin = resolveBin(c.cli)
    if (!bin) {
      console.error(`${c.cli} 不在 PATH 上（未安裝？）`)
      if (o.to) return 127
      continue
    }
    const r = await run(bin, buildArgs(c.cli, 'ask', guarded, c), { cwd: o.cwd, timeoutMs: o.timeout * 1000, env: scrubEnv(process.env) })
    const q = r.code !== 0 && !r.timedOut ? quotaInfo(r.out) : null
    if (q) {
      blockCli(stateFile, c.cli, q.resetAt, 'quota')
      const next = list.slice(i + 1).find(n => resolveBin(n.cli))
      console.error(`[ask] ${c.cli} 額度用盡，封鎖到 ${fmt(q.resetAt)}${next && !o.to ? `，改派 ${next.cli}` : ''}`)
      if (o.to) { process.stdout.write(r.out); return r.code ?? 1 }
      continue
    }
    const out = o.out ?? `${file}.out.md`
    if (r.out.length > 16000) writeFileSync(out, r.out)
    console.log(`[ask] 交給 ${c.cli}（${c.model ?? '預設模型'}／${c.effort ?? '預設等級'}），理由：${reason}`)
    process.stdout.write(summarize(r.out, 16000, 4000, out))
    if (r.timedOut) { console.error(`\n[ask] ${c.cli} 超過 ${o.timeout} 秒，已中斷`); return 124 }
    return r.code ?? 1
  }
  const blocks = Object.values(readState(stateFile).blocks).map(b => b.until).filter(t => t > Date.now())
  console.error(`[ask] 沒有可用的候選（未安裝、未通過 agent-mesh-check 或額度封鎖中）${blocks.length ? `；最早 ${fmt(Math.min(...blocks))} 解封` : ''}`)
  return 75
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).then(code => { process.exitCode = code })
}
