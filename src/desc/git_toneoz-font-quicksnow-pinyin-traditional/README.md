# 澳聲通 快雪拼音體 ToneOZ QuickSnow

實現教科書般的閱讀體驗，涵蓋多種教學用羅馬拼音字符，點亮學習熱情的拼音字體。

---

## 字型下載
  https://toneoz.com/blog/download-quicksnow

## 英數字體 QuickSnow 線上展示：  
  https://toneoz.com/demo_quicksnow/

## 漢字配拼音字體線上展示：  
  請在字型選單中選「快雪」系列：  
  https://toneoz.com/imez

---

## 製作動機

標音符號常用來顯示發音。由於正文往往含有英數字母，並搭配巴洛克襯線體（明體）或古典人文無襯線體（黑體），許多出版品會選用「圓體字」作為標音字體。這樣在視覺上能與正文有所區別，提示讀者這是發音資訊。

同時，這類字體會強調書寫筆形，排除高對比、尖角與過度裝飾性的特徵，使整體結構更清楚、單純且易於辨識。日本森澤 UD 教科書系列字體便是著名例子。

配合教學現場，拼音字體還需要支援教育規格中的各類漢語、閩南語、客語拼音字符。

符合以上需求的圓體拼音字型，截至 2026 年為止，取得途徑仍相當有限。商業出版社可選擇付費客製化字體，而其他小型團隊在製作拼音書籍時則常面臨挑戰。

為了輔助教材製作，澳聲通 ToneOZ 謹呈「快雪時晴」系列拼音字體。

---

## 設計與來源規劃

- 設計精神參考森澤日本教科書 **UD学参丸ゴシック**
- 架構及字符規劃參考字嗨開源字體 **Lesson One**
- 主要母字符來自 Andrew Paglinawan 於 2008 年設計的開源字體 **Quicksand**
- 部分音標字符由 **Google Fonts Noto Sans** 修改而來
- 繁體拼音漢字來自 **教育部全字庫楷體**
- 簡體拼音漢字來自教育標準 1999 公眾授權字體 **文鼎 PL 簡中楷**

---

## 字型內容

快雪時晴系列包含以下字體：

- `ToneOZ-Quicksnow` 英數字型
- `澳聲通快雪拼音楷體-繁`
- `澳声通快雪拼音楷体-简`
- （規劃中）提供傳統破音拆分多檔案版本，適用於 WPS 及舊版 Office

繁簡拼音楷體均為教育規格標準楷體，支援破音字一字多音（字嗨注音 IVS 通用規格），並配備免安裝、免費的線上拼音注音編輯器：

https://toneoz.com/imez

此工具可自動校正破音字，支援國語及普通話兩岸差異音的偵測與切換。

---

## 開源協作說明：如何更新 `sources/reference_tables/*.json`

本專案中的 `sources/reference_tables/*.json` 是可讀的 OpenType table snapshot，用來在 build 階段補回 UFO 與 `fontmake` 目前無法穩定重建的 table，例如 `GDEF`、`GSUB`、`cmap`、`gasp`、`prep`、`name`。

這些 `.json` 檔案是受版本控制的文字資料，可以直接用記事本打開、審查 diff、討論變更，也可以在理解欄位意義的前提下直接編輯。

如果你修改了 UFO 結構，或需要同步新的相容性 table，建議先在 `deploy_quicksnow` 專案中更新生成邏輯，再重新執行對應字型的 deploy，讓工具重新生成 `sources/reference_tables/manifest.json` 與各個 `*.json`。

建議流程：

1. 在 `deploy_quicksnow` 專案中確認 `config/config_deploy_gitrepo_quicksnow.json` 指向正確的參考 TTF。
2. 執行 `python3 deploy_gitrepo_quicksnow.py --ttf ToneOZQSPinyinKaiTraditional.ttf` 重新生成本 repo 的 `sources/` 內容。
3. 回到本 repo 執行 `build.bat`，確認新的 TTF 可成功產出。
4. 用 `sources/validate_build.py` 或直接執行 `build.bat` 內建驗證，確認 glyph count、cmap size 與必要 tables 仍符合預期。

若你真的需要調整某個 table 的生成邏輯，請優先修改生成工具與文件，再重新導出 `.json`，不要只提交孤立的快照變更。

---

## 特色

- 免費、開源、可商用
- 「課本就長這樣」
- 圓體字（筆畫末端圓角處理）
- 擴大字面
- 筆畫易辨識
- 與正文做出功能區隔
- 東方拼音教學筆形
- 小尺寸時仍維持高識別度
- 支援各教學方案中使用到的特殊字符，包含聲調記號
- 英數字體版支援五種粗細靜態字重
- 支援 SIL 1.8 Variable Weight，提供無限段粗細動態字重
- 漢字上方拼音部分使用動態字寬排版，符合英語閱讀體驗

---

## 關於母字體 Quicksand

澳聲通快雪時晴 QuickSnow 改作自 Google Fonts 開源字體 **Quicksand**。

- 2008 年由杜拜的菲律賓設計師 **Andrew Paglinawan** 發起開源計劃
- 2016 年由愛爾蘭埃及裔設計師 **Thomas Jockin** 改進品質
- 2019 年由紐約南斯拉夫裔設計師 **Mirko Velimirovic** 製作可變字重版本

在多元團隊的發展下，Quicksand 對西歐、南歐拉丁字母及越南文有良好支援。澳聲通快雪時晴系列的改作重點，則是增補漢語、閩南語、客語拼音字符，並配合課堂教學需求調整筆形。

---

## 改作重點

- 印刷改手寫：`a` 改為單層
- 裝飾性筆畫復原：`y` 去掉圓弧，`Q` 去掉波浪腳
- 伸頭伸腳：`u` 長尾巴，`I`、`J` 補上工字型頭角
- 數學幾何修正：修正 `P B H X x` 在 Windows 作業系統下的筆畫粗細表現
- 字距調整 Kerning Adjustment
- 錨點調整 Anchor Adjustment
- 補齊教學所需的完整字符集

---

## 支援字符

### 漢語拼音

```text
āáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜêê̄ếê̌ềm̄ḿm̌m̀n̄ńňǹ
ĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙÜǕǗǙǛÊÊ̄ẾÊ̌ỀM̄ḾM̌M̀N̄ŃŇǸ
```

### 台語組合

```text
◌́◌̀◌̂◌̌◌̄◌̍◌̋◌̆◌͘
a̍a̋e̍e̋i̍i̋o̍u̍m̀m̂m̌m̄m̍m̋m̆n̂n̄n̍n̋n̆
A̍A̋E̍E̋I̍I̋O̍U̍M̀M̂M̌M̄M̍M̋M̆N̂N̄N̍N̋N̆
```

### 台語預組

```text
áàǎâāăéèêěēĕíìîǐīĭóòôǒōőŏúùûǔūűŭḿńǹňⁿ
ÁÀÂǍĀĂÉÈÊĚĒĔÍÌÎǏĪĬÓÒÔǑŌŐŎÚÙÛǓŪŰŬḾŃǸŇᴺ
```

### 三種順序

```text
o͘ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘
O͘Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘

ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘
Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘

ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘
Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘
```

---

## 您的支持

如果澳聲通對您有幫助，歡迎用您自己的話語撰寫推薦文章，分享在任何網站：

- 部落格
- 社群平台
- 論壇
- 期刊
- 電子報
- 任何語言皆可

真人寫下的字句，是創作最好的回報。

---

## 鼓勵或建言

### 作者聯絡方式

- Email: `jeffreyx@gmail.com`
- Facebook 討論區：https://www.facebook.com/groups/apptoneoz
- WeChat: `chihlinhsuan`
- LINE: `jeffreyxiphone2018`
