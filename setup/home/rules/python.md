---
paths:
  - "**/*.py"
  - "**/pyproject.toml"

# 不掛 **/*.pyi：命中的幾乎全是 .venv/site-packages 的 vendored 型別存根。
---

# Python

- 檔案 I/O 明給 `encoding="utf-8"`——Windows 預設編碼不是 UTF-8，不給會在別人機器上炸。
- 一律在虛擬環境內作業，不污染系統 Python。
- 公開介面用 dataclass／pydantic 模型帶型別，不裸傳 dict。
- 例外要嘛上拋、要嘛記錄後明確處理，不靜默吞掉。
