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
- 若 `varwideufo.py` 的 `UFO -> TTF` 重建造成 contour direction 與母字型語意不一致，視為錯誤；此錯誤可能導致 Word 粗體顯示異常（例如筆畫反而變細）。
- 若 `varwideufo.py` 的 `UFO -> TTF` 重建遺失母字型原有的 `fvar` named instances、`STAT` axis values 或 `OS/2` style metadata，也視為錯誤；此錯誤可能導致 Word 對粗體或樣式連結判斷異常。
- 若最終字型在 Microsoft Word 中使用粗體按鈕時，`Light` 出現筆畫錯誤，或 `Medium` / `SemiBold` 完全沒有粗體變化，皆視為錯誤，嚴重程度相同。
- 本腳本轉印子程序或錯誤訊息到 stderr 時，每行前面需加 8 個空白，方便和主流程 stdout 區隔。
- variable font 的 anchor 若需隨字重自動變化，必須以 `W300/W700` 兩組 master anchors 參與 build 內插；不可只在最終 TTF 階段 patch 單一固定座標。
- `W300/W700` anchor masters 若啟用，build 過程不得在單一 master glyph 內產生 duplicate anchor；否則視為錯誤。
- `W300/W700` anchor masters 若啟用，最終字型必須保留來源字型的 kern，並與新建出的 variable `mark/mkmk` 合併。
- `W300/W700` anchor masters 若啟用，`fonttool_fix_cmap.py` 不可把中繼字型已建立好的 variable `GPOS/GDEF` 壓平成固定座標。

## CLI
- `-input`：來源資料夾（含 `*.sfd` 與 `glyf_update.txt`）
- `-with`：基底 variable `*.ttf`
- `-output`：輸出 `*.ttf`
- `-fix_stat_linked_bold`：可選，修補最終字型的 `STAT linked bold`（預設關閉）
- `--autohint`：可選，對最終輸出執行 `ttfautohint`（預設關閉）
- `--ttfautohint`：可選，指定 `ttfautohint.exe` 路徑（未指定時用預設路徑）
- `--auto-expand-refer-glyphs`：可選，啟用後會依 SFD `Refer` 關係遞迴擴充 `glyf_update.txt` 清單（預設開啟）
- `--no-auto-expand-refer-glyphs`：可選，停用 SFD `Refer` 遞迴擴充，只使用 `glyf_update.txt` 原始清單

## 輸入規則
### `-input`
- 必須是資料夾，且至少包含一個 `glyf\*.sfd`。
- 同資料夾必須有 `glyf_update.txt`（UTF-8）。
- `glyf_update.txt` 每行一個 glyph 名稱，表示所有 master 共用的更新清單。
- `*.sfd` master 預設放在 `glyf\` 子資料夾。
- anchor 工作用檔預設放在 `anchor\` 子資料夾，不得把它當成 master 參與 build。
- 若 `anchor\` 下同時存在 `ToneOZ-Quicksnow-W300_anchor.sfd` 與 `ToneOZ-Quicksnow-W700_anchor.sfd`，應優先視為 variable anchor masters。
- 單一 `ToneOZ-Quicksnow_anchor.sfd` 僅作為固定 anchor patch 的舊流程相容輸入。

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
- `glyf_update.txt` 為種子清單；不得被腳本改寫。
- 若啟用 `--auto-expand-refer-glyphs`（預設開啟）：
  - 先解析所有 master SFD 的 `Refer` 反向相依（`base -> dependents`）。
  - 只檢查「由 `glyf_update.txt` 種子可達」的 `Refer` 相依鏈；master 之間若不一致，需在單次執行中一次列出全部 mismatch，再報錯中止。
  - 以 BFS 遞迴擴充相依 glyph，且不可重複加入。
- 若啟用 `--no-auto-expand-refer-glyphs`：
  - 僅使用 `glyf_update.txt` 種子清單，不做 `Refer` 解析與遞迴擴充。
- 對每個 master：
  - `input_glyf_folder = _tmp\ufo_input\<ufo_name>\glyphs`
  - `output_glyf_folder = _tmp\ufo_output\<ufo_name>\glyphs`
- 若 glyph 已存在目標 UFO：覆蓋 `.glif`
- 若 glyph 不存在目標 UFO：新增 glyph，並同步更新：
  - `glyphs/contents.plist`
  - `lib.plist` 的 `public.glyphOrder`

### 4. 產生中繼字型
- 用 `varwideufo.py` 從 `_tmp\ufo_output` 建出中繼 TTF（放 `_tmp/`）。
- `varwideufo.py` 必須保留母字型原有的 `fvar` named instances、`STAT` axis values 與 `OS/2` style metadata，不可在中繼字型掉成 0 或退化。
- 若存在 `src\ufo\anchor\ToneOZ-Quicksnow-W300_anchor.sfd` 與 `src\ufo\anchor\ToneOZ-Quicksnow-W700_anchor.sfd`，其 anchors 應視為 variable font 的 anchor masters：
  - `W300` anchors 寫回對應 `W300` UFO
  - `W700` anchors 寫回對應 `W700` UFO
  - 再由 build 流程自動內插，不可先壓成單一固定 anchor

### 5. 修正 cmap/GSUB/GPOS/GDEF（JSON 規則驅動）
- 用 `src\py\fonttool_fix_cmap.py` 處理中繼 TTF，輸出最終 `-output`。
- `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需帶 `--copy_kern_T_left_only_to_J`。
- `--copy_kern_T_left_only_to_J` 的 kerning 複製必須在最終輸出階段對實際保留下來的 `GPOS kern` 生效，不可只改中途 JSON。
- `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需帶 `--name-json src\json\name_Quicksand-VariableFont_wght.json` 以套用改名字串與版號替換。
- `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需帶 `--anchor-rules-json src\json\fonttool_fix_anchor_rules.json` 以套用 anchor JSON。
- `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需帶 `--kern-rules-json src\json\fonttool_fix_kern_rules.json` 以套用最終 pair kerning override。
- 若啟用 `W300/W700` variable anchor masters，`ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時需另外提供來源字型路徑，供後段合併來源 kern 與新建出的 variable `mark/mkmk`。
- 若帶 `-fix_stat_linked_bold`，`ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需一併帶 `-fix_stat_linked_bold`。
- 規則來源：`src\json\fonttool_fix_cmap_rules.json`。
- `fonttool_fix_cmap.py` 必須保持 variable tables，不可退化成靜態字型。

### 6. 可選自動 Hint（ttfautohint）
- 若帶 `--autohint`，`ufo_merge.py` 在產生最終輸出後執行 `ttfautohint`：
  - input：`-output` 產生的 TTF
  - output：覆寫 `-output`
- 目的：改善 Word/小尺寸預覽的鋸齒感。
- 未帶 `--autohint` 時，維持目前不做額外 hint 的行為。

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
step 5. 在 JSON 增加一行規則，例如：`{"from":["ecircumflex","uni030C"],"to":"ecircumflex_uni030C"}`。若是大寫組合（例如 `Ecircumflex + uni030C`），要同時加 `.case` 規則：`{"from":["Ecircumflex","uni030C.case"],"to":"Ecircumflex_uni030C"}`。若是底線加上 U+0307，則加入：`{"from":["underscore","uni0307"],"to":"underscore_uni0307"}`。若要補 `uni030A` 組合，則加入：`{"from":["Y","uni030A"],"to":"Y_uni030A"}`、`{"from":["I","uni030A"],"to":"I_uni030A"}`、`{"from":["O","uni030A"],"to":"O_uni030A"}`、`{"from":["Y","uni030A.case"],"to":"Y_uni030A"}`、`{"from":["I","uni030A.case"],"to":"I_uni030A"}`、`{"from":["O","uni030A.case"],"to":"O_uni030A"}`、`{"from":["i","uni030A"],"to":"i_uni030A"}`、`{"from":["dotlessi","uni030A"],"to":"i_uni030A"}`、`{"from":["o","uni030A"],"to":"o_uni030A"}`、`{"from":["m","gravecomb"],"to":"m_gravecomb"}`、`{"from":["m","gravecomb.case"],"to":"m_gravecomb"}`。  
step 6. 執行 `ufo_merge.bat`。  
step 6.0. 若存在 `src\ufo\anchor\ToneOZ-Quicksnow_anchor.sfd`，`ufo_merge.bat` 需先執行 `src\py\extract_sfd_anchors.py` 更新 `src\json\fonttool_fix_anchor_rules.json`。若改採 `W300/W700` anchor masters，則此步驟可跳過。  
step 7. `ufo_merge.py` 先做 glyph merge 並產生中繼 TTF。  
step 8. `fonttool_fix_cmap.py` 讀規則，寫入 `GSUB.lookups.lookup_ccmp_6` substitution。  
step 8.1. `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時帶 `--copy_kern_T_left_only_to_J`，並在最終輸出階段套用 T-left -> J-left 的 kerning 複製（J 在後 kerning 保留）。  
step 8.2. `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時帶 `--name-json src\json\name_Quicksand-VariableFont_wght.json`，在同一輪 JSON 修補中完成 name table 套用與 `{}` 版號替換。  
step 8.2.0. 若先用 `src\py\extract_sfd_anchors.py` 從 `src\ufo\anchor\ToneOZ-Quicksnow_anchor.sfd` 匯出 `src\json\fonttool_fix_anchor_rules.json`，`ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時需一併帶 `--anchor-rules-json` 套用 anchor patch。  
step 8.2.0.e. `ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時，需一併帶 `--kern-rules-json src\json\fonttool_fix_kern_rules.json`，讓最終輸出可套用指定 pair kerning override（目前包含 `JJ = -80`）。  
step 8.2.0.a. 若要讓 variable font anchor 隨字重內插，需改用 `src\ufo\anchor\ToneOZ-Quicksnow-W300_anchor.sfd` 與 `src\ufo\anchor\ToneOZ-Quicksnow-W700_anchor.sfd` 作為 master anchors，於 build 前各自寫回對應 UFO；此情況下不得再依賴 step 8.2.0 的單一固定 anchor patch，且 `varwideufo.py` 不可再把來源字型舊 `GDEF/GPOS` 蓋回輸出。  
step 8.2.0.b. 當 step 8.2.0.a 啟用時，`reverse_glif_contours()` 不可在單一 GLIF 內重複插入同名 anchor；build 若出現 duplicate anchor warning 視為失敗。  
step 8.2.0.c. 當 step 8.2.0.a 啟用時，`fonttool_fix_cmap.py` 需把來源字型的 kern 與新建出的 variable `mark/mkmk` 合併，而不是整包覆蓋 `GPOS`。  
step 8.2.0.d. 當 step 8.2.0.a 啟用時，`fonttool_fix_cmap.py` 必須保留中繼字型原本的 variable `GPOS/GDEF`，不得把 `Format 3` anchor 壓平成固定 `Format 1`。  
step 8.2.1. 若帶 `-fix_stat_linked_bold`，`ufo_merge.py` 呼叫 `fonttool_fix_cmap.py` 時一併帶此開關，修補 `STAT` 中 `300/500/600 -> 700` 的 linked bold。  
step 8.3. 若帶 `--autohint`，`ufo_merge.py` 在最終輸出後呼叫 `ttfautohint` 進行自動 hint。  
step 8.4. `ufo_merge.bat` 在 variable font build 成功後，需自動呼叫 `bin\make_static_instances.bat`，產生 `_output\static_instances` 下的 5 個 static TTF。  
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
- `--autohint` 開啟時找不到 `ttfautohint.exe` 或執行失敗
- `varwideufo.py` 重建後，原始 glyph 的 contour direction 語意被系統性翻轉
- `varwideufo.py` 重建後，母字型原有的 `fvar` named instances、`STAT` axis values 或 `OS/2.fsSelection` 遺失/退化
- anchor JSON 套用時誤蓋掉其他 GPOS 修補
- `reverse_glif_contours()` 造成單一 master glyph 內 duplicate anchor
- 啟用 variable anchor masters 後，最終字型遺失來源字型的 kern
- 使用 `-fix_stat_linked_bold` 時，最終字型 `STAT` 未成功將 `300/500/600` linked 到 `700`
- 最終字型在 Word 中按粗體時，`Light` 出現筆畫錯誤，或 `Medium` / `SemiBold` 沒有任何粗體變化
- master 不相容導致 `fontmake` 失敗
- 啟用 `--auto-expand-refer-glyphs` 時，「由種子可達」的 `Refer` 相依在 master 間不一致（需一次列出全部 mismatch）

## 驗收條件
1. 可正確處理多個 `*.sfd`。  
2. `glyf_update.txt` 指定 glyph 可在所有 master 被合併。  
3. 新 glyph 可被新增並更新 `contents.plist` / `public.glyphOrder`。  
4. 最終輸出包含規則檔新增的 GSUB substitution。  
5. `GSUB.features` 維持 `ccmp_00002`、`ccmp_00003`。  
6. `GSUB.lookupOrder`、`GSUB.languages` 維持既有結構。  
7. 最終輸出仍為 variable font（`fvar`、`gvar`、`HVAR`、`STAT` 仍存在）。  
8. 當使用 `--autohint` 時，最終輸出需成功經過 `ttfautohint` 處理。  
9. 最終輸出中，原始 glyph 的 contour direction 語意不得因 `UFO -> TTF` 重建而被系統性翻轉。  
10. 中繼字型與最終輸出都必須保留母字型原有的 `fvar` named instances，不可掉成 0。  
11. 中繼字型與最終輸出都必須保留母字型原有的 `STAT` axis values，不可掉成 0。  
12. `OS/2.fsSelection` 不可因重建而退化成導致 Word 粗體/樣式連結異常的狀態。  
13. 最終字型在 Word 中按粗體時，`Light` 不可出現筆畫錯誤，且 `Medium` / `SemiBold` 不可完全沒有粗體變化。  
14. 當使用 `-fix_stat_linked_bold` 時，最終字型的 `STAT` 必須將 `300/500/600` 對應 axis value 都 linked 到 `700`。  
15. 當存在 `src\json\fonttool_fix_anchor_rules.json` 時，最終字型需套用其中指定的 base anchors，且不可蓋掉其他 GPOS 修補。  
16. 本腳本輸出的 stderr 訊息，每行前面需有 8 個空白。  
17. 執行 `ufo_merge.bat` 成功後，需同步產出 `_output\static_instances` 下的 `W300/400/500/600/700` static TTF。  
18. 若 variable font 要支援依字重內插的 anchors，`W300/W700` anchor masters 必須在 master 階段參與 build，而不是只在最終 TTF 階段套固定 anchor。  
19. 若啟用 `W300/W700` anchor masters，build 過程不得出現 duplicate anchor warning。  
20. 若啟用 `W300/W700` anchor masters，最終字型必須同時保有來源字型的 kern 與新建出的 variable `mark/mkmk`。  
21. 若啟用 `W300/W700` anchor masters，最終字型的 `GPOS` anchor 必須仍可隨字重變化，不得在後段被壓平成固定值。  
22. `--copy_kern_T_left_only_to_J` 啟用時，最終輸出字型中的 `Je`、`JA` 等 pair 必須實際反映 `Te`、`TA` 的 kerning。  
23. 當存在 `src\json\fonttool_fix_kern_rules.json` 時，最終輸出字型需套用其中指定的 pair override；目前 `JJ` 必須為 `-80`。  
