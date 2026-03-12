# SPEC_ufo_merge

## 目標
- 新增 `src\py\ufo_merge.py`。
- 本工具負責把多個由 FontForge 編輯過的 `.sfd` 字重來源，合併回指定的可變字型 `ttf`，並輸出新的 `ttf`。

## CLI
- 必須支援以下參數：
  - `-input`
  - `-with`
  - `-output`

## CLI 參數定義

### `-input`
- 為一個資料夾路徑。
- 資料夾內必須包含一個以上 `*.sfd` 檔案。
- 這些 `*.sfd` 為 FontForge 檔案，例如：
  - `Quicksand-VariableFont_wght-W300.ufo.sfd`
  - `Quicksand-VariableFont_wght-W700.ufo.sfd`
- 對於每個 `*.sfd`，同資料夾內必須存在一個對應的 `glyf_list_*.txt` 檔。
- 其中 `*` 必須與該 `sfd` 檔名相同。
- `glyf_list_*.txt` 每行一個 glyph 名稱，代表該 `sfd` 中被修改過的 glyph 清單，以下稱為 `modified_list`。

### `-with`
- 為一個來源 `*.ttf` 字型檔。
- 此檔案會作為合併基底，先轉為 UFO 專案，再將 `modified_list` 指定的 glyph 覆蓋進去。

### `-output`
- 為目標輸出的 `*.ttf` 檔名。

## 功能流程

### 1. 將每個 `*.sfd` 轉成 UFO3
- 針對 `-input` 資料夾中的每個 `*.sfd`：
  - 使用 FontForge 產生 `Unified Font Object UFO3`。
  - 輸出到 `_tmp\ufo_input`。
- 產出的 UFO 目錄名稱應可對應原始 `sfd` 檔名，例如：
  - `_tmp\ufo_input\Quicksand-VariableFont_wght-W300.ufo`
  - `_tmp\ufo_input\Quicksand-VariableFont_wght-W700.ufo`

### 2. 將 `-with` TTF 轉成 UFO 專案
- 使用 `src\py\varwideufo\varwideufo.py`，把 `-with` 指定的 `ttf` 轉換到 `_tmp\ufo_output`。
- `_tmp\ufo_output` 內應產生與字重對應的 UFO 專案內容。

### 3. 覆蓋修改過的 glyph
- 對於每個 `*.sfd` 對應的 `modified_list`：
  - `input_glyf_folder` 為 `_tmp\ufo_input\<ufo_name>\glyphs`
  - `output_glyf_folder` 為 `_tmp\ufo_output\<ufo_name>\glyphs`
- 將 `modified_list` 中列出的 glyph 檔案，從 `input_glyf_folder` 複製到 `output_glyf_folder`。
- 若目標檔案已存在，必須覆蓋。
- glyph 檔案格式為 `*.glif`。
- `modified_list` 中的 glyph 名稱需正確對應到 UFO `glyphs` 目錄下的檔名。

### 4. 由 UFO 專案重建輸出字型
- 覆蓋完成後，使用 `src\py\varwideufo\varwideufo.py`，把 `_tmp\ufo_output` 的 UFO 專案轉回 `-output` 指定的 `ttf`。

## 路徑與暫存規則
- 所有暫存檔案必須放在 `_tmp/` 下。
- 本功能至少使用以下暫存路徑：
  - `_tmp\ufo_input`
  - `_tmp\ufo_output`
- 最終輸出檔案寫到 `-output` 指定位置。

## 相依工具
- 必須依賴 FontForge，將 `*.sfd` 匯出為 UFO3。
- 必須依賴 `src\py\varwideufo\varwideufo.py`：
  - `ttf -> UFO`
  - `UFO -> ttf`

## 錯誤處理
- 以下情況必須明確報錯：
  - `-input` 不存在或不是資料夾。
  - `-input` 中找不到任何 `*.sfd`。
  - 任一 `*.sfd` 缺少對應的 `glyf_list_*.txt`。
  - `-with` 不存在或不是 `*.ttf`。
  - `modified_list` 中指定的 glyph 在來源 UFO 中不存在。
  - `_tmp\ufo_output` 中找不到對應字重的 UFO 或 `glyphs` 目錄。
  - FontForge 執行失敗。
  - `src\py\varwideufo\varwideufo.py` 執行失敗。
  - `-output` 副檔名不是 `*.ttf`。

## 建議實作結構
- `parse_args()`
- `find_sfd_inputs()`
- `resolve_modified_list_path()`
- `build_ufo_from_sfd()`
- `build_ufo_from_ttf()`
- `copy_modified_glyphs()`
- `build_ttf_from_ufo()`
- `main()`

## 驗收條件
1. 執行 `ufo_merge.py -input <folder> -with <font.ttf> -output <target.ttf>` 時，可正確處理多個 `*.sfd`。
2. 每個 `*.sfd` 都會先被轉成 `_tmp\ufo_input` 下的 UFO3。
3. `-with` 會先被轉成 `_tmp\ufo_output` 下的 UFO 專案。
4. `modified_list` 指定的 glyph 檔案會被正確覆蓋到 `_tmp\ufo_output`。
5. 最後可由 `_tmp\ufo_output` 成功輸出 `-output` 指定的 `ttf`。
6. 缺檔、路徑錯誤、glyph 不存在等情況，都會輸出可讀的錯誤訊息。

## 本次範圍限制
- 本規格僅定義 `ufo_merge.py` 的需求。
- 本次僅建立規格，不包含實作。
