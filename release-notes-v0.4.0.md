## Heldenlied Minuskel 0.4.0

**Modern letterforms are now the default.** The historical forms of the
Folchart Psalter moved to the OpenType feature `hist` (mirrored in `ss20`
for applications without `hist` support).

### Highlights
- `hist` / `ss20`: long s (ſ), ss as ß, u/uu/i forms for v/w/j, umlauts with
  superscript e, historical punctuation and numerals
- `ss05`: Roman numerals 1–3999 in minuscules, including years and dates
  (26.9.872 → ·xxui·uiiii·dccclxxii·)
- `ss07`: late medieval numerals
- `ss01`: tall ascenders now also for capitals, new f/ſ + l ligatures
- Titulus at a uniform height on all letters
- Source switched from FontForge to UFO, with build script and automated tests

### Upgrading from 0.3
- Documents that relied on the historical default need `hist` (or `ss20`).
- `ss06` no longer exists; its forms are now the default.
- Roman numerals now need `ss05`, `hist` or `ss20`.

### Downloads
- **OTF**: desktop applications and LaTeX
- **TTF**: alternative for applications with OTF issues
- **Webfont**: WOFF2 with a ready-made CSS file

Known limitations: capitals still show lowercase forms, no kerning yet.
Full changelog: FONTLOG.txt
