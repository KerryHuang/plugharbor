// 操作員 upload／select／as。需要 Chrome 與 playwright-core，缺任一就跳過（playwright-core 需裝在執行 node --test 的目前目錄）。
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { findPlaywright, loadPlaywright } from './lib/deps.mjs'
import { createActor } from './lib/actor.mjs'

const CHROMES = process.env.CHROME_PATH ? [process.env.CHROME_PATH] : ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/opt/google/chrome/chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe']
const skip = !CHROMES.some((c) => c && existsSync(c)) ? '找不到系統 Chrome' : !findPlaywright() ? '目前目錄找不到 playwright-core' : false

async function withPage(fn) {
  const { chromium } = loadPlaywright()
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH, headless: true } : { channel: 'chrome', headless: true })
  try {
    const ctx = await browser.newContext()
    const page = await ctx.newPage()
    page.setDefaultTimeout(5000)
    // about:blank 沒有 sessionStorage，游標會壞；用假網址承載 HTML
    page.setContent = async (html) => {
      await page.route('http://demo.test/page', (route) => route.fulfill({ contentType: 'text/html; charset=utf-8', body: html }))
      await page.goto('http://demo.test/page')
    }
    await fn(page, ctx)
  } finally { await browser.close() }
}

const SELECT_HTML = `<body><input aria-label="假別" readonly>
<script>
const i = document.querySelector('input')
i.addEventListener('click', () => {
  const m = document.createElement('ul'); m.setAttribute('role', 'listbox'); m.className = 'my-menu'
  for (const t of ['特休', '事假']) { const li = document.createElement('li'); li.textContent = t; li.onclick = () => { i.value = t; m.remove() }; m.appendChild(li) }
  document.body.appendChild(m)
})
</script></body>`

test('a.upload：點按鈕觸發 file chooser，相對路徑以 fileRoot 為準（AC-9）', { skip }, async () => {
  const root = mkdtempSync(join(tmpdir(), 'dv-actor-'))
  writeFileSync(join(root, 'sample.png'), 'x')
  await withPage(async (page) => {
    await page.setContent(`<body><button id=b onclick="document.getElementById('f').click()">上傳</button>
<input id=f type=file hidden onchange="document.getElementById('name').textContent=this.files[0].name"><div id=name></div></body>`)
    const a = createActor(page, { moveMs: 10, fileRoot: root })
    await a.upload(page.locator('#b'), 'sample.png')
    assert.equal(await page.locator('#name').textContent(), 'sample.png')
  })
})

test('a.select：字串 label 開浮層並點選項（AC-10）', { skip }, async () => {
  await withPage(async (page) => {
    await page.setContent(SELECT_HTML)
    const a = createActor(page, { moveMs: 10 })
    await a.select('假別', '特休')
    assert.equal(await page.getByLabel('假別').inputValue(), '特休')
  })
})

test('a.select：ui.menu 指定浮層容器（AC-10）', { skip }, async () => {
  await withPage(async (page) => {
    await page.setContent(SELECT_HTML)
    const a = createActor(page, { moveMs: 10, ui: { menu: '.my-menu' } })
    await a.select(page.getByLabel('假別'), '事假')
    assert.equal(await page.getByLabel('假別').inputValue(), '事假')
  })
})

test('a.as：先 login 再 reload／goto（AC-11）', { skip }, async () => {
  await withPage(async (page, ctx) => {
    await page.route('http://demo.test/**', (route) => route.fulfill({
      contentType: 'text/html; charset=utf-8',
      body: `<body><div id=who></div><script>document.getElementById('who').textContent = (document.cookie.match(/u=(\\w+)/) || [])[1] || 'none'</script></body>`,
    }))
    await page.goto('http://demo.test/')
    const login = async (p, userId) => { await ctx.addCookies([{ name: 'u', value: userId, url: 'http://demo.test/' }]) }
    const a = createActor(page, { moveMs: 10, login })
    await a.as('user02')
    assert.equal(await page.locator('#who').textContent(), 'user02')
    await a.as('user03', '/next')
    assert.equal(await page.locator('#who').textContent(), 'user03')
    assert.match(page.url(), /\/next$/)
  })
})

test('a.as 沒有 login 要拋錯（AC-12）', { skip }, async () => {
  await withPage(async (page) => {
    const a = createActor(page, { moveMs: 10 })
    await assert.rejects(() => a.as('user02'), { message: '配方沒有 login，不能用 a.as' })
  })
})
