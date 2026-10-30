#!/usr/bin/env node
// Codex／agy 的 Stop hook：stdin 原樣交給 plugharbor repo 內的 notification.sh，通知規則只維護在那一支。
// 純通知用途，任何失敗都不得影響主流程。
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

// Windows 的 Codex（PowerShell）與 agy（cmd）PATH 上的裸 bash 是 WSL，讀不到 C:/ 路徑；
// 從 git.exe 的位置推回 Git Bash（<Git>\cmd\git.exe 或 <Git>\mingw64\bin\git.exe），找不到才退回裸 bash。
function bashBin() {
  if (process.platform !== 'win32') return 'bash'
  const git = spawnSync('where', ['git'], { encoding: 'utf8' }).stdout?.split(/\r?\n/)[0]?.trim()
  if (!git) return 'bash'
  return [join(dirname(git), '..', 'bin', 'bash.exe'), join(dirname(git), '..', '..', 'bin', 'bash.exe')].find(existsSync) ?? 'bash'
}

// repo 路徑記在 support/plugharbor/repo；找不到腳本時退回 ~/.claude/hooks，都沒有就不做事。
export function notificationScript(home = homedir()) {
  try {
    const file = join(home, '.codex/support/plugharbor/repo')
    const repo = existsSync(file) ? readFileSync(file, 'utf8').trim() : ''
    const inRepo = repo && join(repo, 'plugins', 'toolkit', 'hooks', 'notification.sh')
    if (inRepo && existsSync(inRepo)) return inRepo
  } catch {}
  const legacy = join(home, '.claude/hooks/notification.sh')
  return existsSync(legacy) ? legacy : null
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  let input = ''
  try { input = readFileSync(0, 'utf8') } catch {}
  try {
    const found = notificationScript()
    if (found) spawnSync(bashBin(), [found.replace(/\\/g, '/')], { input, stdio: ['pipe', 'ignore', 'ignore'], timeout: 8000 })
  } catch {}
  // agy 的 hook 一律要在 stdout 回 JSON；Codex 的 Stop 收到空輸出即視為成功
  if (input.includes('"terminationReason"')) process.stdout.write('{}')
}
