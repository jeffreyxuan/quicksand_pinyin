# SPEC_make_static_instances

## 目標
- 新增 `src\py\make_static_instances.py`。
- 將 variable TTF 轉成固定字重 TTF。
- 預設輸出 9 個字重：
  - `300`
  - `350`
  - `400`
  - `450`
  - `500`
  - `550`
  - `600`
  - `650`
  - `700`

## CLI
- `-input`：來源 variable `*.ttf`
- `-output-dir`：輸出資料夾
- 可提供 `bin\make_static_instances.bat` 作為 Windows 手動執行入口；核心邏輯仍以 `src\py\make_static_instances.py` 為準。
- `bin\make_static_instances.bat` 的預設輸出資料夾應為 `_output\static_instances`
- `bin\ufo_merge.bat` 可在 variable font build 成功後自動呼叫 `bin\make_static_instances.bat`

## 輸入規則
- `-input` 必須是存在的 `*.ttf`
- `-output-dir` 必須是資料夾路徑；若不存在可自動建立

## 輸出規則
- 以 `fontTools.varLib.instancer` 產生 static TTF
- 檔名格式：
  - `<原檔名>-W300.ttf`
  - `<原檔名>-W350.ttf`
  - `<原檔名>-W400.ttf`
  - `<原檔名>-W450.ttf`
  - `<原檔名>-W500.ttf`
  - `<原檔名>-W550.ttf`
  - `<原檔名>-W600.ttf`
  - `<原檔名>-W650.ttf`
  - `<原檔名>-W700.ttf`

## Static 命名策略
- 每個 static font 都視為一套獨立單款字型，不和 variable font 共用 family grouping。
- family name 使用：
  - `ToneOZ-Quicksnow-W300`
  - `ToneOZ-Quicksnow-W350`
  - `ToneOZ-Quicksnow-W400`
  - `ToneOZ-Quicksnow-W450`
  - `ToneOZ-Quicksnow-W500`
  - `ToneOZ-Quicksnow-W550`
  - `ToneOZ-Quicksnow-W600`
  - `ToneOZ-Quicksnow-W650`
  - `ToneOZ-Quicksnow-W700`
- 每個 static font 的 `nameID 2` 使用 `Regular`。
- 每個 static font 的 `nameID 4` 使用和 family name 相同的字串。
- 每個 static font 的 `nameID 6`（PostScript name）需唯一，並和對應 family name 一致。
- 每個 static font 的 `nameID 16` 使用和 family name 相同的字串。
- 每個 static font 的 `nameID 17` 使用 `Regular`。
- `usWeightClass` 仍須分別為 `300/350/400/450/500/550/600/650/700`。
- 目的：
  - 可與 variable font `ToneOZ-Quicksnow` 同時安裝
  - 避免 Windows / Word 將 static 與 variable font 混成同一個 family
  - 避免 9 個 static font 彼此互相衝突

## function：make_static_instance
- 實作位置：`src\py\make_static_instances.py`
- 輸入：`input_ttf: Path`, `output_ttf: Path`, `weight: int`
- 輸出：一個 static TTF
- 行為：
  - 呼叫 `fontTools.varLib.instancer`
  - 固定 `wght=<weight>`
  - 實例化後需同步整理 static font metadata：
    - `nameID 1`
    - `nameID 2`
    - `nameID 3`
    - `nameID 4`
    - `nameID 6`
    - `nameID 16`
    - `nameID 17`
    - `OS/2.usWeightClass`

## function：apply_static_metadata
- 實作位置：`src\py\make_static_instances.py`
- 輸入：`font: TTFont`, `family_name: str`, `weight: int`
- 輸出：直接修改字型 metadata
- 行為：
  - 將每個 static font 視為獨立單款字型
  - `nameID 1/4/16` 使用 `ToneOZ-Quicksnow-W300` 這類 family name
  - `nameID 2/17` 使用 `Regular`
  - `nameID 6` 使用唯一 PostScript name
  - `nameID 3` 使用唯一字串，避免和 variable font 或其他 static font 衝突
  - `OS/2.usWeightClass` 設為對應權重

## function：build_default_instances
- 實作位置：`src\py\make_static_instances.py`
- 輸入：`input_ttf: Path`, `output_dir: Path`
- 輸出：9 個 static TTF
- 行為：
  - 依序產生 `300/350/400/450/500/550/600/650/700`

## 錯誤處理
- `-input` 不存在
- `-input` 非 `*.ttf`
- `fontTools.varLib.instancer` 執行失敗

## 驗收條件
1. 可由一個 variable TTF 產出 `300/350/400/450/500/550/600/650/700` 九個 static TTF。  
2. 檔名需帶對應字重後綴（`-W300` 等）。  
3. stderr 輸出時，每行前面需有 8 個空白。  
4. 每個 static font 需使用獨立 family name（`ToneOZ-Quicksnow-W300` 到 `ToneOZ-Quicksnow-W700`，包含 `W350/W450/W550/W650`）。  
5. 每個 static font 的 `nameID 6` 必須唯一，不可與 variable font 或其他 static font 重複。  
6. 若提供 `bin\make_static_instances.bat`，其行為需只是包裝呼叫 `src\py\make_static_instances.py`，不可和 Python 版本規格分叉。  
7. 每個 static font 的 `nameID 1/2/3/4/6/16/17` 與 `OS/2.usWeightClass` 都必須和對應獨立單款策略一致。  
