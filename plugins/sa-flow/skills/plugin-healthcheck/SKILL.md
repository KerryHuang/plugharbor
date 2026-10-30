---
name: plugin-healthcheck
description: >-
  檢查 Claude Code 官方 Plugin 規範最新變化，對比本 plugin 結構，產出健康報告與重構建議。
  適用於定期維護、版本升級、或懷疑 plugin 結構已過時。
  Use when user says "plugin 健康檢查", "plugin health check", "檢查 plugin 結構", "plugin 是否需要更新", "check plugin structure".
argument-hint: "[--fix] [--verbose]"
---

# Plugin 健康檢查

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

定期檢查 Claude Code 官方 Plugin 規範最新變化，對比本 plugin 結構，產出健康報告與重構建議。

## 使用者輸入

```text
$ARGUMENTS
```

- `plugin-healthcheck` — 產出健康報告（僅檢查，不修改）
- `plugin-healthcheck --fix` — 自動修復可安全處理的問題
- `plugin-healthcheck --verbose` — 詳細報告含每個檔案的檢查結果

## 執行流程

### 1. 取得官方最新規範

使用 WebFetch 抓取 Claude Code 官方文件：

```
https://docs.anthropic.com/en/docs/claude-code/plugins
https://docs.anthropic.com/en/docs/claude-code/skills
```

若無法存取，使用 WebSearch 搜尋：
- `"Claude Code plugin" specification site:docs.anthropic.com`
- `"Claude Code plugin" marketplace schema`
- `"Claude Code SKILL.md" format`

從取得的內容提取：
- plugin.json 最新 schema（必填/選填欄位）
- marketplace.json 最新 schema
- SKILL.md frontmatter 支援的欄位
- 支援的目錄結構（skills/, commands/, agents/, hooks/, 等）
- 任何新增的功能或廢棄的做法

### 2. 掃描本 plugin 結構

讀取本 plugin 根目錄（使用 `${CLAUDE_SKILL_DIR}/../..` 或當前目錄），盤點：

| 檢查項 | 方式 |
|--------|------|
| plugin.json | 讀取並解析所有欄位 |
| marketplace.json | 讀取並解析所有欄位 |
| skills/ 目錄 | 列出所有 SKILL.md，解析 frontmatter |
| agents/ 目錄 | 列出所有 agent 定義 |
| references/ 目錄 | 列出所有參考文件 |
| templates/ 目錄 | 列出所有範本 |
| 其他目錄 | 檢查是否有官方新支援的目錄未使用 |

### 3. 結構對比

逐項對比官方規範與本 plugin 現狀：

#### 3.1 Manifest 檢查

| 檢查項 | 等級 | 說明 |
|--------|------|------|
| plugin.json 必填欄位齊全 | CRITICAL | name, description, version |
| plugin.json 有無新增必填欄位 | CRITICAL | 官方可能新增 |
| marketplace.json 格式正確 | CRITICAL | 欄位、source 格式 |
| version 符合 semver | WARNING | 如 1.0.0 |
| 有無官方新增的選填欄位可利用 | INFO | 如 keywords, category |

#### 3.2 SKILL.md 檢查

| 檢查項 | 等級 | 說明 |
|--------|------|------|
| frontmatter 必填欄位齊全 | CRITICAL | name, description |
| 有無官方新增的 frontmatter 欄位 | WARNING | 如新 trigger 語法 |
| 有無廢棄的 frontmatter 欄位 | WARNING | 舊欄位可能不再支援 |
| SKILL.md 行數合理（<500 行） | INFO | 過長影響載入 |
| references/ 引用路徑正確 | CRITICAL | ${CLAUDE_SKILL_DIR}/../.. 路徑存在 |

#### 3.3 目錄結構檢查

| 檢查項 | 等級 | 說明 |
|--------|------|------|
| 官方支援但本 plugin 未使用的目錄 | INFO | 如 hooks/, outputStyles/ |
| 本 plugin 使用但官方不支援的目錄 | WARNING | references/, templates/ 是自訂 |
| .claude-plugin/ 位置正確 | CRITICAL | 只含 plugin.json + marketplace.json |

#### 3.4 內容品質檢查

| 檢查項 | 等級 | 說明 |
|--------|------|------|
| 所有 ${CLAUDE_SKILL_DIR}/../.. 引用的檔案存在 | CRITICAL | 避免破損引用 |
| 無殘留的硬編碼路徑 | WARNING | 專案特定路徑不應出現 |
| 無殘留的硬編碼 agent 名稱 | WARNING | 應用自然語言描述 |
| 無超出 plugin 範圍的實作細節 | INFO | 參考上游階段範圍 |

### 4. 產出健康報告

```markdown
# Plugin 健康報告

**檢查日期**：{YYYY-MM-DD}
**Plugin 版本**：{version from plugin.json}
**官方規範版本**：{取得日期或版本}

## 總覽

| 指標 | 結果 |
|------|------|
| Manifest 完整性 | ✅ / ⚠️ / ❌ |
| SKILL.md 規範符合度 | ✅ / ⚠️ / ❌ |
| 目錄結構 | ✅ / ⚠️ / ❌ |
| 內容品質 | ✅ / ⚠️ / ❌ |
| 整體健康度 | {百分比} |

## 發現

### CRITICAL（必須修復）
{列表}

### WARNING（建議修復）
{列表}

### INFO（參考資訊）
{列表}

## 官方規範變化摘要

| 變化 | 影響 | 建議行動 |
|------|------|---------|
| {新增/變更/廢棄的規範} | {對本 plugin 的影響} | {具體行動} |

## 重構建議

### 短期（下次更新）
{列表}

### 中期（下個版本）
{列表}

### 長期（規劃中）
{列表}
```

### 5. 自動修復（--fix 模式）

僅修復以下安全項目，其餘列入報告由使用者決定：

| 可自動修復 | 方式 |
|-----------|------|
| plugin.json 缺少新增選填欄位 | 補充欄位 |
| SKILL.md frontmatter 缺少欄位 | 補充欄位 |
| 破損的 ${CLAUDE_SKILL_DIR}/../.. 引用 | 修正路徑或標記 |
| version 格式不符 semver | 修正格式 |

**不自動修復**：
- 目錄結構重組（影響範圍大）
- 內容改寫（需人工判斷）
- 官方重大 breaking change（需評估影響）

修復後重新執行檢查，確認問題已解決。

### 6. 版本建議

根據發現的問題數量和嚴重度，建議版本號更新：

| 情況 | 版本建議 |
|------|---------|
| 僅 INFO | 不需更新 |
| 有 WARNING 修復 | patch（如 1.0.0 → 1.0.1） |
| 有 CRITICAL 修復 | minor（如 1.0.0 → 1.1.0） |
| 官方 breaking change | major（如 1.0.0 → 2.0.0） |
