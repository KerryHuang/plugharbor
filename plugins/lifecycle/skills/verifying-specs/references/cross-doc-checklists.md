# Task 8 跨文件一致性驗證檢查清單

> 對應 SKILL.md Task 8.2 / 8.3 / 8.4 / 8.6 / 8.7 / 8.8（`--cross` 模式）。8.1／8.5 的內容留在 SKILL.md 本體，不在此檔。
> 8.8 的判準總覽（哪些是 BLOCKER／WARNING）已寫在 SKILL.md，本檔只放逐項偵測指令與門檻細節。

## 8.2 FRD ↔ SAD 一致性

| 檢查項目 | 等級 |
|---------|------|
| FRD 每個使用者故事在 SAD 工作流中有對應 | CRITICAL |
| FRD 欄位規格在 SAD 資料流中有對應 | CRITICAL |
| FRD 業務規則在 SAD 資訊流處理邏輯中有對應 | CRITICAL |
| SAD 標明的業務生命週期位置合理 | WARNING |

## 8.3 SAD ↔ BFS 一致性

| 檢查項目 | 等級 |
|---------|------|
| SAD 涉及的資料表在 BFS 中都有定義 | CRITICAL |
| SAD 可重用 API 在 BFS 中有引用或說明 | WARNING |
| SAD 實現策略建議在 BFS 中有體現 | WARNING |
| SAD 風險項目在 BFS 中有因應方案 | WARNING |
| SAD Migration 預判的新增 Table/Column 在 BFS 有 §M 規格或明確標注不需要 | CRITICAL |
| SAD §6.6 每個適用維度（B1–B10、M1–M4）都有結論（含明寫「不適用」），無整段留白 | CRITICAL |
| SAD §6.6 的每條邊界結論在 BFS 對應章節有落實（B1-B3→§7 VR、B4→§2.4、B5→§8.4、B6/B8→§8.3、B7→§8、B10→§6.0） | CRITICAL |
| BFS §6.0 DoR 標「同步餵 SAD」的維度，SAD §6.6／§6.5 確實有對應列 | WARNING |

> 維度定義見 `${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md`；
> 承接關係的權威登記在 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md` 產物 owner 矩陣。

## 8.4 BFS ↔ 計劃/任務 一致性

| 檢查項目 | 等級 |
|---------|------|
| BFS 每個 API 端點在計劃/任務中有對應 | CRITICAL |
| 計劃中的每個元件都有對應任務 | CRITICAL |
| 任務相依性符合架構分層 | CRITICAL |
| 無孤立任務（每個任務可追溯到 BFS） | WARNING |

## 8.6 FFS ↔ BFS 驗證規則對齊

| 檢查項目 | 等級 |
|---------|------|
| FFS §4「對應 BFS VR」欄已填且 VR 編號在 BFS §7.1 存在 | CRITICAL |
| FFS 欄位必填標記與 BFS VR 一致 | CRITICAL |
| FFS 驗證訊息與 BFS VR 訊息語意一致（前端可更友善但不可更寬鬆） | WARNING |
| FFS §4.3 表單層級驗證在 BFS §7.3 有對應 | WARNING |

## 8.7 BFS 內部邏輯一致性（多入口 / Bug Fix）

**觸發**：BFS 描述含「兩入口/三入口/共用 Mapper/Bug Fix/對齊」關鍵字。

| 檢查項目 | 等級 |
|---------|------|
| §6.1「既有不變動」路由能在 `analysis/reuse-scan.yml` 的 `routes:` 找到匹配，且 BFS §A.1 有對應現況結論 | CRITICAL |
| BFS §A.2 影響範圍結論列出同類寫入路徑總數、本次範圍、排除項與原因（明細在 reuse-scan.yml） | CRITICAL |
| 多入口一致性宣稱與各入口輸入/輸出/業務行為實際可一致 | CRITICAL |
| 共用元件設計（BFS §2.3）輸入差異明確列出 | CRITICAL |
| Bug Fix 段落每項對應 codebase 具體行號 | CRITICAL |
| `reuse-scan.yml` 的 `handler_mappings:` 列完整 N 欄（不在 BFS 內） | WARNING |
| Request/Response「沿用既有」附完整欄位清單 | CRITICAL |

> 詳細規則 → `${CLAUDE_PLUGIN_ROOT}/skills/specify-backend/references/spec-lint.md`、`bug-validation.md`、`reuse-scan.md`。

## 8.8 文件邊界去重（`--cross` 模式）

判準總覽（BLOCKER／WARNING 分類）已寫在 SKILL.md；本節只放逐項偵測方式。

**去重三項（BLOCKER）**：
- 下游未重抄上游 owner 產物（狀態圖/流程圖/ER/快照），改成 ref + 增量說明。
- 跨文件編號一致：`VR-001` 不可寫成 `VR-01`。
- ref 指向「文件名+章節+標題」（或已宣告簡稱＋章節＋標題，見 `spec-dedup-and-budget.md`「簡稱宣告」），並說明增量。
- BFS 內部無自我重複：§2.4↔§4.2、§3↔§4.1、§12/13/14 逐對比對。

**SPEC-INDEX（WARNING）**：文件含 `<!-- SPEC-INDEX v1 -->` 時，索引依形狀分流比對——完整格式一一對應／
CR 簡化格式子集比對（CR 簡化格式，見 `index-and-size-checks.md`）；
BR/VR/TC 編號區間須與正文一致。

**正文體積（WARNING）**：正文＝`## 1.` 起至 `## D.` 前，FRD/SAD/FFS ≤30KB、BFS ≤45KB，**量法排除 📎 行**；
超標報告須指出可拆成 `{功能}_附錄_{主題}.md` 的章，判準見 [index-and-size-checks.md](index-and-size-checks.md)。

**另五項 WARNING**：
① 版本資訊雙寫——同檔同時有 `<!-- CHANGELOG -->` 表與「修訂歷史」「規格狀態」「版本資訊」任一表；
② 必畫圖缺——依 `${CLAUDE_PLUGIN_ROOT}/references/spec-dedup-and-budget.md`「必畫圖清單」逐項在該章 `grep -c '```mermaid'`；
③ 公式型規則無算例——BR/VR 列含 `＝`／`％`／`÷`／`×`／分攤／遮罩／優先序而同節無「算例」；
④ 引用檔不存在——文中引用的 `analysis/*`、`decisions.md`、`*_附錄_*.md` 逐一 `ls` 驗；
⑤ `§D` 未指向 `decisions.md`（仍是整表且無 ref 行）。
