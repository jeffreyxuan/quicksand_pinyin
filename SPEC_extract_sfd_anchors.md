# SPEC_extract_sfd_anchors

## 目標
- 新增 `src\py\extract_sfd_anchors.py`。
- 從 FontForge 可開啟的 `*.sfd` 檔擷取 glyph anchors。
- 讓使用者可先在 FontForge UI 調整 anchor，再匯出成 JSON 給 `fonttool_fix_cmap.py` 套用。

## CLI
- `-input`：來源 `*.sfd`
- `-output`：輸出 `*.json`

## 輸入規則
- `-input` 必須是存在的 `*.sfd`
- `-output` 必須是 `*.json`

## 輸出格式
- JSON 以 UTF-8 儲存。
- root 為 object，至少包含：
  - `glyph_anchors`
  - `glyph_mark_anchors`
- 格式範例：
```json
{
  "glyph_anchors": {
    "I": {
      "anchor0": {"x": 121, "y": 700},
      "anchor2": {"x": 121, "y": 0}
    }
  },
  "glyph_mark_anchors": {
    "uni030D": {
      "_anchor0": {"x": 20, "y": 0}
    }
  }
}
```

## function：extract_sfd_anchors
- 實作位置：`src\py\extract_sfd_anchors.py`
- 輸入：`input_sfd: Path`, `output_json: Path`
- 輸出：寫出 anchor JSON
- 行為：
  - 使用 FontForge 開啟 SFD
  - 讀取各 glyph 的 anchor points
  - 匯出 base / basemark / ligature anchors 到 `glyph_anchors`
  - 匯出 mark anchors 到 `glyph_mark_anchors`
  - `Anchor-0` 需正規化成 `anchor0`
  - FontForge 的 stderr 輸出時，每一行前面需加 8 個空白，方便和主流程日誌區隔

## Variable anchor master 用途
- `src\ufo\anchor\ToneOZ-Quicksnow-W300_anchor.sfd` 與 `src\ufo\anchor\ToneOZ-Quicksnow-W700_anchor.sfd` 可作為 variable font 的 anchor masters。
- 這兩份檔案的 anchor 匯出結果，不應直接合併成單一固定座標後再 patch 到最終 variable TTF。
- 正確用途是：
  - `W300_anchor.sfd` 匯出 `W300` anchor 資料
  - `W700_anchor.sfd` 匯出 `W700` anchor 資料
  - 後續由 master 階段寫回對應 UFO，再交給 variable font build 流程內插
- 單一 `src\ufo\anchor\ToneOZ-Quicksnow_anchor.sfd` 僅適用於固定 anchor patch 的舊流程。

## 錯誤處理
- `-input` 不存在
- `-input` 非 `*.sfd`
- `-output` 非 `*.json`
- 找不到 `fontforge.exe`
- FontForge 無法開啟 SFD

## 驗收條件
1. 可從 `ToneOZ-Quicksnow_anchor.sfd` 匯出 anchor JSON。  
   - 預設來源位置可為 `src\ufo\anchor\ToneOZ-Quicksnow_anchor.sfd`。  
2. JSON 需包含 glyph 名稱與對應 anchor 座標。  
3. 需區分輸出 base 類 anchors 與 mark anchors，不輸出無關資料。  
4. `ufo_merge.bat` 可先自動呼叫本工具更新 `fonttool_fix_anchor_rules.json`。  
5. 若 FontForge 有 stderr 訊息，輸出時每行前面需有 8 個空白。  
6. 若用於 variable font anchor workflow，必須可分別匯出 `W300` 與 `W700` 的 anchor 資料，供後續 master 階段使用。  
