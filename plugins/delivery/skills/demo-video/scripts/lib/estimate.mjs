// 語音估計：字數 ÷ 5 + 1 秒。只算 Unicode 字母與數字，標點與空白不計。

export function estimateVoiceSec(text) {
  const n = (text.match(/[\p{L}\p{N}]/gu) ?? []).length
  return Math.round((n / 5 + 1) * 10) / 10
}
