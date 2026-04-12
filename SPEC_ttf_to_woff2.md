# SPEC_ttf_to_woff2

## 目標
- 新增 `src\py\ttf_to_woff2.py`。
- 將 `*.ttf` 轉換成 `*.woff2`。
- 需支援 variable TTF；若輸入為 variable font，輸出需保留 variable weight 能力。

## CLI
- `-input`：來源 `*.ttf` 路徑
- `-output`：輸出 `*.woff2` 路徑

## 輸入規則
- `-input` 必須是存在的 `*.ttf`
- `-output` 必須是 `*.woff2`
- `-output` 的父資料夾若不存在，可自動建立

## 輸出規則
- 以 Python 實作
- 使用 `fontTools` 將 TTF 輸出為 WOFF2
- 不可將 variable font 靜態化；若輸入含 `wght` 等 variation 軸，輸出需保留這些軸
- 成功時輸出指定的 `*.woff2`

## function：convert_ttf_to_woff2
- 實作位置：`src\py\ttf_to_woff2.py`
- 輸入：`input_ttf: Path`, `output_woff2: Path`
- 輸出：一個 `*.woff2`
- 行為：
  - 讀入 TTF
  - 設定輸出 flavor 為 `woff2`
  - 寫出到指定路徑

## function：parse_args
- 實作位置：`src\py\ttf_to_woff2.py`
- 輸入：無
- 輸出：`argparse.Namespace`
- 行為：
  - 解析 `-input`
  - 解析 `-output`

## 錯誤處理
- `-input` 不存在
- `-input` 非 `*.ttf`
- `-output` 非 `*.woff2`
- 缺少 WOFF2 所需依賴，導致輸出失敗
- 字型讀取或寫入失敗

## 驗收條件
1. 可將一般 TTF 轉成 WOFF2。
2. 可將 variable TTF 轉成 variable WOFF2。
3. `-input` 與 `-output` 必須可由 CLI 指定。
4. stderr 輸出時，每行前面需有 8 個空白。
