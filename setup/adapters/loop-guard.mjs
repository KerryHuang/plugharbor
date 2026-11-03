#!/usr/bin/env node
// Codex 的 PostToolUse hook：stdin 原樣交給 plugharbor repo 內的 loop-guard.py，判斷邏輯只維護在那一支。
// 輸出（additionalContext／systemMessage）原樣轉回 Codex；任何失敗都靜默放行。
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { homedir } from 'node:os'
import { join } from 'node:path'

// repo 路徑記在 support/plugharbor/repo；找不到腳本就不做事。
export function loopGuardScript(home = homedir()) {
  try {
    const file = join(home, '.codex/support/plugharbor/repo')
    const repo = existsSync(file) ? readFileSync(file, 'utf8').trim() : ''
    const script = repo && join(repo, 'plugins', 'toolkit', 'hooks', 'loop-guard.py')
    return script && existsSync(script) ? script : null
  } catch { return null }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    let raw = ''
    for await (const chunk of process.stdin) raw += chunk
    const script = loopGuardScript()
    if (script) {
      for (const py of process.platform === 'win32' ? ['python', 'py', 'python3'] : ['python3', 'python']) {
        const r = spawnSync(py, [script], { input: raw, encoding: 'utf8', timeout: 8000 })
        // 只有找不到直譯器（ENOENT，或 Windows 的 python 別名 stub 非零退出）才換下一個；逾時不重跑，免得超過 hook 上限。
        if (r.error?.code === 'ENOENT' || (!r.error && r.status !== 0)) continue
        if (r.stdout) process.stdout.write(r.stdout)
        break
      }
    }
  } catch {}
}
