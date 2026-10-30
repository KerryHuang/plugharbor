#!/usr/bin/env node
// 派工短問答：把 prompt 檔交給另一個 agent CLI 以唯讀模式跑一輪，原樣印出它的輸出。
// exit：目標 CLI 的 exit code；逾時 124；PATH 上找不到 127；用法錯誤 2。
import { readFileSync } from 'node:fs'
import { CLIS, resolveBin, buildArgs, scrubEnv, run } from '../../agent-mesh-check/scripts/clis.mjs'

const usage = `用法：node ask.mjs --to <${CLIS.join('|')}> [--timeout <秒，預設 600>] [--cwd <目錄>] <prompt 檔>`

async function main(argv) {
  let to = null, timeout = 600, cwd = process.cwd(), file = null
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--help' || a === '-h') { console.log(usage); return 0 }
    else if (a === '--to') to = argv[++i]
    else if (a === '--timeout') timeout = Number(argv[++i])
    else if (a === '--cwd') cwd = argv[++i]
    else if (!file) file = a
    else { console.error(usage); return 2 }
  }
  if (!CLIS.includes(to) || !file) { console.error(usage); return 2 }
  const bin = resolveBin(to)
  if (!bin) { console.error(`${to} 不在 PATH 上（未安裝？）`); return 127 }
  let prompt
  try { prompt = readFileSync(file, 'utf8') } catch (e) { console.error(`讀不到 prompt 檔：${e.message}`); return 2 }
  // 參數擋不住寫檔的 CLI（agy）只能靠指示；四家一律加，行為一致。
  const guarded = `唯讀任務：不要建立、修改或刪除任何檔案，不要執行有副作用的指令；只讀取與回答。\n\n${prompt}`
  const r = await run(bin, buildArgs(to, 'ask', guarded), { cwd, timeoutMs: timeout * 1000, env: scrubEnv(process.env) })
  process.stdout.write(r.out)
  if (r.timedOut) { console.error(`\n[ask] ${to} 超過 ${timeout} 秒，已中斷`); return 124 }
  return r.code ?? 1
}

main(process.argv.slice(2)).then(code => { process.exitCode = code })
