// 範例用的靜態站：讀環境變數 PORT，提供 leave-request/index.html；/ready 回 200。
import { createServer } from 'node:http'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const page = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'leave-request', 'index.html'))
createServer((req, res) => {
  if (req.url === '/ready') { res.writeHead(200).end('ok'); return }
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }).end(page)
}).listen(Number(process.env.PORT), '127.0.0.1')
