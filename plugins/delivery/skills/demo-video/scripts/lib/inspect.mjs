// 失敗時列出畫面上可互動的元素（accessible name），讓腳本作者知道該改點哪個。

// 在瀏覽器內執行：可見的 button、link、checkbox、tab、menuitem、option，以及有 label 的欄位
function collect() {
  const SEL = 'button,a[href],select,textarea,input:not([type=hidden]),[role=button],[role=link],[role=checkbox],[role=tab],[role=menuitem],[role=option]'
  const clean = (s) => (s ?? '').replace(/\s+/g, ' ').trim()
  const visible = (el) => {
    const st = getComputedStyle(el)
    return st.visibility !== 'hidden' && st.display !== 'none' && el.getClientRects().length > 0
  }
  const nameOf = (el) => {
    const lb = el.getAttribute('aria-labelledby')
    if (lb) { const t = clean(lb.split(/\s+/).map((id) => document.getElementById(id)?.textContent).join(' ')); if (t) return t }
    const al = clean(el.getAttribute('aria-label'))
    if (al) return al
    const labels = el.labels ? [...el.labels].map((l) => l.textContent).join(' ') : ''
    if (clean(labels)) return clean(labels)
    const type = (el.getAttribute('type') ?? '').toLowerCase()
    if (el.tagName === 'INPUT' && ['button', 'submit', 'reset'].includes(type)) return clean(el.value)
    const text = clean(el.textContent)
    if (text && !['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return text
    return clean(el.getAttribute('title')) || clean(el.getAttribute('alt')) || clean(el.getAttribute('placeholder'))
  }
  const names = []
  for (const el of document.querySelectorAll(SEL)) {
    if (!visible(el)) continue
    const n = nameOf(el)
    if (n && !names.includes(n)) names.push(n)
  }
  return names.slice(0, 40)
}

export async function listInteractive(page) {
  try { return await page.evaluate(collect) } catch { return [] }
}
