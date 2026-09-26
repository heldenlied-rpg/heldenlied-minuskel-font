# Heldenlied Minuskel

A Carolingian minuscule typeface inspired by and modelled on the Folchart Psalter
(St. Gallen, Stiftsbibliothek, Cod. Sang. 23, 9th century), created for
the tabletop RPG *Heldenlied – Das Schicksal der Helden*
(https://heldenlied-rpg.de).

Designed for display use: titles, logos, handouts and atmospheric text,
not body text.

![Specimen](documentation/images/Heldenlied-Minuskel-Sample.jpg)
<sub>Background: edited from St. Gallen, Stiftsbibliothek, Cod. Sang. 23, p. 215:
Folchart-Psalter (https://doi.org/10.5076/e-codices-csg-0023), licensed under
CC BY-NC 3.0. The specimen image is not covered by the OFL.</sub>

## Download

Ready-to-use fonts are attached to each
[release](https://github.com/heldenlied-rpg/heldenlied-minuskel-font/releases):
OTF for desktop applications and LaTeX, TTF as an alternative, and WOFF2
with a ready-made CSS file for websites.

## Status

Version 0.4. Changes are listed in [FONTLOG.txt](FONTLOG.txt).

Known limitations: capital letters still show lowercase forms (dedicated
capital sets are planned as `ss02`–`ss04`), there is no kerning yet, and
the fonts are unhinted.

### Upgrading from 0.3

- Modern letterforms are now the default. Documents that relied on the
  historical look need `hist` (or `ss20`).
- `ss06` no longer exists; its forms are now the default.
- Roman numerals are no longer converted automatically; they need `ss05`,
  `hist` or `ss20`.

## OpenType features

By default the font uses modern, readable letterforms. The historical
forms of the Folchart Psalter are available through `hist` (or its
mirror `ss20` for applications without `hist` support).

| Feature | Description |
|---------|-------------|
| `liga`  | Standard ligatures (t_i, t_u, t_t, f_f, f + umlaut), also after capital F and T |
| `calt`  | Shortened f crossbar before ascenders |
| `mark`  | Titulus (combining macron U+0304) positioned above letters |
| `ss01`  | Tall ascenders for b, d, h, k, l (also B, D, H, K, L), with f/ſ + l ligatures |
| `ss05`  | Roman numerals 1–3999 in minuscules, e.g. 12 → ·xii·, 872 → ·dccclxxii·. A period or comma after a number merges into the punctus, so dates become ·xxui·uiiii·dccclxxii· |
| `ss07`  | Late medieval numerals (5 and 7); takes precedence over Roman numerals in `ss05`, `hist` and `ss20` |
| `hist` / `ss20` | Historical forms: long s (ſ), ss as ß, u/uu/i forms for v/w/j, umlauts with superscript e, historical punctuation, Roman numerals 1–3999 and late medieval numerals for all other numbers |

`ss02`–`ss04` are reserved for Capitalis quadrata, Uncial and
Half-Uncial capitals. `ss06` (“Modern readability” up to 0.3) is no
longer used, as modern forms are now the default.

## Usage

LaTeX (XeLaTeX or LuaLaTeX with fontspec):

    \newfontfamily\minuskel{HeldenliedMinuskel-Regular.otf}
    {\minuskel Modern text}
    {\minuskel\addfontfeature{Style=Historic} Historical text}
    {\minuskel\addfontfeature{StylisticSet=5} Roman numerals: 2026}

CSS:

    font-family: "Heldenlied Minuskel";
    font-feature-settings: "hist" 1;              /* historical forms */
    font-feature-settings: "ss05" 1, "ss01" 1;    /* Roman numerals, tall ascenders */

LibreOffice: append the features to the font name, e.g.
`Heldenlied Minuskel:hist` or `Heldenlied Minuskel:ss05&ss01`.

Microsoft Word: *Font → Advanced → Stylistic sets* offers one set at a
time; use set 20 for the historical forms, as Word does not support `hist`.

## Source

Glyphs are drawn in Inkscape (`sources/svg/`). The font source is a UFO
(`sources/HeldenliedMinuskel-Regular.ufo`); all OpenType features are
maintained as plain text in its `features.fea`.

## Building

Requires Python 3. From the repository root:

    pip install -r requirements.txt
    python scripts/build.py

This writes OTF, TTF and WOFF2 to `fonts/`. Add `--check` to run
Fontbakery on the result, `--tests` to run the feature tests, or
`--release` to create one ZIP per font format (OTF, TTF, webfont) in
`release/` for attaching to a GitHub release.

## Testing

    python tests/run_tests.py

checks the expected glyph sequences with HarfBuzz and creates test
documents for all feature combinations in `tests/output/`: an HTML page
with the webfont embedded, a LibreOffice Writer file (uses the installed
font) and a LaTeX file built to PDF. Test texts and expected results are
maintained in `tests/testcases.py`.

## Development notes

All glyphs are drawn by hand with pen and ink, scanned and vectorised
by the designer. Design decisions and historical interpretation are
based on the designer's own study of the Folchart Psalter.

Claude (Anthropic) was used as an assistant during development: for
analysing font files, writing and debugging the OpenType features, the
build and test scripts, background research on historical letterforms,
and drafting documentation. Scripts written with Claude also made purely
technical changes to existing outlines (removing vectorisation artefacts,
assembling composite glyphs, a uniform scaling of the titulus stroke).
No glyph shapes were designed or drawn by AI.

## License
Copyright 2026 Richard Westebbe (https://github.com/heldenlied-rpg/heldenlied-minuskel-font), 
with Reserved Font Name "Heldenlied Minuskel".

This Font Software is licensed under the SIL Open Font License,
Version 1.1. See [OFL.txt](OFL.txt).

Historical source: Cod. Sang. 23 via e-codices (https://www.e-codices.ch).