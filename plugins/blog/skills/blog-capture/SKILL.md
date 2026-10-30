---
name: blog-capture
description: 把目前 session 做的專案、POC 或小成就，整理成一份 blog 素材包存到 Google Drive 的 blog-inbox/，之後回寫文章的 session 用 write-post 寫成文章。只收素材、不寫文章、不碰 blog repo。Use when 使用者說「/blog-capture」「這個可以寫成文章」「收成 blog 素材」時。
---

# 收 blog 素材

在原本做事的 session 趁熱收素材：這裡最清楚使用者說過什麼、踩過什麼坑、為什麼這樣決定。文章之後在寫文章的 session（用 `write-post` skill）寫，這裡**不寫文章、不碰 blog repo、不 commit**。

## 1. 判斷是不是公司專案

看目前 repo 的 remote（`git remote -v`）：

- 指向公司內部的 git 主機（私有網域、自架 GitLab 等）→ **公司專案**，第 3 步要去識別化。
- 其他（個人 GitHub、沒有 remote）→ 個人專案，照實收。
- 不在 git repo 裡、或看不出來 → 當成公司專案處理，並在素材包註明「來源不明，已按公司專案去識別化」。
- remote 看不出是公司還是個人時，問使用者一次。

## 2. 收素材

來源依序：這個 session 的對話 → repo 的 commit 紀錄、README、設計文件、NOTES → session 紀錄檔。只收**實際發生過**的事，不推測、不美化。

- **session 紀錄檔**在 `~/.claude/projects/<cwd 把 / 換成 ->/<session-id>.jsonl`，很大，不要整份讀；用 python 只抽 `type == "user"` 的訊息文字。時間是 UTC，換成使用者所在時區。
- **context 壓縮摘要**可以用，但它是 AI 的轉述：引用時標「（摘要）」，跟原始訊息衝突時以原始訊息為準。
- **數字**分清楚是「規格要求的目標」還是「實際做到的結果」，只有後者能寫成成果；找不到出處的標「未核對」。
- 工作樹裡還沒 commit 的東西（別的 session 正在做的）不算素材，最多提一句。

素材包用這個格式（Markdown）：

```markdown
# <專案名稱>：<一句話說它是什麼>

- 收件日：<YYYY-MM-DD>；專案期間：<起>～<迄>
- 類型：個人專案／公司專案（已去識別化）
- 建議分類：依部落格自己的分類擇一（可附次選）
- 建議題目：<1–2 個，寫讀者會好奇的問題或發現>
- 出處：<repo 網址或本機路徑>、<相關 commit>、<session 紀錄路徑>
- 線上版：<網址，沒有就寫「無」>

## 做了什麼、為什麼做
## 過程（照時間順序，標出使用者每一步說了什麼）
## 關鍵決定與放棄的方案
## 踩到的坑與怎麼解
## 成果與數字（每個數字附出處：哪個檔案、哪則訊息）
## 使用者的原話
> 逐字引用，附時間。只放使用者親手打的話。user 訊息裡這些都**不是**使用者的話，不放：
> 貼上的外部內容（prompt、文章、log）、skill 展開文字、其他 session／subagent 的回報、壓縮摘要、
> harness 自動訊息（如 "Output token limit hit"）、只有圖片的訊息。貼上的外部內容只記「貼了什麼、來自哪裡」。
## 還缺什麼（寫文章時要問使用者的）
## 已移除的資訊類型（公司專案才有）
```

## 3. 公司專案去識別化

寫進素材包**之前**就拿掉，不是寫完再刪：

- 公司名、產品名、客戶名、同事名、內部系統與專案代號、內部網址與主機名
- 程式碼片段、資料表結構、真實資料與數字（營收、筆數、客戶數）
- 票號、PR／MR 編號、內部文件連結

只留：用了什麼技術、怎麼做、遇到什麼問題、學到什麼。把拿掉的**類型**（不是內容）列在「已移除的資訊類型」，讓使用者審。拿不準要不要拿掉的，一律拿掉，並在「還缺什麼」註明。

## 4. 存到 Google Drive

- 用 Google Drive connector 的 `create_file` 上傳到名為 `blog-inbox` 的資料夾：先用 `title = 'blog-inbox'` 搜尋資料夾取得 id 當 `parentId`；搜不到就問使用者，不自行建立在其他位置。
- 檔名 `<YYYY-MM-DD>-<英文-slug>.md`，`contentMimeType: text/markdown`，`disableConversionToGoogleType: true`（保持純 Markdown，之後才讀得回來）。
- 同名檔已存在就先讀，補充後另存成 `-v2`，不覆蓋。
- 沒有 Google Drive connector（例如工具不存在或未授權）：把素材包內容完整貼在回覆裡，請使用者自己存或貼到寫文章的 session，**不要**改存到其他地方。

## 5. 回報

對呼叫你的人（通常是使用者；若你是 subagent 就回給主 session）一段話：素材包的 Drive 連結、建議題目、「還缺什麼」裡有幾題要使用者回答；公司專案另外列出已移除的資訊類型。最後提醒：要寫成文章時，到寫文章的 session 說「用 blog-inbox 的 <檔名> 寫文章」。
