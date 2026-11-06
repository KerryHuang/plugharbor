import { createRequire } from 'node:module'
import { join } from 'node:path'

// playwright-core 裝在「工作目錄」（目前目錄的 node_modules），不裝進 skill 也不全域安裝。
export function findPlaywright() {
  try {
    return createRequire(join(process.cwd(), 'noop.js'))('playwright-core')
  } catch {
    return null
  }
}

export function loadPlaywright() {
  const pw = findPlaywright()
  if (!pw) throw new Error('找不到 playwright-core：在工作目錄執行 npm install playwright-core（或跑 ensure-tools.sh --dir <工作目錄>），並在該目錄下執行引擎。')
  return pw
}
