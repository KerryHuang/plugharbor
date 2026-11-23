# Windows shell 坑

只在 Windows（Git Bash）上會踩到的；macOS／Linux 可忽略。

- **Python 輸出重導向強制 UTF-8**：stdout 預設 cp950，`python x.py > file` 中文落檔即亂碼（console 看起來正常）。自寫腳本開頭 `sys.stdout.reconfigure(encoding="utf-8")`，或執行時帶 `PYTHONUTF8=1`；落檔亂碼先查輸出端，不是來源檔。
- **`!` 前綴指令一次只給一行**：多行貼上時只有第一行的 `!` 被剝掉，第二行起變成 bash 的 exit code 反轉，`&&` 後段靜默不跑。每條自帶驗證，等結果再給下一條。
- **不用 `cd <目錄> && …` 複合指令**：cwd 會跨指令漂移，權限系統也判不出目錄而每條都彈窗。每條指令自帶絕對路徑；非得在某目錄跑就用 subshell `(cd … && cmd)`。派 subagent 時 prompt 也要寫明「搜尋用 Grep／Glob 工具＋絕對路徑」，它讀不到這條。
- **設定檔裡的 `bash` 寫 Git Bash 絕對路徑**：裝了 WSL 時，裸 `bash` 可能叫到 WSL 的 bash（看不到 Windows PATH 與檔案）。hook、MCP `headersHelper` 這類由別的程式啟動的指令都要寫死 `C:/Program Files/Git/bin/bash.exe`。
