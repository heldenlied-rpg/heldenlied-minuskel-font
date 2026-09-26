# Tests

```
python tests/run_tests.py                  # Prüfung + alle Testdokumente
python tests/run_tests.py --no-pdf         # ohne LaTeX
python tests/run_tests.py --engine lualatex
python scripts/build.py --tests            # bauen und danach testen
```

## Was passiert

1. **Glyphenprüfung:** Jeder Eintrag in `EXPECTED` (`testcases.py`) wird
   mit HarfBuzz gesetzt und mit der erwarteten Glyphenfolge verglichen.
   Benötigt `uharfbuzz` (`pip install uharfbuzz`). Bei Fehlern endet das
   Skript mit Exit-Code 1, Details in `output/shaping-report.txt`.
2. **Testdokumente** in `output/` (nicht im Repo):
   - `test.html`: Webfont eingebettet, daher unabhängig von installierten
     Schriften. Oben ein interaktiver Bereich mit Feature-Schaltern,
     darunter alle Kombinationen aus `COMBOS`.
   - `test.fodt`: LibreOffice Writer. Nutzt die **installierte** Schrift,
     Features über den Schriftnamen (`Heldenlied Minuskel:hist&ss01`).
     Vorher alte Version deinstallieren, neue installieren, LibreOffice
     komplett neu starten.
   - `test.tex` / `test.pdf`: fontspec mit dem gebauten OTF (keine
     Installation nötig). Standard-Engine ist XeLaTeX.

## Pflege

Neue Texte, Kombinationen oder erwartete Ergebnisse nur in
`testcases.py` eintragen; alle Dokumente werden daraus erzeugt.
