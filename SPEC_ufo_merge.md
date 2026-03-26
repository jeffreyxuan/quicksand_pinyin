# SPEC_ufo_merge

## uni0358（o͘）定位要求
- 最終修補（`fonttool_fix_cmap.py`）中的 `fix_uni0358` 必須採用小寫優先基準：
  - 若同一 subtable 具有 `O/o` 參考，`uni0358` mark anchor 先以 `o` 計算，避免 `o͘` 飄高。
  - 之後再回填 `O*` / `o*` 的 `anchor5` base anchors。

## o̍͘ / O̍͘（mkmk）要求
- 最終修補（`fonttool_fix_cmap.py`）需確保 `uni030D` 可疊到 `uni0358`：
  - `gpos_mark_to_mark` 內要有 `marks["uni030D"]`。
  - `gpos_mark_to_mark` 內要有 `bases["uni0358"]` 對應 class anchor。

## U+25CC（◌）修補要求
- 最終修補階段（`fonttool_fix_cmap.py`）需確保 `◌ + combining mark` 在輸出字型可用。
- 必做項目：
  - `cmap` 補齊 `U+25CC -> uni25CC`。
  - `GDEF.glyphClassDef` 將 `uni25CC` 設為 base class（`1`）。
  - `GPOS gpos_mark_to_base` 的 `bases.uni25CC` 補齊必要 anchors（優先沿用 `a/o/A/O` 既有 anchors，避免符號過高）。

## 目標
- 新增 `src\py\ufo_merge.py`。
- 將多個 FontForge 編輯過的 `*.sfd` 變更，合併回 variable TTF。
- 最終輸出必須保持 variable font（保留 `fvar`、`gvar`、`HVAR`、`STAT`）。

## CLI
- `-input`：來源資料夾（含 `*.sfd` 與 `glyf_update.txt`）
- `-with`：基底 variable `*.ttf`
- `-output`：輸出 `*.ttf`

## 輸入規則
### `-input`
- 必須是資料夾，且至少包含一個 `*.sfd`。
- 同資料夾必須有 `glyf_update.txt`（UTF-8）。
- `glyf_update.txt` 每行一個 glyph 名稱，表示所有 master 共用的更新清單。

### `-with`
- 必須是存在的 `*.ttf`。

### `-output`
- 必須是 `*.ttf` 路徑。

## FontForge 新增字符前置操作
- 若需新增原本不存在的字元，先在 FontForge 使用 `Encoding -> Add Encoding Slots`。
- 再於 `Glyph Info` 設定：
  - `Glyph Name`
  - `Unicode Value`（若是有 Unicode 的字元）
- 若要參與 variable build，所有插值 master 都要同步新增。

## 主流程
### 1. SFD 轉 UFO3
- 每個 `*.sfd` 轉成 UFO3，輸出到 `_tmp\ufo_input`。

### 2. 基底 TTF 轉 UFO
- 用 `src\py\varwideufo\varwideufo.py` 將 `-with` 轉到 `_tmp\ufo_output`。

### 3. 合併 glyph（依 `glyf_update.txt`）
- 對每個 master：
  - `input_glyf_folder = _tmp\ufo_input\<ufo_name>\glyphs`
  - `output_glyf_folder = _tmp\ufo_output\<ufo_name>\glyphs`
- 若 glyph 已存在目標 UFO：覆蓋 `.glif`
- 若 glyph 不存在目標 UFO：新增 glyph，並同步更新：
  - `glyphs/contents.plist`
  - `lib.plist` 的 `public.glyphOrder`

### 4. 產生中繼字型
- 用 `varwideufo.py` 從 `_tmp\ufo_output` 建出中繼 TTF（放 `_tmp/`）。

### 5. 修正 cmap/GSUB/GPOS/GDEF（JSON 規則驅動）
- 用 `src\py\fonttool_fix_cmap.py` 處理中繼 TTF，輸出最終 `-output`。
- `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需帶 `--copy_kern_T_left_only_to_J`。
- 規則來源：`src\json\fonttool_fix_cmap_rules.json`。
- `fonttool_fix_cmap.py` 必須保持 variable tables，不可退化成靜態字型。

## GSUB 維護原則（目前字型狀態）
- 沿用既有 feature：`ccmp_00002`、`ccmp_00003`（不新增 `ccmp_00000`）。
- 沿用既有 lookup：`lookup_ccmp_6`（`type = gsub_ligature`）。
- `GSUB.lookupOrder` 維持原順序（不新增新 lookup name）。
- `GSUB.languages` 維持既有掛接（`DFLT_DFLT`、`latn_DFLT`、既有 `latn_*`）。

## 新增組合字流程（與 SPEC_fonttool_fix_cmap 一致）
step 1. 在 `W300`、`W700` 新增目標 glyph（例：`ecircumflexuni030C`）。  
step 2. 在兩個 master 完成字形。  
step 3. 在 `glyf_update.txt` 加入該 glyph。  
step 4. 建立 `src\json\fonttool_fix_cmap_rules.json`。  
step 5. 在 JSON 增加一行規則，例如：`{"from":["ecircumflex","uni030C"],"to":"ecircumflex_uni030C"}`。若是大寫組合（例如 `Ecircumflex + uni030C`），要同時加 `.case` 規則：`{"from":["Ecircumflex","uni030C.case"],"to":"Ecircumflex_uni030C"}`。  
step 6. 執行 `ufo_merge.bat`。  
step 7. `ufo_merge.py` 先做 glyph merge 並產生中繼 TTF。  
step 8. `fonttool_fix_cmap.py` 讀規則，寫入 `GSUB.lookups.lookup_ccmp_6` substitution。  
step 8.1. `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時帶 `--copy_kern_T_left_only_to_J`，套用 T-left -> J-left 的 kerning 複製（J 在後 kerning 保留）。  
step 9. `fonttool_fix_cmap.py` 維持 `GSUB.features = ccmp_00002 / ccmp_00003`。  
step 10. `fonttool_fix_cmap.py` 維持 `GSUB.lookupOrder`。  
step 11. `fonttool_fix_cmap.py` 維持 `GSUB.languages`。  
step 12. 建立 `src\py\verify_gsub_rules.py` 進行「結構 + shaping」檢查：除了確認 GSUB 規則存在，也要驗證實際輸入序列可命中目標 glyph（例如 `U+00EA+U+030C -> ecircumflex_uni030C`、`U+00CA+U+030C` 含 `.case` 路徑 -> `Ecircumflex_uni030C`）。  
step 13. Codex 執行 `verify_gsub_rules.py` 回報驗證結果（含 build 是否通過）。

## 錯誤處理
- `-input` 不存在或不是資料夾
- 找不到 `*.sfd`
- 找不到 `glyf_update.txt`
- `-with` 不存在或非 `*.ttf`
- `-output` 非 `*.ttf`
- 來源/目標 UFO 缺必要檔案（`glyphs`、`contents.plist`、`lib.plist`）
- `fontforge` / `varwideufo.py` / `fonttool_fix_cmap.py` 執行失敗
- master 不相容導致 `fontmake` 失敗

## 驗收條件
1. 可正確處理多個 `*.sfd`。  
2. `glyf_update.txt` 指定 glyph 可在所有 master 被合併。  
3. 新 glyph 可被新增並更新 `contents.plist` / `public.glyphOrder`。  
4. 最終輸出包含規則檔新增的 GSUB substitution。  
5. `GSUB.features` 維持 `ccmp_00002`、`ccmp_00003`。  
6. `GSUB.lookupOrder`、`GSUB.languages` 維持既有結構。  
7. 最終輸出仍為 variable font（`fvar`、`gvar`、`HVAR`、`STAT` 仍存在）。  
