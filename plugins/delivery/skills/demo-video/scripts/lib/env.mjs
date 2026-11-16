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
  if (preferred && !listenerPids(preferred).length) { const p = await tryListen(preferred); if (p) return p }
  return tryListen(0)
}

export function listenerPids(port) {
  if (process.platform !== 'win32') {
    const r = spawnSync('lsof', ['-t', `-iTCP:${port}`, '-sTCP:LISTEN'], { encoding: 'utf8' })
    if (r.error?.code === 'ENOENT') throw new Error('需要 lsof 才能判斷監聽者（請安裝 lsof）')
    return String(r.stdout ?? '').split('\n').map(Number).filter((n) => n > 0)
  }
  try {
    const pids = []
    for (const line of sh('netstat', ['-ano']).split(/\r?\n/)) {
      const f = line.trim().split(/\s+/)
      if (f[0] === 'TCP' && f[3] === 'LISTENING' && f[1].endsWith(`:${port}`)) pids.push(Number(f[4]))
    }
    return pids
  } catch { return [] }
}

export const listenerPid = (port) => listenerPids(port)[0] ?? null

const pgidOf = (pid) => Number(spawnSync('ps', ['-o', 'pgid=', '-p', String(pid)], { encoding: 'utf8' }).stdout.trim())

// 監聽者屬於我們起的程序：POSIX 看 process group（啟動器形式的 cmd 也成立），win32 看 pid
const ownsListener = (port, childPid) =>
  listenerPids(port).some((p) => (process.platform === 'win32' ? p === childPid : p === childPid || pgidOf(p) === childPid))

const isAlive = (pid) => { try { process.kill(pid, 0); return true } catch (e) { return e.code === 'EPERM' } }

export function acquireLock(dataDir) {
  mkdirSync(dataDir, { recursive: true })
  const file = join(dataDir, '.lock')
  for (let i = 0; i < 2; i++) {
    try {
      writeFileSync(file, String(process.pid), { flag: 'wx' })
      // 只刪 pid 是自己的鎖；可重複呼叫、同步
      return () => { try { if (readFileSync(file, 'utf8') === String(process.pid)) rmSync(file, { force: true }) } catch {} }
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

// lock：呼叫端已先拿好的鎖（acquireLock 的回傳值），有傳就不再自己拿；stop／killSync 都會釋放它
export async function startEnv(recipe, { videoRoot, outDir, log = console.log, register, lock } = {}) {
  const dataDir = join(videoRoot, '.data')
  const release = lock ?? acquireLock(dataDir)
  let child = null
  let exited = null
  let stopped = false
  let stopping = null
  const groupAlive = () => { try { process.kill(-child.pid, 0); return true } catch { return false } }
  const posix = process.platform !== 'win32'
  const waitGone = async (ms) => {
    const end = Date.now() + ms
    while (Date.now() < end && (posix ? groupAlive() : !exited)) await sleep(50)
    return posix ? !groupAlive() : !!exited
  }
  // 同步收尾，給 process.on('exit') 用：行程崩潰時 detached 的 server 不會跟著死
  const killSync = () => {
    try { if (child?.pid) { if (posix) process.kill(-child.pid, 'SIGTERM'); else process.kill(child.pid) } } catch {}
    release()
  }
  const stop = () => {
    stopped = true
    stopping ??= (async () => {
      try {
        if (child?.pid && (posix ? groupAlive() : !exited)) {
          if (posix) { try { process.kill(-child.pid, 'SIGTERM') } catch {} } else child.kill()
          if (!(await waitGone(5000))) {
            if (posix) { try { process.kill(-child.pid, 'SIGKILL') } catch {} } else child.kill('SIGKILL')
            await waitGone(2000)
          }
        }
      } finally { release() }
    })()
    return stopping
  }
  register?.(stop, killSync)
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
    if (stopped) throw Object.assign(new Error('已中止'), { aborted: true })

    mkdirSync(outDir, { recursive: true })
    const logFile = join(outDir, 'server.log')
    const [cmd, ...args] = Array.isArray(start.cmd) ? start.cmd : start.cmd.trim().split(/\s+/)
    const fd = openSync(logFile, 'w')
    try {
      child = spawn(cmd, args, { cwd: resolve(videoRoot, start.cwd ?? '.'), env, stdio: ['ignore', fd, fd], windowsHide: true, detached: process.platform !== 'win32' })
    } finally { closeSync(fd) }
    child.on('error', (e) => { exited = e })
    child.on('exit', (code) => { exited ??= { code } })

    const deadline = Date.now() + (start.readyTimeoutMs ?? 60000)
    const url = `http://127.0.0.1:${port}`
    while (!stopped && !exited && Date.now() < deadline) {
      if (child.pid && ownsListener(port, child.pid) && (await ping(url + start.readyPath))) {
        log(`就緒：pid ${child.pid}，埠 ${port}`)
        return { url, pid: child.pid, stop, killSync }
      }
      await sleep(250)
    }
    if (stopped) throw Object.assign(new Error('已中止'), { aborted: true })
    throw new Error(`server 未就緒（log：${logFile}）`)
  } catch (e) {
    await stop()
    throw e
  }
}
