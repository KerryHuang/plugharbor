// 範例影片腳本（虛構情境：員工請假申請）。格式說明見 references/script-format.md。
// 執行：在 examples/ 目錄下（node_modules 裝在這裡）
//   node ../scripts/demo-video.mjs dry-run leave-request/video.mjs   # 先驗操作，不配音不錄影
//   node ../scripts/demo-video.mjs build leave-request/video.mjs     # 成品在 leave-request/out/
// 站台由上一層的 env.mjs 起，不用寫 base。
export default {
  name: 'leave-request',
  voice: 'zh-TW-HsiaoChenNeural',
  segments: [
    {
      text: '這支影片示範，怎麼在員工入口提出一筆請假申請。',
      run: async (a) => { await a.pause(2500) },
    },
    {
      text: '先選假別，這裡選事假。',
      run: async (a) => {
        await a.click(a.p.getByLabel('假別')) // 原生 select，不是浮層，所以不用 a.select
        await a.p.getByLabel('假別').selectOption('事假')
      },
    },
    {
      text: '接著填請假日期和事由。',
      run: async (a) => {
        await a.fill(a.p.getByLabel('請假日期'), '2026-12-01')
        await a.type(a.p.getByLabel('事由'), '家中有事')
      },
    },
    {
      text: '按下送出申請，畫面會顯示已送出，接下來就等主管簽核。',
      run: async (a) => {
        await a.click(a.p.getByRole('button', { name: '送出申請', exact: true }))
        await a.p.getByRole('status').waitFor()
      },
    },
  ],
}
