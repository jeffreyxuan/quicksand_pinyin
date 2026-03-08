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










