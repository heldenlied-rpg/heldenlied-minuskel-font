## Heldenlied Minuskel 0.5.0

**Complete Google Fonts Latin Core character set, new spacing and first
kerning.** The font now covers most Western, Central and Northern European
languages.

### Highlights
- Character set: complete GF Latin Core, with accented letters built as
  composites, plus ø, ð, ł, đ, ħ and þ/Þ
- New symbols and punctuation: @ # % & * § ¶ © ® ™ °, € £ ¢ ¥ $,
  math signs, brackets, braces, guillemets, ellipsis, bullet, dotted cross
  and reference mark
- `locl`: Catalan punt volat (l·l) and Turkish/Azerbaijani/Crimean Tatar
  dotted and dotless i
- `ccmp`: dotless i and j before accents above (e.g. Dutch íj́);
  apostrophe-style caron for ď ľ Ľ ť
- `mark`: combining accents above and below letters, including stacked
  accents
- Respaced all letters, keeping the tight letter spacing
- `kern`: first class-based kerning for letters and punctuation
  (about 1,360 pairs)

### Upgrading from 0.4
- Because of the new spacing and kerning, line lengths in existing
  documents will change.
- Glyph names now follow Fontra's naming (e.g. `macroncomb`, `idotless`).
  This only matters if you reference glyph names directly.

### Downloads
- **OTF**: desktop applications and LaTeX
- **TTF**: alternative for applications with OTF issues
- **Webfont**: WOFF2 with a ready-made CSS file

Known limitations: capitals still show lowercase forms, unhinted.
Full changelog: FONTLOG.txt
