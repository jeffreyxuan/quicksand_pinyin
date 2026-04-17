<div lang="zh-CN">
  
# 澳声通 快雪拼音楷体字体-简体版 ToneOZ QuickSnow Pinyin Kai Simplified

![toneoz-quicksnow-simplified](https://github.com/user-attachments/assets/05d54b75-bdbb-45f8-af68-3d4a9fe63dd7)

---

## 您的支持

如果澳声通对您有帮助，欢迎您用自己的话撰写推荐文章，发布到公开网站、博客、社交平台、论坛、期刊、电子报等，任何语言都可以。

真实用户写下的文字，是对创作最好的回馈。

---

## 鼓励或建议

作者 : Jeffrey Xuan
- Email: [jeffreyx@gmail.com](mailto:jeffreyx@gmail.com)
- WeChat: [chihlinhsuan](https://weixin.qq.com/)
- LINE: [jeffreyxiphone2018](https://line.me/)
- 

## 简介

结合汉语拼音与教育部标准楷体，采用圆体大字澳声通「[Quicksnow 快雪时晴](https://github.com/jeffreyxuan/toneoz-font-quicksnow)」英数字拼音字体，致力于呈现接近高品质教材级别的阅读体验。

---

## 字体下载

  [https://toneoz.com/blog/quicksnow](https://toneoz.com/blog/quicksnow)

---

## 汉字配拼音字体在线展示：  
  请在字体菜单中选择「快雪」系列：  
  [https://toneoz.com/ime](https://toneoz.com/ime)

---

## 特色

- 免费、开源、可商用。采用 **OFL（Open Font License）** 授权发布，可放心使用，无需额外付费。
- 字形风格接近课本用字，符合教育规范笔形
- 汉字上方的拼音部分采用动态字宽排版，更符合英文阅读习惯
- 小字号下仍保持较高辨识度
- 笔画清晰，易于区分
- 拼音字体与正文在功能上做出明确区隔
- 支持多音字一字多音
- 兼容 [IVS 字嗨注音规范](https://github.com/ButTaiwan/bpmfvs)，切换字体时读音不会错位

## 拼音／注音编辑器

提供免费、免安装的 **拼音注音编辑器**，支持多音字自动校正：

[https://toneoz.com/ime](https://toneoz.com/ime)

编辑器也可配合教学方案，切换普通话与国语的两岸差异读音，方便教师根据不同教学场景灵活使用。

---

## 开源协作说明：如何更新 `sources/reference_tables/*.json`

本项目中的 `sources/reference_tables/*.json` 是可读的 OpenType table snapshot，用来在 build 阶段补回 UFO 与 `fontmake` 目前无法稳定重建的 table，例如 `GDEF`、`GSUB`、`cmap`、`gasp`、`prep`、`name`。

这些 `.json` 文件是受版本控制的文字资料，可以直接用记事本打开、审查 diff、讨论变更，也可以在理解字段意义的前提下直接编辑。

如果你修改了 UFO 结构，或需要同步新的相容性 table，建议先在 `deploy_quicksnow` 工程中更新生成逻辑，再重新执行对应字型的 deploy，让工具重新生成 `sources/reference_tables/manifest.json` 与各个 `*.json`。

建议流程：

1. 在 `deploy_quicksnow` 工程中确认 `config/config_deploy_gitrepo_quicksnow.json` 指向正确的参考 TTF。
2. 运行 `python3 deploy_gitrepo_quicksnow.py --ttf ToneOZQSPinyinKaiSimplified.ttf` 重新生成本 repo 的 `sources/` 内容。
3. 回到本 repo 运行 `build.bat`，确认新的 TTF 可成功产出。
4. 用 `sources/validate_build.py` 或直接运行 `build.bat` 内建验证，确认 glyph count、cmap size 与必要 tables 仍符合预期。

若你真的需要变更某个 table 的生成逻辑，请优先修改生成工具与文档，再重新导出 `.json`，不要只提交孤立的快照变更。

---

## 汉字上方的拼音：澳声通「[Quicksnow 快雪时晴](https://github.com/jeffreyxuan/toneoz-font-quicksnow)」英数字拼音字体

通过拼音学习中文，罗马字拼音非常重要。因为正文通常使用宋体或黑体，出版时常会另外采用更易辨认的圆体来标注拼音，让读者一眼就能看出那是发音信息。

这类字体通常会尽量做到清晰、简洁、易认，同时也要支持各类语言教学所需的拼音符号。

为了辅助教材制作，澳声通 ToneOZ 特别开发并推出「[Quicksnow 快雪时晴](https://github.com/jeffreyxuan/toneoz-font-quicksnow)」系列拼音字体。

<img width="1920" height="1080" alt="toneoz-quicksnow-logo03" src="https://github.com/user-attachments/assets/82a7e30e-cb73-4d3e-b212-c8cb93c68294" />

<img width="1920" height="1080" alt="toneoz-quicksnow-logo02" src="https://github.com/user-attachments/assets/e2a650da-50c8-494c-83ab-a0eb6cf68170" />

澳声通 [快雪时晴 QuickSnow](https://github.com/jeffreyxuan/toneoz-font-quicksnow) 英数字体，是基于 Google Fonts 的开源字体 [Quicksand](https://fonts.google.com/specimen/Quicksand?preview.script=Latn) 改造而来。

Quicksand 这套字体最早由菲律宾裔、旅居迪拜的设计师 Andrew Paglinawan 于 2008 年发起；2016 年由爱尔兰／埃及裔设计师 Thomas Jockin 进一步提升字体质量；2019 年则由旅居纽约的南斯拉夫裔设计师 Mirko Velimirovic 制作了可变字重版本。

在这样一个跨国团队的持续接力下，Quicksand 原本就对西欧、南欧拉丁字母以及越南语有较好的支持。

---

## 母字体

- 繁体拼音汉字免费商用授权来自 : 全字库正楷体  
  [《Open Government Data License, version 1.0》](https://data.gov.tw/en/licenses)
- 简体免费商用授权来自 : 文鼎PL简中楷  
  [《ARPHIC PUBLIC LICENSE 1999》](http://ftp.gnu.org/non-gnu/chinese-fonts-truetype/LICENSE)
- 正文汉字中的英数字符部分基于「[FONTWORKS Klee One](https://github.com/fontworks-fonts/Klee)」以及「[LXGW 霞鹜文楷](https://github.com/lxgw/LxgwWenKai)」，采用 SIL Open Font License 1.1 免费商用授权。

</div>
