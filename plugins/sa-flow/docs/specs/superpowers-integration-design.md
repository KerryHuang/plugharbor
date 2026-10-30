# Superpowers Integration Design

**Status:** Approved

> 2.0.0 起 `specify` 拆為 `specify-backend`／`specify-frontend`，流程也加入 explore、dev-readiness、qa-verify 等棒；現行流程以 `references/pipeline.md` 為準，本檔保留為當初的整合決策紀錄。

## Overview

整合 `sdlc` plugin 與 `superpowers` plugin，形成完整的軟體開發生命週期 pipeline。兩者分工明確：

- **superpowers** — 流程驅動（brainstorming、planning、executing、reviewing）
- **sdlc** — 文件產出（FRD、SAD、BFS、驗證報告）

整合方式為**引用式**（option C）：sdlc skills 在關鍵銜接點加入前置檢查與後續指引，不複製 superpowers 內容，兩邊各自獨立可運作。

---

## Full Development Pipeline

### 標準流程（新功能）

```
[ superpowers:brainstorming ]           輸出：設計文件 (docs/specs/)
         ↓
[ sa-flow:requirement ]                    輸出：FRD
         ↓
[ sa-flow:system-analysis ]                輸出：SAD
         ↓
[ sa-flow:specify ]                        輸出：BFS
         ↓
[ sa-flow:verifying-specs ]                輸出：驗證報告
         ↓
[ sa-flow:linear-create ]                  輸出：Linear ticket
         ↓
[ superpowers:writing-plans ]           輸出：實作計畫
         ↓
[ superpowers:subagent-driven-development ]
         ↓
[ superpowers:verification-before-completion ]
         ↓
[ superpowers:requesting-code-review ]
         ↓
[ superpowers:finishing-a-development-branch ]
```

### CR 流程（既有功能調整）

```
[ sa-flow:requirement --change ]           輸出：CR-FRD
         ↓
[ sa-flow:specify --change ]               輸出：CR-BFS + CR-FFS
         ↓
[ sa-flow:verifying-specs ]                輸出：驗證報告
         ↓
[ sa-flow:linear-create ]                  輸出：Linear ticket
         ↓
[ superpowers:writing-plans ]           輸出：實作計畫
         ↓
（同標準流程後半段）
```

> CR 流程不需要 brainstorming，需求已明確，從 requirement 直接開始。

---

## Skill 修改點

### `sa-flow:requirement` — 前置檢查
在 skill 開頭加入：
- 標準模式：確認是否已有 brainstorming 設計文件（`docs/specs/`）
- 若無，提示用戶先執行 `superpowers:brainstorming`
- 允許跳過（需求已明確時直接產 FRD）
- CR 模式（`--change`）：不需要 brainstorming，直接執行

### `sa-flow:specify` — 後續指引
BFS 產出後加入：
- 提示下一步執行 `sa-flow:verifying-specs`

### `sa-flow:verifying-specs` — 交棒指引
驗證通過後加入：
- 提示下一步執行 `superpowers:writing-plans`
- 說明輸入文件：FRD + SAD + BFS

### 新增 `references/pipeline.md`
- 全流程地圖
- 各 skill 可引用此文件

---

## README 修改點

**`plugins/sa-flow/README.md` 與 `plugins/sa-flow/README.zh-TW.md`** 新增兩個章節：

1. **Integration with Superpowers** — 說明兩個 plugin 分工、安裝需求
2. **Development Pipeline** — 完整 pipeline 視覺化圖表（標準流程 + CR 流程）

---

## 不修改範圍

| Skill | 原因 |
|-------|------|
| `foxpro-analyzer` | 獨立分析工具，不在主流程中 |
| `linear-create` | 已是 pipeline 一環，無需修改 |
| `retrospective` | 維護工具 |
| `plugin-healthcheck` | 維護工具 |

---

## 相依性

- superpowers 未安裝時，sdlc skill 仍可獨立運作
- sdlc 不複製任何 superpowers skill 內容
- 引用僅為文字提示，不做強制攔截
