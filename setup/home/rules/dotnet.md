---
paths:
  - "**/*.cs"
  - "**/*.csproj"
  - "**/*.sln"
---

# .NET / C#

- 版本號交給 Semantic Release／CI——不手改 csproj 版本、不自己打 git tag。
- Nullable 開啟的專案，`!` 只用在你能證明非 null 的地方，不拿它壓警告。
- EF Core：唯讀查詢預設 `AsNoTracking()`；migration 產生後不手改；
  對產出的 SQL 形狀沒把握就先把查詢印出來看，別憑 LINQ 猜。
