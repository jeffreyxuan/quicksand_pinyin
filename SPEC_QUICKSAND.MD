# SPEC_QUICKSAND

來源: `C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\spec.md`

## 與 Quicksand 相關的規格摘錄

### 3.3 字型資源管理原則
- 包含 varwide 候選字體（例如 Nunito、Quicksand）也要複製進 `res/fonts` 後再被 style key 引用。

### 10. 偏好紀錄
- 可變寬拼音字體候選: `Nunito`、`Quicksand`（使用者偏好，後續以 `*_varwide` style 優先測試）。

### 12.5 QuickSand 改造補充規格
- Quicksand 為了支援台語組合，需加入 `ⁿ`、`ᴺ`。
- Quicksand 台語組合需要加入 i̍ `i_hungarumlautcomb`、i̋`i_verticallineabovecomb`。在 FontForge 中使用 `Encoding -> Add Encoding Slots`，並於 `Glyph Info` 設定 `Glyph Name`。GSUB/ccmp 加入替換規則
- Combining mark 需要加入：◌́◌̀◌̂◌̌◌̄◌̍◌̋◌̆◌͘。
- 為了支援台語組合, Quicksand uni0358 在配合 o͘ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘ O͘Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘ 時, 左緣與O的右緣切齊。
- 為了支援台語組合, Quicksand uni0358 的高度在配合大寫O͘Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘ 的時候需要調高, 高到 uni0358下緣與O的上緣同高度。
- 為了支援台語組合, Quicksand須補 uni030D uni0358。
- 大寫 Q 必須改右下角尾巴寫法。
- 大寫 R 必須改右下角尾巴寫法。
- 必備字符新增：`ǖǘǚǜ`、`ǕǗǙǛ`、`ḿ`、`Ḿ`、`ǹ`、`Ǹ`。
- `u` 以及 `ūúǔùüǖǘǚǜ` 必須有尾巴。
- 拼音聲調高度規則：
  - 第 2、4 聲調符號需高於 `b/h/k` 頂部。
  - `l` 要略高於 `b`。
  - 第 2、4 聲調符號需再高於 `l` 頂部。
- 需調整聲調位置的字：
  - `ế ề Ế Ề`
  - `Á À É È Í Ì Ó Ò Ú Ù`
- `í ì` 需要做聲調符號左右位移（非僅高度）。
- `Á À É È Í Ì Ó Ò` 聲調需抬高 `1 step`，避免小字尺寸黏連。

### 12.6 拼音字體測試備註
- 曾測字重方案：`Quicksand-Medium` + FontForge `weightadd -16`。











### 13. 使用 ttfautohint 重建字體 instruction
- 請從官方網站下載 `ttfautohint`：`https://freetype.org/ttfautohint/`。
- 安裝後固定使用以下 Windows 執行檔路徑：`C:\tool\ttfautohint\ttfautohint.exe`。
- 重建字體時，將輸入與輸出字體檔放在命令最後兩個參數。
- 範例：

  ```shell
  C:\tool\ttfautohint\ttfautohint.exe input.ttf output.ttf
  ```

### 14. `ff_rehint.py`：補回遺失的 instruction
- CLI 參數：`-original`、`-input`、`-output`。
- `-original`：原始 TTF（例如 `res\Quicksand-Regular.ttf`）。
- `-input`：經 FontForge 修改且可能遺失 instruction 的 TTF（例如 `_output\Quicksand-Regular_pinyin.ttf`）。
- `-output`：輸出字體檔。
- 流程：
  1. 使用 `otfccdump` 匯出 `-original` 與 `-input` 的 JSON。
  2. 比對 glyph instruction，找出「`-original` 有 instruction、`-input` 沒有 instruction」的 glyph。
  3. 對 `-input` 執行 `ttfautohint`，再以 `otfccdump` 匯出重建後 JSON。
  4. 只將上述缺失 glyph 的 instruction 回填到 `-input` JSON。
  5. 使用 `otfccbuild` 產生 `-output`。
- 若有執行 `ttfautohint`，需將 command line 印到 console 以利 debug。
- `ttfautohint` 預設路徑：`C:\tool\ttfautohint\ttfautohint.exe`。

### 15. `ff_rename.py`：套用 name table 並更新版本欄位
- CLI 參數：`-input`、`-output`、`-namejson`。
- `-namejson`：字型 name table JSON（例如 `C:\Users\jeffreyx\Documents\git\quicksand_pinyin\src\json\name_Quicksand-Regular.json`）。
- `-input`：輸入字型檔。
- `-output`：輸出字型檔。
- 一開始以目前日期產生 `version`，格式為 `0.YYMMDD`（例如 `0.260310`）。
- `-namejson` 中所有 `Version {}` 或含 `{}` 的版本 placeholder，皆以 `version` 取代。
- 設定 `OS_2.achVendID = "TNOZ"`。
- 設定 `OS_2.ulCodePageRange1` 加入 FE 相關 bits：`jis`、`gbk`、`big5`、`korean`（其餘既有 bits 保留）。
- 設定 `head.created = round(now_time - base_time)`（Mac epoch；例如 `3712652272`）。
- 設定 `head.fontRevision = version`。
- 流程：
  1. `otfccdump` 匯出 `-input` JSON。
  2. 套用 `-namejson` 與上述欄位規則。
  3. `otfccbuild` 產生 `-output`。
### 16. `ff_regulay.py`：由 bat 傳入輸入與輸出檔名
- CLI 參數：`-input`、`-output`。
- `-input`：輸入 SFD 檔。
- `-output`：輸出 TTF 檔。
- 不可在程式內寫死 Quicksand 檔名，實際檔名由呼叫端 bat 決定。

### 17. 批次腳本流程表
- 通則：
  - 所有與輸出檔名相關的決策都由 `*.bat` 決定。
  - `build.bat` 一開始宣告 `INPUT_FILEPATH=src\ff\Quicksand-Regular_pinyin.sfd`。
  - `build.bat` 與其呼叫的各個 bat，都必須先切換到 repo 根目錄後再執行後續命令，確保從 `bin\` 啟動時相對路徑仍正確。
  - 各 bat 之間必須透過參數傳遞 input/output；前一步的 output 要當成下一步的 input。

| Step | BAT | Input | Output |
|---|---|---|---|
| 1 | `ff_regular.bat` | `INPUT_FILEPATH` | `_output\<basename>_init.ttf` |
| 2 | `ff_fix_cmap.bat` | step 1 output | `_output\<basename>_fix_cmap.ttf` |
| 3 | `ff_rehint.bat` | step 2 output | `_output\<basename>_rehint.ttf` |
| 4 | `ff_rename.bat` | step 3 output | `_output\<basename>_rename.ttf` |
| 5 | `ff_weight_reduce.bat` | step 4 output | `_output\<basename>_weightadd-16.ttf` |
| 6 | `build.bat` final copy | step 4 output | `_output\<basename>.ttf` |
| 7 | `build.bat` publish copy | step 6 output | `C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest\<basename>.ttf` |
