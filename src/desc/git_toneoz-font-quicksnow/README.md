# ToneOZ QuickSnow

**ToneOZ QuickSnow** is a free and open-source font family created by [ToneOZ.com](https://toneoz.com), released under the **SIL Open Font License**.

<img width="1920" height="1080" alt="toneoz-quicksnow-logo01" src="https://github.com/user-attachments/assets/7a8181f0-721a-42c1-8139-dfe57988eed4" />


Phonetic typefaces that deliver a textbook-quality reading experience and support a wide range of educational romanized phonetic annotation characters.

---

## Demo

Quicksnow web font live demo:

[https://toneoz.com/demo_quicksnow/](https://toneoz.com/demo_quicksnow/)

---

## Download Fonts

[https://toneoz.com/blog/quicksnow](https://toneoz.com/blog/quicksnow)

---
## Your support

If ToneOZ has been useful to you, please consider sharing your experience in your own words on any website, blog, social media, forum, newsletter, or magazine. Any language is welcome. Honest feedback from real users means a great deal to the creator.

---
## Contact 

- Author: Jeffrey Xuan [jeffreyx@gmail.com](mailto:jeffreyx@gmail.com)
- Facebook group: [曉聲通國語字典](https://www.facebook.com/groups/apptoneoz)
- WeChat: [chihlinhsuan](https://weixin.qq.com/)
- LINE: [jeffreyxiphone2018](https://line.me/)

---
## Overview

The **QuickSnow** series is designed for a wide range of educational use cases, especially phonetic annotation in teaching materials.

<img width="1920" height="1080" alt="toneoz-quicksnow-logo02" src="https://github.com/user-attachments/assets/af612059-6491-4690-9d4e-abd5def87fa5" />


Fonts in the family include:

- [x] **ToneOZ-Quicksnow** — half-width Latin letters and numerals
- [x] **ToneOZ QuickSnow Phonetic Kai Traditional Chinese**
- [x] **ToneOZ QuickSnow Phonetic Kai Simplified Chinese**

---

## How to build

1. Make sure `python3` is available in your environment.
2. Run `build.bat`.

---

## Open Source Collaboration: how to update `sources/reference_tables/*.json`

The files under `sources/reference_tables/*.json` are readable OpenType table snapshots. They are used during the build to restore tables that UFO plus `fontmake` do not always reproduce reliably, such as `GDEF`, `GSUB`, `cmap`, `gasp`, `prep`, and `name`.

These `.json` files are version-controlled text. They can be opened in a basic text editor, reviewed in diffs, discussed in pull requests, and edited directly by contributors who understand the field meanings.

If you change the UFO structure or need to refresh compatibility tables, update the generator in `deploy_quicksnow`, then rerun the matching deploy task so the tool regenerates `sources/reference_tables/manifest.json` and the corresponding `*.json` files.

Recommended workflow:

1. In the `deploy_quicksnow` project, confirm that `config/config_deploy_gitrepo_quicksnow.json` points to the correct reference TTF.
2. Run the matching deploy command, for example `python3 deploy_gitrepo_quicksnow.py --ttf ToneOZ-Quicksnow.ttf`.
3. Return to this repo and run `build.bat` to regenerate the output font.
4. Use `sources/validate_build.py`, or simply rely on the built-in validation inside `build.bat`, to confirm that glyph count, cmap size, and required tables still match expectations.

If the actual table-generation strategy needs to change, update the generator and documentation first, then regenerate the `.json` files instead of committing an isolated snapshot edit.

---

## Designed for Education

The phonetic Kai fonts for Traditional and Simplified Chinese combine Quicksnow with education-oriented standard Kai typefaces. They support multiple pronunciations for a single character through the widely used IVS-based phonetic annotation specification (字嗨注音 IVS), and are designed for practical classroom use.

<img width="1920" height="1080" alt="toneoz-quicksnow-logo03" src="https://github.com/user-attachments/assets/49892292-e38f-4b59-b7ec-f5b61e8b9309" />

![toneoz-quicksnow-logo04](https://github.com/user-attachments/assets/ae4acb89-6d00-421c-acd3-19dee2cd2375)

---

## Phonetic editor

The QuickSnow family also works together with the free online phonetic editor:

**ToneOZ IME**  
https://toneoz.com/ime

Features of the editor include:

- automatic correction of polyphonic heteronyms characters
- support for both **Pǔtōnghuà (<span lang="zh">普通话</span> Common Tongue)** and **Guóyǔ (國語 National Language)**
- no installation required

---

## Free and Open Source

- [x] Derived from the open-source Google font **Quicksand**
- [x] Partly mixed with **Noto Sans**
- [x] Free to use, including commercial use
- [x] Released under the **SIL Open Font License**

---

## Key Features

ToneOZ proudly presents the **QuickSnow** phonetic font series.

### Visual and educational design

- [x] Designed to feel familiar in educational materials — “like a real textbook”
- [x] Rounded stroke endings for a softer and clearer appearance
- [x] Enlarged glyph area for better visibility
- [x] Clear stroke shapes for easy recognition
- [x] Strong visual separation from body text, so learners can immediately identify phonetic information
- [x] East Asian phonetic-teaching oriented letterforms
- [x] High legibility even at small sizes

### Font technology

- [x] Supports **five static weights** : 300 Light, 400 Regular, 500 Medium, 600 Semi-bold, 700 Bold.
- [x] Supports **SIL 1.8 variable weight**, allows smooth and flexible weight adjustment
- [x] For the Kai version : Uses dynamic-width layout for phonetic text above Chinese characters, providing a more natural reading experience for Latin-based phonetic annotation

---

## Why This Font Was Made

Phonetic symbols are widely used to indicate pronunciation in educational materials.  
In many textbooks and learning resources, the body text is often set in serif or traditional sans-serif styles. For phonetic annotation, however, publishers often prefer a **rounded style** to visually distinguish pronunciation from the main text.

This distinction helps readers immediately understand that the phonetic text is supplementary pronunciation information, not body content.

At the same time, phonetic fonts for education should:

- emphasize handwritten-style educational letterforms
- avoid overly sharp, decorative, or high-contrast details
- remain simple, clear, and easy to recognize
- support all characters required by teaching standards

A well-known reference in this design direction is the Japanese **Morisawa UD textbook font** series.

For general use, phonetic fonts must also support the full set of characters used in **Mandarin**, **Hokkien**, and **Hakka** phonetic systems.

As of 2026, access to rounded educational phonetic fonts that meet these requirements is still limited. Commercial publishers may commission custom typefaces, but smaller educational teams and independent creators often face significant difficulty when creating phonetic educational materials.

**ToneOZ QuickSnow** was created to help the above situations.

---

## Background

ToneOZ QuickSnow is adapted from **Quicksand**, an open-source typeface originally initiated in 2008 by Dubai-based Filipino designer **Andrew Paglinawan**.

It was later improved in 2016 by Irish-Egyptian designer **Thomas Jockin**, and a variable-weight version was produced in 2019 by New York-based Yugoslav designer **Mirko Velimirovic**.

Thanks to this diverse development history, Quicksand offers strong support for Western and Southern European Latin scripts as well as Vietnamese.

The main focus of the **ToneOZ QuickSnow** adaptation is:

- expanding support for Mandarin, Hokkien, and Hakka phonetic characters
- adjusting letterforms for classroom teaching needs
- improving suitability for educational phonetic annotation

---

## License

This project is released under the **SIL Open Font License**.

---

## Website

Learn more at:  
https://toneoz.com

### Character support

- [x] Supports special characters used in educational phonetic systems
- [x] Includes tone marks and related phonetic symbols
- [x] Expanded support for Mandarin, Hokkien, and Hakka phonetic notation

漢語拼音

āáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜêê̄ếê̌ềm̄ḿm̌m̀n̄ńňǹ
ĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙÜǕǗǙǛÊÊ̄ẾÊ̌ỀM̄ḾM̌M̀N̄ŃŇǸ

台語組合

◌́◌̀◌̂◌̌◌̄◌̍◌̋◌̆◌͘
a̍a̋e̍e̋i̍i̋o̍u̍m̀m̂m̌m̄m̍m̋m̆n̂n̄n̍n̋n̆
A̍A̋E̍E̋I̍I̋O̍U̍M̀M̂M̌M̄M̍M̋M̆N̂N̄N̍N̋N̆

台語預組

áàǎâāăéèêěēĕíìîǐīĭóòôǒōőŏúùûǔūűŭḿńǹňⁿ
ÁÀÂǍĀĂÉÈÊĚĒĔÍÌÎǏĪĬÓÒÔǑŌŐŎÚÙÛǓŪŰŬḾŃǸŇᴺ

三種順序

o͘ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘
O͘Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘

ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘
Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘

ó͘ò͘ô͘ǒ͘ō͘o̍͘ŏ͘ő͘
Ó͘Ò͘Ô͘Ǒ͘Ō͘O̍͘Ŏ͘Ő͘
