# -*- coding: utf-8 -*-
"""docx → PDF 回轉器的選擇：Windows 有 Word COM 用 Word，否則用 LibreOffice。

只用標準函式庫，讓 CLI 在沒裝 pymupdf 的環境也能先判斷、給出清楚訊息。
  python converter_select.py    # 印出選到的轉換器；皆無則印安裝指引、退出碼 3
"""
import os
import shutil
import sys

EXIT_UNAVAILABLE = 3

INSTALL_HINT = (
    "找不到可用的 docx→PDF 轉換器（Windows 需 Word，其他平台或無 Word 需 LibreOffice）。"
    "請安裝 LibreOffice 並確認 soffice 在 PATH："
    "macOS `brew install --cask libreoffice`、Ubuntu `sudo apt install libreoffice-writer`、"
    "Windows `winget install TheDocumentFoundation.LibreOffice`。"
    "或加 --allow-degraded 只驗文字軸。"
)

_MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"


class ConverterUnavailable(RuntimeError):
    """Word 與 LibreOffice 都找不到。"""


def _word_registered() -> bool:
    try:
        import winreg
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application"))
        return True
    except OSError:
        return False


def detect_env() -> dict:
    """蒐集本機實況：platform、word_com（Windows 且 Word 已註冊）、soffice 路徑或 None。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice and os.path.exists(_MAC_SOFFICE):
        soffice = _MAC_SOFFICE
    return {
        "platform": sys.platform,
        "word_com": sys.platform == "win32" and _word_registered(),
        "soffice": soffice,
    }


def select_converter(env: dict) -> str:
    """env 含 platform、word_com、soffice。回 "word" 或 "libreoffice"，皆無 raise ConverterUnavailable。"""
    if env.get("platform") == "win32" and env.get("word_com"):
        return "word"
    if env.get("soffice"):
        return "libreoffice"
    raise ConverterUnavailable(INSTALL_HINT)


def main() -> int:
    try:
        print(select_converter(detect_env()))
        return 0
    except ConverterUnavailable as e:
        print(str(e), file=sys.stderr)
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    sys.exit(main())
