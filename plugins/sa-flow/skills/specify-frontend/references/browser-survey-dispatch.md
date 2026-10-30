# 視覺分析派工樣板（browser-surveyor）

`specify-frontend` Step 4 的 `sa-flow:browser-surveyor` 派工 prompt。

`{}` 為呼叫端填入值；所有路徑一律展開成**絕對路徑**。

```
subagent_type: "sa-flow:browser-surveyor"
prompt: |
  mode: survey
  url: {使用者提供的 URL}
  env_class: {由 URL 判定}
  readonly: {production 或判不準一律 true}
  credentials: {登入設定檔絕對路徑，先 `ls` 驗存在}
  targets:
    - {FRD §4 畫面清單逐項：畫面名、怎麼到達}
  out_file: {功能目錄}/analysis/ui-survey.md
  shot_dir: {功能目錄}/analysis/shots
  focus: 完整欄位清單（label／型別／必填／預設值／長度上限／選項來源）、
         各狀態（空／載入／錯誤／唯讀）、驗證訊息原文、操作按鈕的啟用條件
  isolated_context: specify-frontend-{功能碼或序號}   # 同 session 派多個時各自不同，例 survey-01／survey-02
```

同 session 可平行派多個瀏覽器 agent，各給不同 `isolated_context`。
