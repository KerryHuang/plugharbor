#!/usr/bin/env node
import { syncUser } from './sync-user.mjs'
import { homedir } from 'node:os'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

try {
  // installSupport 把來源 repo 路徑寫在同目錄的 repo 檔；repo 不在了就靜默略過。
  const file = join(dirname(fileURLToPath(import.meta.url)), 'repo')
  const repo = existsSync(file) ? readFileSync(file, 'utf8').trim() : ''
  if (repo && existsSync(join(repo, 'setup/home'))) {
    const { changed } = syncUser({ home: homedir(), repo })
    if (changed.length) {
      const root = changed.includes('.codex/AGENTS.md') ? readFileSync(join(homedir(), '.codex/AGENTS.md'), 'utf8') : ''
      process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: `plugharbor 來源已更新，Codex 同步 ${changed.length} 個檔。agent catalog 變更需新 session 才能完整驗收。\n${root}` } }))
    }
  }
} catch (error) { console.error(`[plugharbor sync] ${error.message}`); process.exitCode = 1 }
