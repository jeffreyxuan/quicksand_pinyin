THIS FILE MUST BE UTF-8. Read and write this file using UTF-8; rules below are in Chinese.
- 所有回覆一律使用中文。
- *.md 檔案必須維持 UTF-8 編碼，不可改成 ANSI 或其他編碼。
- 編輯任何既有檔案前，必須先確認原檔編碼；寫回時必須保持相同編碼。
- 若無法 100% 確認原檔編碼，必須先停止並詢問，不得寫入。
- 禁止使用系統預設 ANSI code page 覆寫檔案。

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

## 規格檔修改保護規則（重要）
- 修改任何 `SPEC_*.md` 時，預設只能「增量修改」（minimal diff）。
- 禁止在未經使用者明確同意下，整份重寫、刪除重建、或大幅精簡既有章節。
- 若需要重構章節順序或大幅改寫，必須先提出差異摘要並取得使用者確認後才能執行。
- 不得刪除既有條文，除非：
  1. 使用者明確要求刪除，或
  2. 新條文已逐條覆蓋且在變更說明中列出對照。
- 每次修改 `SPEC_*.md` 後，必須在回覆中提供：
  - 變更檔案
  - 保留章節
  - 新增章節
  - 刪除章節（若有）
- 若變更會導致單一 `SPEC_*.md` 刪除超過 20% 行數，視為高風險變更，必須先停下並詢問使用者確認。  





