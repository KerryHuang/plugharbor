import { test } from 'node:test'
import assert from 'node:assert/strict'
import { estimateVoiceSec } from './lib/estimate.mjs'

test('20 字旁白估 5 秒', () => {
  assert.equal(estimateVoiceSec('這是一段剛好二十個字的測試旁白內容喔喔喔'), 5)
})

test('標點不計字數', () => {
  assert.equal(estimateVoiceSec('一、二。'), 1.4)
})

test('字母與數字都算字', () => {
  assert.equal(estimateVoiceSec('Edge TTS 3'), 2.4)
})
