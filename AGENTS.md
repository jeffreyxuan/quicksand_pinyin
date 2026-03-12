# AGENTS.md

## 目的
本檔只保留「協作與執行準則」。
完整功能規格、CLI 與 function 需求，請看各功能對應的 `SPEC_xxx.md`。

## 規格來源
- 每個 Python 腳本都應有各自對應的規格檔，命名格式為 `SPEC_<module_name>.md`。
- 各 `SPEC_xxx.md` 是對應 Python 腳本的規格唯一來源（single source of truth）。
- 若 `AGENTS.md` 與對應 `SPEC_xxx.md` 有不一致，以該 `SPEC_xxx.md` 為準。

## 開發準則
- 本專案文件預設為中文內容，文字檔請一律使用 UTF-8 編碼儲存。
- `otfccdump` 的 JSON 是「ASCII 主體 + 可能混入系統 code page 字節（Windows 常見 cp950/ANSI）」來處理，而不是純 UTF-8。
- 所有暫存檔案放在 `_tmp/`。
- 所有輸出檔案放在 `_output/`。
- 以 Python 實作。
- function 命名使用 `snake_case`，參數與回傳值需有 type hints。
- docstring 欄位遵循：`Summary`、`Args`、`Returns`、`Raises`（可選）、`Example`。
## Python 執行方式
- 在本專案（Windows + PowerShell）請優先用以下格式執行 `python3`：
  - `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 <你的指令>"`
- 需要快速檢查版本時可用：
  - `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 --version"`


## 變更流程
- 新需求先更新對應的 `SPEC_xxx.md`，再改程式。
- 每次新增 Python 腳本時，都必須同步新增對應的 `SPEC_xxx.md`。
- 每次「新增 function」或「修改既有 function 行為/簽章」，都必須同步更新對應的 `SPEC_xxx.md`。
- 規格調整後，僅在必要時同步更新本檔（避免重複維護）。







