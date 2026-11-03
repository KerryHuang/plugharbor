# ui-ux

UI/UX plugin — 設計知識庫加上「設計新畫面」與「審查畫面」的通用規範。受眾專屬規範放受眾附錄，一般專案不套用。

## 定位

`[frontend / design]` 跨技術棧、跨受眾的介面設計知識，不綁特定框架或專案。

## 受眾附錄

位置：`references/audience-<名稱>.md`（plugin 根共用）。`designing-ui`、`auditing-ui` 開頭會「偵測受眾」，只在需要時載入。

| 附錄 | 載入條件 |
|---|---|
| `audience-kids.md` | 使用者明確說兒童，或專案 README／設定標明兒童受眾 |

沒有對應附錄時照通用規範加專案既有畫面的寫法；之後可加其他受眾附錄。

## Skills（3）

| Skill | 用途 |
|-------|------|
| `ui-ux-pro-max` | 設計知識庫：67 styles / 96 palettes / 56 font pairings / 98 UX guidelines / 25 charts 的框架、優先級、速查規則與交付前檢查表 |
| `designing-ui` | 設計或修改畫面的通用規範與自查流程（一步一件事、回饋、狀態、對比、響應式、失敗處理） |
| `auditing-ui` | 依通用清單（加受眾附錄加項）唯讀審查既有畫面，回報嚴重度與依據 |

## 備註

`ui-ux-pro-max` 的核心資料庫（styles/palettes 等 CSV）與 `scripts/search.py` CLI 目前**未一併納入**此 plugin。SKILL.md 內含 fallback 說明：即使沒有 `scripts/`、`data/`，文件的速查／規則／檢查表仍可獨立參照。若要啟用 CLI，需從來源複製 `scripts/` 與 `data/` 進 `skills/ui-ux-pro-max/`。

## License

MIT
