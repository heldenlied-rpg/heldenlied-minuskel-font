#!/usr/bin/env python3
"""
Importiert neue Glyphen aus Inkscape-SVGs in die UFO-Quelle.

Die SVG-Vorlagen liegen in sources/svg/ (Seite 1000 x 1000, Grundlinie bei
y = 707, also 293 über dem unteren Seitenrand). Der Glyphenname ist der
Dateiname ohne ".svg"; weicht er ab, wird er mit Doppelpunkt angegeben.
Der Codepoint wird aus dem Glyphennamen abgeleitet: zuerst über die Namen,
die auch Fontra verwendet (guillemetleft, circumflexcomb, ...), danach über
AGL-Namen und uniXXXX. Bei eigenen Namen wird er als drittes Feld angegeben.

Aufruf aus dem Repo-Stammordner:
    python scripts/import_svg.py bar numbersign
    python scripts/import_svg.py circumflex:circumflexcomb       # SVG:Glyphenname
    python scripts/import_svg.py circumflex:dach:0302            # SVG:Glyphenname:Codepoint

Je Glyphe wird die Kontur auf die Grundlinie gesetzt, an die linke Kante
(x = 0) geschoben, auf ganze Einheiten gerundet und in der Pfadrichtung an
die vorhandenen Glyphen angeglichen. Die Dickte entspricht zunächst der Konturbreite; Vor- und
Nachbreite, Anker usw. folgen in Fontra. Vorhandene Glyphen werden nie
überschrieben.
"""
import argparse
import sys
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools import agl
from fontTools.misc.transform import Transform
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.roundingPen import RoundingPen
from fontTools.svgLib import SVGPath
from fontTools.ufoLib.glifLib import GlyphSet

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sources" / "HeldenliedMinuskel-Regular.ufo"
SVG_DIR = ROOT / "sources" / "svg"

VIEWBOX = "0 0 1000 1000"   # Seite der SVG-Vorlagen = 1000 UPM
BASELINE = 707              # y der Grundlinie im SVG (von oben gemessen)


class Glyph:
    """Minimaler Container für die Attribute einer .glif-Datei."""
    width = 0
    unicodes = ()


def check_svg(path):
    """Prüft, ob das SVG zur Vorlage passt; gibt eine Fehlermeldung oder None zurück."""
    root = ET.parse(path).getroot()
    if " ".join((root.get("viewBox") or "").replace(",", " ").split()) != VIEWBOX:
        return f'viewBox ist nicht "{VIEWBOX}"'
    for el in root.iter():
        if el.tag.endswith("}g") and el.get("transform"):
            return "Ebene/Gruppe hat ein transform-Attribut (in Inkscape Gruppierung aufheben)"
    return None


def read_contours(path):
    """Liest alle Pfade und gibt sie als Liste geschlossener Konturen zurück."""
    def draw(dx):
        # SVG: y nach unten; Font: y nach oben, Grundlinie auf y = 0
        rec = RecordingPen()
        transform = Transform().translate(dx, 0).scale(1, -1).translate(0, -BASELINE)
        SVGPath(str(path), transform=transform).draw(RoundingPen(rec))
        return rec

    bounds = BoundsPen(None)
    draw(0).replay(bounds)
    if bounds.bounds is None:
        return []
    contours, current = [], []
    for op, args in draw(-bounds.bounds[0]).value:   # linke Kante auf x = 0
        if op == "endPath":                          # offene Pfade schließen
            op = "closePath"
        current.append((op, args))
        if op == "closePath":
            contours.append(current)
            current = []
    return contours


def replay(contour, pen):
    for op, args in contour:
        getattr(pen, op)(*args)


def fix_directions(contours):
    """Außenkonturen im Uhrzeigersinn, Punzen dagegen.

    Das ist die Richtung aller bisherigen (aus FontForge stammenden) Glyphen.
    Gemischte Richtungen ergäben Löcher, sobald sich alte und neue Glyphen
    als Komponenten überlappen. fontmake normalisiert die Richtung beim Build.
    """
    result = RecordingPen()
    for i, contour in enumerate(contours):
        area = AreaPen()
        replay(contour, area)
        start = contour[0][1][0]
        depth = 0                    # in wie vielen anderen Konturen liegt diese?
        for j, other in enumerate(contours):
            if i != j:
                inside = PointInsidePen(None, start, evenOdd=True)
                replay(other, inside)
                depth += bool(inside.getResult())
        correct = (depth % 2 == 0) == (area.value < 0)   # Fläche < 0: Uhrzeigersinn
        replay(contour, result if correct else ReverseContourPen(result))
    return result


@lru_cache(maxsize=None)
def fontra_names():
    """Glyphennamen, wie Fontra sie verwendet, als {Name: Codepoint}.

    Fontra erzeugt seine Namensliste aus der GlyphData.xml von glyphsLib.
    glyphsLib wird mit fontmake installiert; fehlt es, bleibt die Liste leer.
    """
    try:
        spec = find_spec("glyphsLib")
        folder = Path(next(iter(spec.submodule_search_locations)))
        root = ET.parse(folder / "data" / "GlyphData.xml").getroot()
    except (AttributeError, ImportError, OSError, StopIteration, ET.ParseError):
        return {}
    return {el.get("name"): int(el.get("unicode"), 16)
            for el in root.iter("glyph") if el.get("unicode")}


def unicode_for(name):
    """Codepoint aus dem Glyphennamen; None bei Varianten und Ligaturen.

    Zuerst gelten die Namen aus Fontra, danach AGL-Namen und uniXXXX.
    """
    if name in fontra_names():
        return fontra_names()[name]
    if "." in name or "_" in name:
        return None
    text = agl.toUnicode(name)
    return ord(text) if len(text) == 1 else None


def import_glyph(glyph_set, used_unicodes, spec):
    stem, name, hexcode = (spec.split(":") + ["", ""])[:3]
    stem = stem.removesuffix(".svg")
    name = name or stem
    try:
        code = int(hexcode, 16) if hexcode else unicode_for(name)
    except ValueError:
        return f"{spec}: '{hexcode}' ist kein Codepoint in Hex"
    path = SVG_DIR / f"{stem}.svg"

    if not path.exists():
        return f"{spec}: {path.relative_to(ROOT)} nicht gefunden"
    if name in glyph_set:
        return f"{spec}: Glyphe '{name}' existiert bereits, nicht überschrieben"
    problem = check_svg(path)
    if problem:
        return f"{spec}: {problem}"
    contours = read_contours(path)
    if not contours:
        return f"{spec}: keine Pfade im SVG gefunden"

    outline = fix_directions(contours)
    bounds = BoundsPen(None)
    outline.replay(bounds)

    glyph = Glyph()
    glyph.width = round(bounds.bounds[2])
    note = "ohne Unicode"
    if code in used_unicodes:
        note = f"ohne Unicode (U+{code:04X} gehört schon zu '{used_unicodes[code]}')"
    elif code is not None:
        glyph.unicodes = [code]
        used_unicodes[code] = name
        note = f"U+{code:04X}"

    glyph_set.writeGlyph(
        name, glyph,
        drawPointsFunc=lambda pen: outline.replay(SegmentToPointPen(pen)),
    )
    print(f"  {name}: {len(contours)} Kontur(en), Dickte {glyph.width}, {note}")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("glyphs", nargs="+", metavar="SVG[:GLYPHENNAME[:CODEPOINT]]",
                        help="SVG-Dateiname ohne Endung, optional mit abweichendem "
                             "Glyphennamen und Codepoint in Hex")
    args = parser.parse_args()

    if not SOURCE.exists():
        sys.exit(f"Quelle nicht gefunden: {SOURCE}")

    glyph_set = GlyphSet(str(SOURCE / "glyphs"))
    used_unicodes = {code: name
                     for name, codes in glyph_set.getUnicodes().items()
                     for code in codes}

    if not fontra_names():
        print("Hinweis: glyphsLib nicht gefunden (wird mit fontmake installiert). "
              "Codepoints werden nur aus AGL-Namen und uniXXXX abgeleitet.")
    print(f"Import nach {SOURCE.relative_to(ROOT)}:")
    errors = [e for e in (import_glyph(glyph_set, used_unicodes, s) for s in args.glyphs) if e]
    glyph_set.writeContents()

    for e in errors:
        print(f"  FEHLER {e}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()