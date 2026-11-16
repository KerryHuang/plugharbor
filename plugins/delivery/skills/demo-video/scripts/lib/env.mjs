// 錄影環境配方：載入、起站、就緒判定、收尾。
import { spawn, spawnSync } from 'node:child_process'
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:net'
import { dirname, join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { sh } from './media.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export function findEnv(scriptPath) {
  const p = join(dirname(resolve(scriptPath)), '..', 'env.mjs')
  return existsSync(p) ? resolve(p) : null
}

export async function loadEnv(envPath) {
  const r = (await import(pathToFileURL(resolve(envPath)).href)).default
  const errs = []
  const need = (path, ok, example) => { if (!ok) errs.push(`✗ ${path}：缺少或型別不對\n  正確範例：${example}`) }
  need('build', typeof r?.build === 'function', 'build({ root, sh }) { ... }')
  need('reset', typeof r?.reset === 'function', 'reset({ dataDir, sh, env }) { ... }')
  const c = r?.start?.cmd
  need('start.cmd', (typeof c === 'string' && c.trim()) || (Array.isArray(c) && c.length > 0), "cmd: ['node', 'server.js']")
  need('start.portEnv', typeof r?.start?.portEnv === 'string' && r.start.portEnv, "portEnv: 'PORT'")
  need('start.readyPath', typeof r?.start?.readyPath === 'string' && r.start.readyPath, "readyPath: '/health'")
  if (errs.length) throw new Error([...errs, `✗ ${errs.length} 個錯誤；沒有開始起站`].join('\n'))
  return r
}

const tryListen = (port) => new Promise((res) => {
  const s = createServer()
  s.once('error', () => res(null))
  s.listen(port, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)) })
})

export async function findFreePort(preferred) {
  if (preferred) { const p = await tryListen(preferred); if (p) return p }
  return tryListen(0)
}

export function listenerPid(port) {
  try {
    if (process.platform === 'win32') {
      for (const line of sh('netstat', ['-ano']).split(/\r?\n/)) {
        const f = line.trim().split(/\s+/)
        if (f[0] === 'TCP' && f[3] === 'LISTENING' && f[1].endsWith(`:${port}`)) return Number(f[4])
      }
      return null
    }
    const out = spawnSync('lsof', ['-t', `-iTCP:${port}`, '-sTCP:LISTEN'], { encoding: 'utf8' }).stdout
    const pid = Number(out.split('\n')[0])
    return pid > 0 ? pid : null
  } catch { return null }
}

const isAlive = (pid) => { try { process.kill(pid, 0); return true } catch (e) { return e.code === 'EPERM' } }

export function acquireLock(dataDir) {
  mkdirSync(dataDir, { recursive: true })
  const file = join(dataDir, '.lock')
  for (let i = 0; i < 2; i++) {
    try {
      writeFileSync(file, String(process.pid), { flag: 'wx' })
      return () => rmSync(file, { force: true })
    } catch (e) {
      if (e.code !== 'EEXIST') throw e
      const pid = Number(readFileSync(file, 'utf8'))
      if (pid > 0 && isAlive(pid)) throw new Error(`已有一個 demo-video 在跑（pid ${pid}）`)
      rmSync(file, { force: true })
    }
  }
  throw new Error('無法取得鎖檔')
}

async function ping(url) {
  try { return (await fetch(url, { signal: AbortSignal.timeout(2000) })).ok } catch { return false }
}

export async function startEnv(recipe, { videoRoot, outDir, log = console.log, register } = {}) {
  const dataDir = join(videoRoot, '.data')
  const release = acquireLock(dataDir)
  let child = null
  let exited = null
  let stopped = false
  const stop = async () => {
    if (stopped) return
    stopped = true
    if (child && !exited) {
      const done = new Promise((r) => child.once('exit', r))
      child.kill()
      if ((await Promise.race([done, sleep(5000).then(() => 'timeout')])) === 'timeout') {
        child.kill('SIGKILL')
        await Promise.race([done, sleep(2000)])
      }
    }
    release()
  }
  register?.(stop)
  const step = async (name, fn) => {
    try { return await fn() } catch (e) { throw new Error(`配方 ${name} 失敗：${e.message}`) }
  }
  try {
    const { start } = recipe
    await step('build', () => recipe.build({ root: videoRoot, sh }))
    const port = await findFreePort(start.port)
    const env = { ...process.env, ...start.env, [start.portEnv]: String(port) }
    await step('reset', () => recipe.reset({ dataDir, sh, env }))
    log('reset 完成')
    if (stopped) throw new Error('已中止')

    mkdirSync(outDir, { recursive: true })
    const logFile = join(outDir, 'server.log')
    const [cmd, ...args] = Array.isArray(start.cmd) ? start.cmd : start.cmd.trim().split(/\s+/)
    const fd = openSync(logFile, 'w')
    try {
      child = spawn(cmd, args, { cwd: resolve(videoRoot, start.cwd ?? '.'), env, stdio: ['ignore', fd, fd], windowsHide: true })
    } finally { closeSync(fd) }
    child.on('error', (e) => { exited = e })
    child.on('exit', (code) => { exited ??= { code } })

    const deadline = Date.now() + (start.readyTimeoutMs ?? 60000)
    const url = `http://127.0.0.1:${port}`
    while (!stopped && !exited && Date.now() < deadline) {
      if (child.pid && listenerPid(port) === child.pid && (await ping(url + start.readyPath))) {
        log(`就緒：pid ${child.pid}，埠 ${port}`)
        return { url, pid: child.pid, stop }
      }
      await sleep(250)
    }
    throw new Error(`server 未就緒（log：${logFile}）`)
  } catch (e) {
    await stop()
    throw e
  }
}
