#!/usr/bin/env python3
"""
Build-Skript für Heldenlied Minuskel.

Baut aus der UFO-Quelle OTF, TTF und WOFF2, bereinigt die Dateien und
prüft sie optional mit Fontbakery.

Aufruf aus dem Repo-Stammordner:
    python scripts/build.py           # bauen
    python scripts/build.py --check   # bauen und mit Fontbakery prüfen
    python scripts/build.py --tests   # bauen und tests/run_tests.py ausführen
    python scripts/build.py --release # bauen und ZIPs für ein GitHub-Release erstellen
"""
import argparse
import re
import zipfile
import shutil
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sources" / "HeldenliedMinuskel-Regular.ufo"
FONTS = ROOT / "fonts"
NAME = "HeldenliedMinuskel-Regular"

OTF = FONTS / "otf" / f"{NAME}.otf"
TTF = FONTS / "ttf" / f"{NAME}.ttf"
WOFF2 = FONTS / "webfonts" / f"{NAME}.woff2"
RELEASE = ROOT / "release"
FAMILY = "Heldenlied Minuskel"
# Dateien, die jedem Release-ZIP beiliegen (die OFL verlangt die Lizenz)
RELEASE_DOCS = ["OFL.txt", "FONTLOG.txt", "README.md"]


def run(cmd):
    print(">", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True)


def clean():
    for sub in ("otf", "ttf", "webfonts"):
        d = FONTS / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


def compile_fonts():
    # fontmake über "python -m" aufrufen, damit PATH keine Rolle spielt
    base = [sys.executable, "-m", "fontmake", "-u", SOURCE]
    run(base + ["-o", "otf", "--output-path", OTF])
    run(base + ["-o", "ttf", "--output-path", TTF])


def postprocess(path):
    """Bereinigung nach dem Build (früher scripts/postexport.py)."""
    f = TTFont(path)
    f["name"].removeNames(platformID=1)      # Mac-Namenseinträge entfernen
    f["OS/2"].recalcAvgCharWidth(f)          # xAvgCharWidth neu berechnen
    for t in ("DSIG", "FFTM"):               # Altlasten entfernen
        if t in f:
            del f[t]
    if "glyf" in f:
        fix_unhinted(f)
    f.save(path)


def fix_unhinted(f):
    """Ungehintete TTF: Smart Dropout Control aktivieren (wie gftools fix-nonhinting)."""
    from fontTools.ttLib import newTable
    from fontTools.ttLib.tables import ttProgram
    prep = newTable("prep")
    prep.program = ttProgram.Program()
    prep.program.fromAssembly(["PUSHW[]", "511", "SCANCTRL[]", "PUSHB[]", "4", "SCANTYPE[]"])
    f["prep"] = prep
    gasp = newTable("gasp")
    gasp.gaspRange = {0xFFFF: 0x000F}
    f["gasp"] = gasp
    f["maxp"].maxStackElements = max(f["maxp"].maxStackElements, 2)


def make_woff2():
    f = TTFont(TTF)
    f.flavor = "woff2"                       # benötigt das Paket "brotli"
    f.save(WOFF2)


def check():
    """Fontbakery je Datei einzeln aufrufen (sonst gelten OTF und TTF als eine Familie)."""
    exe = shutil.which("fontbakery")
    cmd = [exe] if exe else [sys.executable, "-m", "fontbakery"]
    failed = []
    for font in (OTF, TTF):
        report = FONTS / f"fontbakery-report-{font.suffix[1:]}.md"
        print(f"\n=== Fontbakery: {font.name} ===")
        r = subprocess.run([str(c) for c in cmd + ["check-universal", "--ghmarkdown", report, font]])
        if r.returncode != 0:
            failed.append(font.name)
        print(f"Bericht: {report.relative_to(ROOT)}")
    if failed:
        print("\nFontbakery meldet FAIL/FATAL für: " + ", ".join(failed))
    else:
        print("\nFontbakery: keine FAILs")
    return not failed


def font_version():
    """Version aus dem gebauten Font im Format des Git-Tags.

    Die Font-Version M.NPP wird zu M.N.P (wie das Tag vM.N.P):
    0.400 -> 0.4.0, 0.401 -> 0.4.1, 0.410 -> 0.4.10, 1.000 -> 1.0.0
    """
    name = TTFont(OTF)["name"].getDebugName(5) or ""
    m = re.search(r"(\d+)\.(\d)(\d\d)", name)
    if not m:
        return "unbekannt"
    major, minor, patch = m.groups()
    return f"{int(major)}.{int(minor)}.{int(patch)}"


def webfont_css():
    return f"""/* {FAMILY} – Einbindung als Webfont */
@font-face {{
  font-family: "{FAMILY}";
  src: url("{WOFF2.name}") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}

/* Beispiele:
   .modern     {{ font-family: "{FAMILY}"; }}
   .historisch {{ font-family: "{FAMILY}"; font-feature-settings: "hist" 1; }}
   .roemisch   {{ font-family: "{FAMILY}"; font-feature-settings: "ss05" 1; }}
*/
"""


def make_release():
    """Je Font-Format ein ZIP mit Font, Lizenz und Dokumentation."""
    version = font_version()
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir()
    base = NAME.split("-")[0]
    for label, font, extra in (("OTF", OTF, {}), ("TTF", TTF, {}),
                               ("Webfont", WOFF2, {f"{base}.css": webfont_css()})):
        folder = f"{base}-{version}-{label}"
        target = RELEASE / f"{folder}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(font, f"{folder}/{font.name}")
            for doc in RELEASE_DOCS:
                if (ROOT / doc).exists():
                    z.write(ROOT / doc, f"{folder}/{doc}")
            for name, text in extra.items():
                z.writestr(f"{folder}/{name}", text)
        print(f"  {target.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="nach dem Build mit Fontbakery prüfen")
    parser.add_argument("--tests", action="store_true",
                        help="nach dem Build die Tests in tests/ ausführen")
    parser.add_argument("--release", action="store_true",
                        help="ZIPs je Font-Format für ein GitHub-Release erstellen")
    args = parser.parse_args()

    if not SOURCE.exists():
        sys.exit(f"Quelle nicht gefunden: {SOURCE}")

    clean()
    compile_fonts()
    for p in (OTF, TTF):
        postprocess(p)
    make_woff2()
    print("\nFertig:")
    for p in (OTF, TTF, WOFF2):
        print(f"  {p.relative_to(ROOT)}")

    ok = True
    if args.check:
        ok = check() and ok
    if args.tests:
        ok = subprocess.run([sys.executable, str(ROOT / "tests" / "run_tests.py")]).returncode == 0 and ok
    if args.release:
        if ok:
            print(f"\nRelease-ZIPs (Version {font_version()}):")
            make_release()
        else:
            print("\nRelease-ZIPs nicht erstellt, da Prüfung oder Tests fehlgeschlagen sind.")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
