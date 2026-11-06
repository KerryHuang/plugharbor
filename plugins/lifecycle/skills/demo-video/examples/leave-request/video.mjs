// 範例影片腳本（虛構情境：員工請假申請）。格式說明見 references/script-format.md。
// 執行：bash run.sh <工作目錄>
export default {
  name: 'leave-request',
  base: 'http://127.0.0.1:5190/index.html',
  voice: 'zh-TW-HsiaoChenNeural',
  segments: [
    {
      text: '這支影片示範，怎麼在員工入口提出一筆請假申請。',
      run: async (a) => { await a.pause(2500) },
    },
    {
      text: '先選假別，這裡選事假。',
      run: async (a) => {
        await a.click(a.p.getByLabel('假別'))
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
