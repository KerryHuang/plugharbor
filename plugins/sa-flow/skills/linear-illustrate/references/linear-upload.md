# Linear 上傳與回票

## 上傳附件（每檔三步，嚴格依序）

**一次只處理一個檔案**：prepare → PUT → finalize 完成後才 prepare 下一個（signed URL 只有 **60 秒**，批次 prepare 會過期）。

### 1. prepare

```
Linear MCP prepare_attachment_upload
  issue: ABC-123
  filename: <檔名>.png
  contentType: image/png
  size: <精確 bytes，用 ls -la 取得>
  title: <附件標題>
```

### 2. PUT（curl）

```bash
curl -sS -X PUT --data-binary @"<檔案絕對路徑>" \
  -H "content-type: image/png" \
  -H "cache-control: public, max-age=31536000" \
  -H "x-goog-content-length-range: <size>,<size>" \
  -H 'Content-Disposition: attachment; filename="<檔名>.png"' \
  -o /dev/null -w "%{http_code}" \
  "<uploadRequest.url 完整簽名網址>"
```

**Gotchas（皆為實際踩過）：**

- `uploadRequest.url` 必須**逐字元完整複製**——簽名是 512 字 hex，抄錯任何一字元（包括混入形似的 Unicode 字元）直接 400。
- 所有 headers 一個都不能少、大小寫照原樣；`x-goog-content-length-range` 的兩個數字都是精確檔案 size。
- 回 400/403 → URL 已錯或已過期，**重新 prepare** 再來，不要重試舊 URL。
- 期望輸出 `200`。

### 3. finalize

```
Linear MCP create_attachment_from_upload
  issue: ABC-123
  assetUrl: <prepare 回傳的 assetUrl>
  title: <附件標題>
```

## 內嵌到票描述

`save_issue` 更新 description，用 markdown 圖片語法引用 **assetUrl**（不帶簽名參數；Linear 顯示時會自動重新簽名）：

```markdown
![圖片說明](https://uploads.linear.app/<workspace>/<id>/<id>)
```

### 描述結構慣例

在既有描述中插入，**不動其他章節**：

```markdown
## 現行畫面（實機截圖，<測試環境> / <功能名稱>）

**畫面 1 — <標題>：** <說明：紅框①藍框②各指什麼、問題是什麼>

![...](assetUrl1)

## 調整後示意圖（真實畫面合成）        ← 只在有 composite 圖時

**畫面 2 — <標題>：** <說明>

> 本圖由現行系統真實截圖合成，僅示意區塊位置；欄位間距與收合行為由前端依現行元件實作。

![...](assetUrl2)
```

- 票內原有的 ASCII 示意圖（舊票遺留）**移除**，改由本 skill 上傳的真實截圖承擔視覺說明；畫面的欄位與行為以票內「畫面內容規格」章節為準。
- 若使用者這次指定了更精確的位置/行為（如「放在價格資料之下」），同步更新功能範圍與驗收條件的文字。
- 說明文字對 dev 寫：講清楚每個編號框的語意與業務卡點，不要只貼圖。

### save_issue 注意

- description 是**整份覆寫**——先 `get_issue` 拿完整原文再插入，不可只送片段。
- 參考文件裡的 `<document>` 標籤送回時會轉成一般 markdown 連結，屬正常現象。
