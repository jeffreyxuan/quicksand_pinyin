# varwideufo.py spec

## Goal
Build a single CLI tool named `varwideufo.py` that can do both directions:

1. Convert a **variable weight font** (`.ttf` / `.otf`) into a **UFO project**.
2. Convert a **UFO project** back into a **variable weight font** (`.ttf`).

The script is intended for engineering workflows, reverse-engineering, and patching variable fonts with a UFO-based editing step in the middle.

## CLI
The script must support exactly these primary flags:

- `-input`
- `-output`

### Examples

Convert variable font to UFO project:

```bash
python varwideufo.py -input Quicksand-VF.ttf -output ./ufo_project
```

Convert UFO project back to variable font:

```bash
python varwideufo.py -input ./ufo_project/Quicksand.designspace -output ./build/Quicksand-VF.ttf
```

Acceptable UFO-side inputs:

- a `.designspace` file
- a `.ufo` path, as long as a sibling `.designspace` exists
- a directory containing exactly one `.designspace`

## Direction detection
The tool should auto-detect mode from `-input`:

- `.ttf` / `.otf` => **VF to UFO**
- `.designspace` / `.ufo` / directory => **UFO to VF**

No extra mode flag is required.

## Scope

### Supported input for VF to UFO
- OpenType variable fonts with an `fvar` table
- Must contain a `wght` axis
- Current implementation target: **glyf-based TrueType outlines**

### Unsupported or out of scope
- Full fidelity recovery of original source data
- CFF/CFF2 reverse extraction in the first version
- Multiple designspace files inside one input directory
- 100% restoration of original kerning groups, guidelines, layer metadata, editor-private data, or build history

## Functional requirements

### A. Variable font -> UFO project
When `-input` is a variable font:

1. Validate that the font has:
   - `fvar`
   - `wght` axis
2. Read the `wght` axis min/default/max values.
3. Instantiate static masters at:
   - minimum weight
   - default weight
   - maximum weight
4. Convert each instantiated font into a standalone `.ufo`.
5. Generate one `.designspace` file that references the created UFO masters.
6. The generated source filenames in the `.designspace` must resolve correctly relative to the `.designspace` file itself.
7. Write everything under `-output`.
8. 產生的 UFO 專案必須記錄原始來源字型路徑，使重建步驟在新增 glyph 或新增 cmap 對應的情況下，仍可判定是否保留原始相容資料表。

### Output layout example

```text
ufo_project/
  Quicksand-W300.ufo/
  Quicksand-W400.ufo/
  Quicksand-W700.ufo/
  Quicksand.designspace
```

### UFO content requirements
Each generated UFO should include at least:

- `metainfo.plist`
- `fontinfo.plist`
- `layercontents.plist`
- `glyphs/contents.plist`
- `glyphs/*.glif`
- `lib.plist`
- `groups.plist`
- `kerning.plist`
- `features.fea`

The UFO only needs to be **minimal but valid** and editable in typical UFO-capable editors.
- Generated GLIF filenames must remain unique on case-insensitive filesystems such as Windows.

### Glyph extraction requirements
For the first version:

- Extract glyph order
- Extract Unicode mapping from cmap
- Extract advance widths from `hmtx`
- Extract outlines from `glyf`
- Support:
  - simple glyphs
  - composite glyphs
- Write contours/components to GLIF format 2 XML

### B. UFO project -> variable font
When `-input` points to a designspace/UFO/project directory:

1. Resolve the matching `.designspace` file.
2. Use `fontmake` to build a variable font.
3. Invoke `fontmake` with the `.designspace` directory as the working directory so relative UFO source paths resolve correctly.
4. Write the built variable `.ttf` to `-output`.
5. 若 UFO 專案中含有原始來源字型 metadata，且重建結果仍符合原始資料表保留規則，則應保留原始來源字型中的相容資料表，包括 `fvar`、`STAT`、`OS/2`、`GDEF`、`GPOS`、`GSUB`、`prep`、`gasp`、`name`。
6. Fail clearly if `fontmake` is not installed.
7. 重建後的原始 glyph contour direction 語意必須與來源字型一致；若被系統性翻轉，視為錯誤。
8. 實作上可在 `fontmake` 前對臨時建置用 UFO 專案做 contour 反轉補償，但不可直接污染使用者原始 UFO 專案檔案。

### Contour direction 錯誤定義
以下情況明確定義為錯誤，而不是可接受差異：

- `TTF -> UFO` 結果正常，但 `UFO -> TTF` 後原始 simple glyph 的 contour direction 被系統性翻轉。
- 翻轉後雖仍可顯示，但在 Microsoft Office Word 等環境中造成粗體顯示異常（例如筆畫變細）。

本工具不可將此情況視為單純編譯器慣例差異；必須視為需要修正的重建 bug。

### Variable metadata 錯誤定義
以下情況也明確定義為錯誤，而不是可接受差異：

- 來源 variable font 原本有 `fvar` named instances，但重建後掉成 0。
- 來源 variable font 原本有 `STAT` axis values，但重建後掉成 0。
- `OS/2.fsSelection` 因重建退化，導致 Microsoft Word 等環境對粗體或樣式連結的判斷異常。
- 最終字型在 Microsoft Word 中使用粗體按鈕時，`Light` 出現筆畫錯誤，或 `Medium` / `SemiBold` 完全沒有粗體變化。

此類 metadata 遺失即使 outline 仍可顯示，也視為需要修正的重建 bug。

### 原始資料表保留規則
重建 variable font 時，若 UFO 專案中含有原始來源字型 metadata，且重建結果仍符合下列條件，則應保留原始來源字型中的相容資料表：

- 原始 glyph 全部仍存在於重建後字型中。
- 原始 glyph 的順序未被改動。
- 新 glyph 可附加在原始 glyph 集合之後。
- 原始 cmap 的所有 codepoint 對應仍指向相同 glyph。
- 可另外新增新的 cmap 對應。

若符合上述條件，應保留原始來源字型中的：

- `fvar`
- `STAT`
- `OS/2`
- `GDEF`
- `GPOS`
- `GSUB`
- `prep`
- `gasp`
- `name`

重建步驟不可再要求重建後字型與原始來源字型的 glyph order 或 cmap 必須完全相同。

若不符合上述條件，則應跳過保留流程，並輸出可讀的 warning。

## Dependencies

### Required Python library
- `fontTools`

### Required external tool for UFO -> VF
- `fontmake`

Recommended install:

```bash
pip install fonttools fontmake
```

## Error handling
The script should fail with a clear message when:

- input path does not exist
- input font is not variable
- input font has no `wght` axis
- input font is not glyf-based for VF -> UFO
- no designspace file is found for UFO -> VF
- multiple designspace files are found where one is required
- `fontmake` is missing for UFO -> VF
- `-output` type is incompatible with the chosen direction

### Warning 行為
若原始資料表保留流程被跳過，工具必須輸出可讀的 warning，說明原因至少包含以下其中之一：

- 缺少原始來源字型 metadata
- 原始 glyph 在重建後字型中遺失
- 原始 glyph 順序被改動
- 原始 cmap 對應被改動

## Build strategy details

### Reverse direction notes
The generated UFO project is a **reconstruction**, not the original source.

That means the script is expected to recover a practical editable project, not a bit-identical source tree.

Expected losses compared with the original authoring source may include:

- private editor metadata
- layer organization
- guideline data
- original interpolation setup beyond min/default/max masters
- group-based kerning semantics if not recoverable

### Forward direction notes
The rebuild path relies on `fontmake`, which assumes the UFO and designspace are valid for interpolation.
If the user edits masters in a way that breaks point compatibility, the build may fail. This is expected and should be surfaced as-is.
`fontmake` 若輸出與來源字型不同的 contour direction 慣例，不可直接接受為最終結果；工具需以來源字型語意為準。
`fontmake` 若未重建出來源字型原有的 `fvar` named instances、`STAT` axis values 或正確的 `OS/2` style metadata，也不可直接接受為最終結果；工具需以來源字型 metadata 為準。

## Non-goals
Do not implement in v1:

- GUI
- automatic point-compatibility repair
- avar/STAT authoring UI
- named-instance recreation beyond what `fontmake` produces
- full CFF2 support
- auto-discovery of intermediate masters from arbitrary deltas

## Suggested implementation structure

```text
varwideufo.py
  parse_args()
  detect_direction()
  variable_font_to_ufo_project()
  ttfont_to_ufo()
  write_glif()
  reverse_glif_contours()
  prepare_build_project()
  build_variable_font_from_ufo()
```

## Acceptance criteria
The implementation is acceptable if:

1. Running VF -> UFO creates a valid output directory with UFO masters and a designspace.
2. Running UFO -> VF invokes `fontmake` and writes a variable `.ttf`.
3. Invalid inputs produce readable errors.
4. The generated UFOs can be opened by at least one UFO editor.
5. The code is written as one standalone Python file named `varwideufo.py`.
6. 若重建後字型僅在原始 glyph 集合後附加新 glyph，且原始 cmap 對應維持不變，則仍應保留原始來源字型中的相容資料表。
7. 單純新增 `uni030D` 等新 glyph，不應自動導致 `GDEF`、`GPOS`、`GSUB` 保留流程被跳過。
8. 若保留流程被跳過，輸出的 warning 必須可說明具體原因。
9. `UFO -> TTF` roundtrip 後，原始 glyph 的 contour direction 語意必須與來源字型一致，不可系統性翻轉。
10. 若來源字型原本含有 `fvar` named instances 與 `STAT` axis values，重建後不可掉成 0。
11. `OS/2.fsSelection` 不可因重建而退化成導致樣式連結異常的狀態。
12. 最終字型在 Word 中按粗體時，`Light` 不可出現筆畫錯誤，且 `Medium` / `SemiBold` 不可完全沒有粗體變化。
