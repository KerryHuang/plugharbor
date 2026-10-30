#!/usr/bin/env node
// 狀態圖示用 herdr 內建的 state_icon（2026-10-27 起不再寫 emoji state_labels，並清掉舊的），這裡只回報 tab 名稱 token：
// - 同一個 tab 有多個 agent pane 時加上「(序號/總數)」，側欄才分得出是同一個 tab 下的不同 pane。
// - 依狀態寫進 $where_<狀態>（其餘四個清空）：sidebar 上色規則只能比對 token 自己的值，
//   要讓 tab 名稱依狀態變色，只能每種狀態一個 token 各自設樣式。
// 重複回報無副作用，所以每次全量重算，不追蹤哪些已補過。
// 用 node 寫、不依賴 sh／jq，macOS 與 Windows 共用同一份；參數一律以陣列傳給 herdr，不經 shell（emoji、中文才不會被拆壞）。
// 另外把子智慧體掛在 launcher 底下：launcher 在子 pane 寫 parent_pane（dispatch-worker），或 pi 子智慧體寫 parent_sid
// 對到 parent pane 上的 pi_sid（setup/herdr/pi/herdr-tree.ts）。這裡算出樹線（├─ └─，接在 $where_<狀態> 開頭）與排序鍵 order，
// 再用 agent.view.set 依 order 排 Agents 清單（socket 方法，CLI 送不了）。
import { execFileSync } from 'node:child_process'
import { createConnection } from 'node:net'
import { hostname } from 'node:os'

const herdr = process.env.HERDR_BIN_PATH || 'herdr'
const run = args => execFileSync(herdr, args, { encoding: 'utf8' })
const list = args => JSON.parse(run(args)).result
const STATES = ['blocked', 'working', 'done', 'idle', 'unknown']
const sleep = ms => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)

const event = process.env.HERDR_PLUGIN_EVENT || ''
// pane.exited 在 pane 移除前就發出，稍等一下再讀清單，否則還會把它算進去
if (event === 'pane.exited') sleep(1000)
// focus 事件可能比 seen 旗標先到，稍等再讀
if (event.endsWith('.focused')) sleep(500)

// 依狀態寫進 <prefix>_<狀態>，其餘四個清空
const stateTokens = (prefix, status, value) =>
  STATES.flatMap(s => s === status ? ['--token', `${prefix}_${s}=${value}`] : ['--clear-token', `${prefix}_${s}`])

const tabs = list(['tab', 'list']).tabs
const label = Object.fromEntries(tabs.map(t => [t.tab_id, t.label]))
const agents = list(['agent', 'list']).agents

// 樹：root 依 herdr 原本的 workspace／tab／pane 順序編號，子節點在 parent 鍵後面接 .NNN，字串排序即樹的前序。
// 側欄會把其他 machine 的 agent 併進同一份清單、照各自回報的 order 排，兩台編號會撞（Mac 的 000.001.001 夾進
// Windows 的 parent 與子節點之間），所以最前面加主機名，每台自成一段
const host = hostname().toLowerCase()
const pad = n => String(n).padStart(3, '0')
const wsIdx = Object.fromEntries(list(['workspace', 'list']).workspaces.map((w, i) => [w.workspace_id, i]))
const tabIdx = Object.fromEntries(tabs.map((t, i) => [t.tab_id, i]))
const paneIdx = Object.fromEntries(list(['pane', 'list']).panes.map((p, i) => [p.pane_id, i]))
const tok = a => a.tokens ?? {}
const paneOfSid = new Map(agents.filter(a => tok(a).pi_sid).map(a => [tok(a).pi_sid, a.pane_id]))
const alive = new Set(agents.map(a => a.pane_id))
const parentOf = a => {
  const p = tok(a).parent_pane || paneOfSid.get(tok(a).parent_sid)
  return p && p !== a.pane_id && alive.has(p) ? p : undefined
}
const kids = Map.groupBy(agents.filter(parentOf), parentOf)
const tree = new Map()  // pane_id → { order, indent }
const walk = (a, order, indent, stem) => {
  if (tree.has(a.pane_id)) return
  tree.set(a.pane_id, { order, indent })
  const cs = kids.get(a.pane_id) ?? []
  cs.forEach((c, j) => walk(c, `${order}.${pad(j)}`, stem + (j === cs.length - 1 ? '└─' : '├─'), stem + (j === cs.length - 1 ? '  ' : '│ ')))
}
agents.filter(a => !parentOf(a))
  .map(a => [a, `${host}.${pad(wsIdx[a.workspace_id] ?? 999)}.${pad(tabIdx[a.tab_id] ?? 999)}.${pad(paneIdx[a.pane_id] ?? 999)}`])
  .sort(([, x], [, y]) => x.localeCompare(y))
  .forEach(([a, key]) => walk(a, key, '', ''))
// parent 互指成環的不在樹上，沒有 order，排到最後、不會消失
const treeTokens = a => {
  const t = tree.get(a.pane_id)
  return [...(t ? ['--token', `order=${t.order}`] : ['--clear-token', 'order']),
    '--clear-token', 'tree']  // 舊版的獨立 $tree token，樹線已併進 $where_<狀態>
}

// pane 外框也標 ★（同 dispatch-worker 的 herdr_layout.py）：只加不拿，已是 ★ 開頭的不動
const paneLabel = Object.fromEntries(list(['pane', 'list']).panes.map(p => [p.pane_id, p.label || '']))
for (const a of agents) {
  const cur = paneLabel[a.pane_id] ?? ''
  if (kids.has(a.pane_id) && !cur.startsWith('★')) run(['pane', 'rename', a.pane_id, `★ ${cur || label[a.tab_id] || ''}`.trim()])
}

const byTab = Map.groupBy(agents, a => a.tab_id)
for (const group of byTab.values()) {
  group.forEach((a, i) => {
    let where = (label[a.tab_id] ?? '?') + (group.length > 1 ? ` (${i + 1}/${group.length})` : '')
    // 底下有掛子智慧體／worker 的就是主 session，標 ★（同 dispatch-worker 的 pane 外框）；
    // state_icon 後面 herdr 只接一個空格，不插「 · 」，所以顯示成「● ★ 名稱」。
    // 星號用 Font Awesome 的 U+F005（Nerd Font，同 pi-straw-boss）；pane 外框維持 herdr_layout.py 的 Unicode ★
    if (kids.has(a.pane_id)) where = `\uF005 ${where}`
    // 樹線放進名稱開頭、不另開 token：herdr 在相鄰 token 間固定插「 · 」，只有 state_icon 後面是單一空格
    const indent = tree.get(a.pane_id)?.indent
    if (indent) where = `${indent} ${where}`
    run(['pane', 'report-metadata', a.pane_id, '--source', 'plugharbor-sidebar', '--clear-state-labels',
      '--clear-token', 'main',
      '--clear-token', 'where', ...stateTokens('where', a.agent_status, where), ...treeTokens(a)])
  })
}

// Spaces 面板：workspace 名稱依整體狀態寫進 $space_<狀態>（其餘清空）上色，圖示用內建 state_icon；
// 各狀態 agent 數寫進 $count_<狀態>（「●2」，config 依狀態上色，沒有就清掉），一眼看出這個 workspace 裡誰在等你。
for (const ws of list(['workspace', 'list']).workspaces) {
  const mine = agents.filter(a => a.workspace_id === ws.workspace_id)
  const counts = STATES.flatMap(s => {
    const n = mine.filter(a => a.agent_status === s).length
    return n ? ['--token', `count_${s}=●${n}`] : ['--clear-token', `count_${s}`]
  })
  // 沒有任何 agent 時 herdr 會回 unknown——名稱改用灰色（idle）
  const status = mine.length && STATES.includes(ws.agent_status) ? ws.agent_status : 'idle'
  run(['workspace', 'report-metadata', ws.workspace_id, '--source', 'plugharbor-sidebar',
    '--clear-token', 'counts', ...counts, ...stateTokens('space', status, ws.label)])
}

// Agents 清單依 order 排；每次都重設（set 會整份取代，重複無副作用），server 重啟後的 startup 也會重裝回來。
// 只有以 plugin 身分執行時有 socket 與 plugin id；手動跑 apply.mjs 時略過。
const { HERDR_SOCKET_PATH: socket, HERDR_PLUGIN_ID: pluginId } = process.env
if (socket && pluginId) {
  const params = {
    source: `plugin:${pluginId}`, label: 'tree',
    sort: [{ field: { token: 'order' }, order: 'asc' }, ...['workspace_order', 'tab_order', 'pane_order'].map(field => ({ field, order: 'asc' }))],
  }
  await new Promise(done => {
    const s = createConnection(process.platform === 'win32' ? `\\\\.\\pipe\\${socket}` : socket).setTimeout(5000)
    s.on('connect', () => s.write(`${JSON.stringify({ id: `plugharbor-sidebar-${Date.now()}`, method: 'agent.view.set', params })}\n`))
    s.on('data', chunk => { if (chunk.includes(10)) s.destroy() })
    for (const e of ['timeout', 'error', 'close']) s.on(e, () => { s.destroy(); done() })
  })
}
