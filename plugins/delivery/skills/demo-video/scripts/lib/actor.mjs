// 操作員：把「點、輸入、移動」放慢並加上游標與點擊漣漪，錄影畫面沒有真實游標，觀眾才跟得上。

import { resolve } from 'node:path'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export async function installCursor(page) {
  await page.addInitScript(() => {
    addEventListener('DOMContentLoaded', () => {
      const c = document.createElement('div')
      c.id = '__cursor'
      c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 11-7 1.5L9.5 22z" fill="#111" stroke="#fff" stroke-width="1.6"/></svg>'
      c.style.cssText = 'position:fixed;left:640px;top:360px;z-index:2147483647;pointer-events:none;transition:left .5s cubic-bezier(.3,.8,.3,1),top .5s cubic-bezier(.3,.8,.3,1)'
      document.documentElement.appendChild(c)
      // 換頁後游標位置保留
      const st = sessionStorage.getItem('__c')
      if (st) { const [x, y] = st.split(','); c.style.left = `${x}px`; c.style.top = `${y}px` }
    })
  })
}

// 開始錄影後呼叫：畫面靜止時 screencast 不送影格，動一下游標才有第一格
export async function nudgeCursor(page) {
  await page.evaluate(() => { const c = document.getElementById('__cursor'); if (c) c.style.left = '660px' })
  await sleep(700)
}

export function createActor(page, { moveMs = 560, typeDelay = 85, ui, login, fileRoot = process.cwd() } = {}) {
  const a = {
    p: page,
    pause: sleep,
    async move(loc) {
      await loc.waitFor()
      await loc.scrollIntoViewIfNeeded()
      const b = await loc.boundingBox()
      const x = b.x + b.width / 2
      const y = b.y + b.height / 2
      await page.evaluate(([x, y]) => {
        const c = document.getElementById('__cursor')
        if (c) { c.style.left = `${x}px`; c.style.top = `${y}px` }
        sessionStorage.setItem('__c', `${x},${y}`)
      }, [x, y])
      await sleep(moveMs)
      return { x, y }
    },
    // 游標移過去之外，也要觸發真正的 hover（選單、tooltip 才會出現）
    async hover(loc) { await a.move(loc); await loc.hover() },
    async click(loc) {
      const { x, y } = await a.move(loc)
      await page.evaluate(([x, y]) => {
        const r = document.createElement('div')
        r.style.cssText = `position:fixed;left:${x - 18}px;top:${y - 18}px;width:36px;height:36px;border-radius:50%;background:rgba(25,118,210,.35);z-index:2147483646;pointer-events:none;transition:transform .35s,opacity .35s`
        document.documentElement.appendChild(r)
        requestAnimationFrame(() => { r.style.transform = 'scale(1.7)'; r.style.opacity = '0' })
        setTimeout(() => r.remove(), 400)
      }, [x, y])
      await loc.click()
      await sleep(350)
    },
    // 逐字輸入，觀眾看得到打字過程
    async type(loc, text) { await a.click(loc); await loc.pressSequentially(text, { delay: typeDelay }); await sleep(200) },
    async fill(loc, v) { await a.click(loc); await loc.fill(v); await sleep(300) },
    // 先等 file chooser 再點按鈕；相對路徑以影片目錄為準
    async upload(button, file) {
      const chooser = page.waitForEvent('filechooser')
      await a.click(button)
      await (await chooser).setFiles(resolve(fileRoot, file))
      await sleep(300)
    },
    // 點開下拉後，在最後一個浮層容器（ui.menu，預設 [role=listbox]）裡點選項
    async select(label, option) {
      await a.click(typeof label === 'string' ? page.getByLabel(label) : label)
      const menu = page.locator(ui?.menu ?? '[role=listbox]').last()
      await a.click(menu.getByText(option, { exact: true }))
    },
    // 換使用者：配方的 login 設好身分後重載；path 相對於目前 origin
    async as(userId, path) {
      if (!login) throw new Error('配方沒有 login，不能用 a.as')
      await login(page, userId)
      if (path) await page.goto(new URL(path, page.url()).href)
      else await page.reload()
      await sleep(300)
    },
  }
  return a
}
