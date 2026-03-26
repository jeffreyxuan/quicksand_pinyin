# SPEC_fonttool_fix_cmap

## uni0358（右上點）定位修補
- `fix_uni0358` 需改為「小寫優先基準」：
  - 若 subtable 同時有 `O/o`，`uni0358` 的 mark anchor 先以小寫 `o` 幾何與 anchor 計算。
  - 避免沿用大寫 `O` 基準導致 `o͘`（`o + uni0358`）右上點飄太高。
- `O*` 與 `o*` 的 `anchor5` 仍須各自回填，保持大小寫都可附著。

## o̍͘ / O̍͘（第二層附著）修補
- `fonttool_fix_cmap.py` 需補 `mkmk` 鏈路，讓 `uni030D` 可附著到 `uni0358`：
  - 在 `gpos_mark_to_mark` 的對應 subtable，確保 `marks["uni030D"]` 存在。
  - 同時在 `bases["uni0358"]` 補上 `uni030D` 所用 class 的 anchor（例如 `anchor0`）。
- 目的：`o + uni0358 + uni030D` 與 `O + uni0358 + uni030D` 皆可正常顯示。

## U+25CC（◌）修補
- `fonttool_fix_cmap.py` 需補強 `U+25CC` 的 combining 行為，避免 `◌ + mark` 失效。
- 修補內容：
  - `cmap`：確保 `U+25CC -> uni25CC`。
  - `GDEF.glyphClassDef`：確保 `uni25CC` 為 base class（值 `1`）。
  - `GPOS gpos_mark_to_base`：在各 subtable 的 `bases.uni25CC` 補齊 mark class 對應 anchor（優先沿用 `a/o/A/O` 的 base anchors，避免上方符號過高）。
- 輸出需列印 `dotted-circle fix stats`，至少包含：
  - `cmap_updates`
  - `class_updates`
  - `subtables_touched`
  - `base_anchor_updates`

## 目標
- 新增 `src\py\fonttool_fix_cmap.py`，以 JSON 設定驅動方式維護 `GSUB` 規則。
- 讓未來新增組合字時，不需要重寫 Python 程式，只需更新 JSON。
- 最終輸出字型必須保留 variable font 資料表（`fvar`、`gvar`、`HVAR`、`STAT`）。

## 範例
- 範例：`ecircumflex + uni030C`
- 解法：新增預組字 `ecircumflexuni030C`，再加一條 `GSUB ligature` 規則。
- 方法：`OpenType GSUB ligature substitution`（由 JSON 設定驅動）。

## 規則檔
- 規則檔路徑：`src\json\fonttool_fix_cmap_rules.json`
- 規則檔以 UTF-8 儲存。
- 每筆規則至少包含：
  - `from`（字串陣列）
  - `to`（字串）
- 基本範例：
  - `{"from":["ecircumflex","uni030C"],"to":"ecircumflexuni030C"}`

## 既有 GSUB 結構維護原則（以目前字型狀態為準）
- 沿用既有 feature：`ccmp_00002`、`ccmp_00003`（不新增 `ccmp_00000`）。
- 沿用既有 lookup：`lookup_ccmp_6`（`type = gsub_ligature`）。
- `GSUB.lookupOrder` 維持現有順序（不新增新 lookup name）。
- `GSUB.languages` 維持現有掛接（`DFLT_DFLT`、`latn_DFLT` 與既有 `latn_*`）。

## Kerning 複製（X -> I）
- 新增可選開關：`--copy-kern-x-to-i`（預設關閉）。
- 開啟時，在同一份 `otfccdump` JSON 內執行 `copy_kern_X_to_I`，不做第二次 dump/build。
- 複製範圍：
  - `X` 在前：`(X, R) -> (I, R)`
  - `X` 在後：`(L, X) -> (L, I)`
- 僅處理 `GPOS.features.kern` 掛接的 `gpos_pair` lookup。

## function：copy_kern_X_to_I
- 實作位置：`src\py\fonttool_fix_cmap.py`
- 目的：把 `X` 的前後 kerning 規則複製給 `I`。
- 輸入：`ttf_json: Dict[str, Any]`
- 回傳統計至少包含：
  - `x_left_rules_found`
  - `x_right_rules_found`
  - `i_left_rules_added_or_updated`
  - `i_right_rules_added_or_updated`
  - `skipped_conflicts`
- 輸出列印需包含 `copy_kern_X_to_I stats`，並標示 `enabled=0/1`。

## Kerning 複製（T-left -> J-left）
- 新增可選開關：`--copy-kern-t-left-to-j`（預設關閉，並相容別名 `--copy_kern_T_left_only_to_J`）。
- 開啟時，在同一份 `otfccdump` JSON 內執行 `copy_kern_T_left_only_to_J`，不做第二次 dump/build。
- 複製範圍：
  - `T` 在前：`(T, R) -> (J, R)`（overwrite）
- 保留範圍：
  - `J` 在後：`(L, J)` 的既有 kerning 必須保留不變。
- 僅處理 `GPOS.features.kern` 掛接的 `gpos_pair` lookup。

## function：copy_kern_T_left_only_to_J
- 實作位置：`src\py\fonttool_fix_cmap.py`
- 目的：只把 `T` 在前的 kerning 複製到 `J` 在前。
- 輸入：`ttf_json: Dict[str, Any]`
- 回傳統計至少包含：
  - `t_left_rules_found`
  - `j_left_rules_added_or_updated`
  - `j_right_rules_preserved`
  - `skipped_conflicts`
- 輸出列印需包含 `copy_kern_T_left_only_to_J stats`，並標示 `enabled=0/1`。

## 新增組合字流程
step 1. 在 `W300`、`W700` 的 SFD 都新增 glyph `ecircumflexuni030C`（`Encoding -> Add Encoding Slots`，設定 `Glyph Name`）。  
step 2. 在 `W300`、`W700` 都完成 `ecircumflexuni030C` 字形。  
step 3. 在 `glyf_update.txt` 加入 `ecircumflexuni030C`（若有改 `ecircumflex` / `uni030C` 也一起列）。  
step 4. 建立規則檔：`C:\Users\jeffreyx\Documents\git\quicksand_pinyin\src\json\fonttool_fix_cmap_rules.json`。  
step 5. 在規則 JSON 增加一行設定，例如：`{"from":["ecircumflex","uni030C"],"to":"ecircumflex_uni030C"}`。若是大寫組合（例如 `Ecircumflex + uni030C`），要同時加 `.case` 規則：`{"from":["Ecircumflex","uni030C.case"],"to":"Ecircumflex_uni030C"}`。  
step 6. 執行 `ufo_merge.bat`。  
step 7. `ufo_merge.py` 先做 glyph merge 並產出中繼 TTF。  
step 8. `fonttool_fix_cmap.py` 讀取 rules JSON，並在 `GSUB.lookups.lookup_ccmp_6`（`type = gsub_ligature`）加入 substitution：`{"from":["ecircumflex","uni030C"],"to":"ecircumflexuni030C"}`。  
step 9. `fonttool_fix_cmap.py` 維持 `GSUB.features` 使用現有 feature：`ccmp_00002`、`ccmp_00003`（不新增 `ccmp_00000`）。  
step 10. `fonttool_fix_cmap.py` 維持 `GSUB.lookupOrder` 現有順序（不新增新 lookup name；沿用 `lookup_ccmp_6`）。  
step 11. `fonttool_fix_cmap.py` 維持 `GSUB.languages` 現有掛接（`DFLT_DFLT`、`latn_DFLT` 與既有 `latn_*`）。  
step 11.1. 若帶 `--copy-kern-x-to-i`，`fonttool_fix_cmap.py` 在同一份 JSON 內執行 `copy_kern_X_to_I`，將 X 前後 kerning 複製到 I。  
step 11.2. 若帶 `--copy-kern-t-left-to-j`（或 `--copy_kern_T_left_only_to_J`），`fonttool_fix_cmap.py` 在同一份 JSON 內執行 `copy_kern_T_left_only_to_J`，只複製 T 在前 kerning 到 J 在前（保留 J 在後 kerning）。  
step 12. 建立 `verify_gsub_rules.py`（例如放在 `src\py\verify_gsub_rules.py`），用來檢查「規則存在 + shaping 命中」：  
- `lookup_ccmp_6` 是否存在目標 substitution  
- `features` 是否仍為 `ccmp_00002`、`ccmp_00003`  
- shaping 驗證是否命中目標 glyph（例如 `U+00EA+U+030C -> ecircumflex_uni030C`、`U+00CA+U+030C` 含 `.case` 路徑 -> `Ecircumflex_uni030C`）  
- `lookupOrder` 是否未新增新 lookup name  
- `languages` 是否維持既有掛接  
- 輸出字型是否仍保留 `fvar/gvar/HVAR/STAT`  
step 13. `Codex` 執行 `verify_gsub_rules.py` 自動驗證，並回報結果（包含 `ufo_merge.bat` build 是否通過，作為可插值相容檢查結果）。

## 驗收條件
1. 新增組合字規則時，只需更新 `fonttool_fix_cmap_rules.json`，不需改 Python。  
2. 最終字型可查到新增 substitution。  
3. 最終字型 `GSUB.features` 仍沿用 `ccmp_00002`、`ccmp_00003`。  
4. 最終字型 `GSUB.lookupOrder`、`GSUB.languages` 維持既有結構。  
5. 最終字型仍為 variable font（`fvar`、`gvar`、`HVAR`、`STAT` 仍存在）。  
6. 當使用 `--copy-kern-x-to-i` 時，最終字型需完成 X->I 的前後 kerning 複製。  
7. 當使用 `--copy-kern-t-left-to-j`（或 `--copy_kern_T_left_only_to_J`）時，最終字型需完成 `(T, R) -> (J, R)` 的覆蓋複製。  
8. 當使用 `--copy-kern-t-left-to-j`（或 `--copy_kern_T_left_only_to_J`）時，既有 `(L, J)` kerning 必須保持不變。  
