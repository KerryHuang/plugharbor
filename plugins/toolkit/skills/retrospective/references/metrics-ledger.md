# metrics.yml：待驗指標帳本

位置：`<retrospective.path>/metrics.yml`（路徑設定見 SKILL.md 的「設定」）。進版控；不放人名，寫角色。
Step 5 追加、下次回顧的 Step 0 讀取。不要放進 plugin 安裝目錄（更新時會被蓋掉）。

```yaml
# 待驗指標帳本
# due 只能是下列兩種之一（機器可判斷到期）：
#   new_chains: 自 since 起新增的工作單位達 count 個
#               （工作單位＝符合 units_glob 的目錄，以該目錄在 git 的首次 commit 日期晚於 since 計）
#   date:       到該日期
# status：open（待驗）｜passed｜failed｜side-effect｜retired（不再追蹤，note 寫原因）
# checks：每次驗證追加一筆，不改舊筆；未到期也記，verdict 寫 not-due。

metrics:
  - id: M-20260105-01
    source: 20260105-review-speed/report.md
    layer: demo-plugin            # 被改的 plugin 或層級
    metric: 審查回合數
    criterion: 下 5 個工作單位的審查退回次數平均 ≤ 1
    due: {new_chains: 5, since: "2026-01-05", units_glob: "docs/*/*"}
    if_not: 回退審查閘門，改查退回原因
    status: open
    checks:
      - {date: "2026-01-12", verdict: not-due, evidence: "新增 1/5"}
```

## 規則

- `criterion` 必須可觀察、可數（「退回次數」可以，「品質提升」不行）。寫不成 `new_chains` 或 `date` 的指標無法自動到期，改寫成可數的判準。
- 新增 `new_chains` 指標時，用同一個 `units_glob`（`retrospective.units_glob`，未設定用 `docs/*/*`）算數，並在 `due` 旁留 `units_glob` 以免日後口徑漂移。
- `verdict`：`pass`｜`fail`｜`side-effect`｜`not-due`。判定後把 `status` 改成對應值；舊的 check 不改。
- 追加後用 `python3 -c 'import yaml,sys;yaml.safe_load(open(sys.argv[1]))' <path>/metrics.yml` 確認解析通過（沒有 PyYAML 時肉眼確認縮排）。
