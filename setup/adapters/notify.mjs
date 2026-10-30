#!/usr/bin/env node
// Codex／agy 的 Stop hook：stdin 原樣交給 ~/.claude/hooks/notification.sh，通知規則只維護在那一支。
// 純通知用途，任何失敗都不得影響主流程。
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
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

let input = ''
try { input = readFileSync(0, 'utf8') } catch {}
try {
  const script = join(homedir(), '.claude/hooks/notification.sh').replace(/\\/g, '/')
  spawnSync(bashBin(), [script], { input, stdio: ['pipe', 'ignore', 'ignore'], timeout: 8000 })
} catch {}
// agy 的 hook 一律要在 stdout 回 JSON；Codex 的 Stop 收到空輸出即視為成功
if (input.includes('"terminationReason"')) process.stdout.write('{}')
