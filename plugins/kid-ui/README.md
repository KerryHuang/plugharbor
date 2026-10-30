# kid-ui

給兒童（以小一、6–7 歲、平板橫放為基準）使用的 app 介面規範，兩個 skill。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install kid-ui@plugharbor
```

## Skills

| Skill | 用途 |
|-------|------|
| `designing-kid-ui` | 新增或修改兒童會看到的畫面、按鈕、彈窗、提示、念的話、CSS 版面時使用：文字、念題、點擊回饋、彈窗、返回／關閉、主題配色、版面尺寸，以及同系列 app 要一致的元件（`components.md`）。 |
| `auditing-kid-ui` | 依檢查清單（`checklist.md`）唯讀審查既有畫面，回報不符合處、嚴重度與依據。只能手動觸發。 |

## app 專屬設定

規範是通用的；每個 app 自己的版面寫法與元件位置放在專案的 `.claude/skills/designing-kid-ui/this-app.md`
（或 `.claude/rules/`）。兩者都沒有時，skill 會請使用者提供年齡層和裝置。
