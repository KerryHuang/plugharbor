#!/usr/bin/env node
import { pathToFileURL } from 'node:url'

// 僅辨識直接的 Git 命令與常見 shell -c；不是任意程式碼的安全邊界。
export function inspectCommand(command) {
  const words = []
  let word = '', quote = '', escaped = false
  const flush = () => { if (word) words.push(word); word = '' }
  for (const char of command) {
    if (escaped) { word += char; escaped = false; continue }
    if (char === '\\' && quote !== "'") { escaped = true; continue }
    if (quote) { if (char === quote) quote = ''; else word += char; continue }
    if (char === '"' || char === "'") { quote = char; continue }
    if (/\s/.test(char)) { flush(); if (char === '\n') words.push('\0;'); continue }
    if (';&|()'.includes(char)) { flush(); words.push('\0' + char); continue }
    word += char
  }
  flush()
  let commandStart = true
  for (let i = 0; i < words.length; i++) {
    if (words[i].startsWith('\0')) { commandStart = true; continue }
    if (!commandStart) continue
    if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(words[i]) || ['env', 'command', 'sudo'].includes(words[i])) continue
    commandStart = false
    if (['sh', 'bash', 'zsh'].includes(words[i].split('/').at(-1)) && /^-[^-]*c/.test(words[i + 1] ?? '')) {
      const reason = inspectCommand(words[i + 2] ?? '')
      if (reason) return reason
    }
    if (words[i].split('/').at(-1) !== 'git') continue
    let j = i + 1
    while (words[j]?.startsWith('-')) {
      if (['-C', '-c', '--git-dir', '--work-tree'].includes(words[j])) j += 2
      else j++
    }
    const action = words[j++]
    const args = []
    while (j < words.length && !words[j].startsWith('\0')) args.push(words[j++])
    if (action === 'add' && args.some(x => x === '.' || /^-[^-]*A/.test(x) || x === '--all')) return '禁止全量 staging，請逐檔指名。'
    if (action === 'tag' && args.length && !args.some(x => ['--list', '-l'].includes(x))) return '版本由 Semantic Release 管理，不手動建立或刪除 tag。'
    if (action === 'push' && args.some(x => /^-[^-]*[fd]/.test(x) || x.startsWith('+') || x.startsWith('--force') || x === '--delete' || x === '-d' || x.startsWith(':'))) return 'force push／刪遠端分支需先列確切指令並取得人工同意。'
    if (action === 'reset' && args.includes('--hard')) return 'reset --hard 需先確認影響範圍並取得人工同意。'
    if (action === 'clean' && args.some(x => x === '--force' || /^-[^-]*f/.test(x)) && args.some(x => /^-[^-]*d/.test(x))) return 'clean -fd 需先確認影響範圍並取得人工同意。'
  }
  return null
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    let raw = ''
    for await (const chunk of process.stdin) raw += chunk
    const payload = JSON.parse(raw)
    const command = payload.tool_input?.command ?? payload.tool_input?.cmd
    const reason = typeof command === 'string' ? inspectCommand(command) : null
    if (reason) process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: reason + ' 本 guard 不辨識對話授權；有已核准例外時需在 /hooks 明確停用此 guard，完成後恢復。' } }))
  } catch (error) { console.error(`[Git guard] ${error.message}`); process.exitCode = 2 }
}
