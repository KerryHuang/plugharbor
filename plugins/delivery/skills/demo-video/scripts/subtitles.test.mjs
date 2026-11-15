import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildCues, splitSentences, srtTime, toSrt, weight } from './lib/subtitles.mjs'
import { assertSafeName, buildFilterGraph, parseStreamDurations } from './lib/media.mjs'

test('依標點切句，標點留在句尾以便計權', () => {
  assert.deepEqual(splitSentences('先登入，再按新增。完成！'), ['先登入，', '再按新增。', '完成！'])
})

test('沒有標點的整句不切', () => {
  assert.deepEqual(splitSentences('只有一句沒有標點'), ['只有一句沒有標點'])
})

test('過長的句子均分，且每段不超過上限', () => {
  const parts = splitSentences('一二三四五六七八九十一二三四五六七八九十一二三四五，', 10)
  assert.equal(parts.length, 3)
  assert.ok(parts.every((p) => p.replace('，', '').length <= 10))
  assert.equal(parts.join(''), '一二三四五六七八九十一二三四五六七八九十一二三四五，')
})

test('標點加權 2 字', () => {
  assert.equal(weight('先登入，'), 6) // 含標點 4 字 + 停頓加權 2
  assert.equal(weight('先登入'), 3)
})

test('字幕時間涵蓋整段語音，首尾相接，字幕不含句尾標點', () => {
  const cues = buildCues('甲乙，丙丁戊。', 10, 6)
  assert.equal(cues.length, 2)
  assert.equal(cues[0].from, 10)
  assert.ok(Math.abs(cues[1].to - 16) < 1e-9)
  assert.equal(cues[0].to, cues[1].from)
  assert.deepEqual(cues.map((c) => c.text), ['甲乙', '丙丁戊'])
  // 權重 5（甲乙，）: 6（丙丁戊。）：權重大的句子時間較長
  assert.ok(cues[1].to - cues[1].from > cues[0].to - cues[0].from)
})

test('srtTime 補零、進位正確', () => {
  assert.equal(srtTime(0), '00:00:00,000')
  assert.equal(srtTime(61.5), '00:01:01,500')
  assert.equal(srtTime(3661.0004), '01:01:01,000')
  assert.equal(srtTime(1.9996), '00:00:02,000')
})

test('toSrt 序號從 1、區塊以空行分隔', () => {
  const srt = toSrt([{ text: 'A', from: 0, to: 1 }, { text: 'B', from: 1, to: 2.5 }])
  assert.equal(srt, '1\n00:00:00,000 --> 00:00:01,000\nA\n\n2\n00:00:01,000 --> 00:00:02,500\nB\n')
})

test('parseStreamDurations 分開讀影像與音軌', () => {
  assert.deepEqual(parseStreamDurations('video,52.8\naudio,64.0\n'), { video: 52.8, audio: 64 })
  assert.ok(Number.isNaN(parseStreamDurations('video,N/A\naudio,64\n').video))
})

test('合成 filter 一定用 tpad 補滿影像軌（靜止畫面不會讓影像提早結束）', () => {
  const g = buildFilterGraph({ total: 20, starts: [0.5, 8], cues: [{ from: 0.5, to: 3 }] })
  assert.match(g, /tpad=stop_mode=clone:stop_duration=20\.00/)
  assert.match(g, /trim=duration=20\.00/)
  assert.match(g, /adelay=500:all=1/)
  assert.match(g, /between\(t,0\.500,3\.000\)/)
})

test('name 只接受單純檔名，路徑與 .. 一律報錯', () => {
  assert.equal(assertSafeName('leave-request'), 'leave-request')
  assert.equal(assertSafeName('請假申請 v2'), '請假申請 v2')
  for (const bad of ['../existing', 'a/b', 'a\\b', '..', '.', '', '/etc/x', undefined, 5]) {
    assert.throws(() => assertSafeName(bad), /單純檔名/, String(bad))
  }
})
