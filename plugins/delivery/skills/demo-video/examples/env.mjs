// 範例錄影環境配方（靜態頁）。欄位說明見 references/script-format.md 的「錄影環境配方」。
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

export default {
  build: async () => {}, // 靜態頁，不用建置
  reset: async () => { console.log('範例是靜態頁，沒有資料要清') },
  start: {
    cmd: [process.execPath, join(here, 'serve.mjs')], // 路徑可能含空白，用陣列
    portEnv: 'PORT',
    readyPath: '/ready',
  },
  tts: { provider: 'edge', licensed: false },
}
