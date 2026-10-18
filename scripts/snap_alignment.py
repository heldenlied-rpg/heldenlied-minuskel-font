#!/usr/bin/env python3
"""
Rastet Punkte auf Grundlinie, x-Höhe und Oberlänge ein (Fontbakery: outline_alignment_miss).

On-Curve-Punkte, die bis zu 2,5 Einheiten neben einer Zone liegen, werden auf die
Zone geschoben; die direkt angrenzenden Anfasser wandern um denselben Betrag mit,
damit Kurvenrichtung und Glätte erhalten bleiben.

Zonen: Grundlinie 0 und Oberlänge/Versalhöhe 707 für alle Glyphen,
x-Höhe 460 nur für Kleinbuchstaben (Unicode-Kategorie Ll, bei unkodierten
Varianten und Ligaturen über die Namensteile vor dem Punkt bzw. am Unterstrich).

Aufruf aus dem Repo-Stammordner:
    python scripts/snap_alignment.py           # nur anzeigen
    python scripts/snap_alignment.py --write   # Änderungen schreiben
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLYPHS = ROOT / "sources" / "HeldenliedMinuskel-Regular.ufo" / "glyphs"
TOL = 2.5

POINT = re.compile(r'(<point\b[^>]*?\by=")([-\d.eE]+)(")')
TYPE = re.compile(r'\btype="(\w+)"')
NAME = re.compile(r'<glyph name="([^"]+)"')


UNI = re.compile(r'<unicode hex="([0-9A-Fa-f]+)"')
LOWER = set()   # Namen der kodierten Kleinbuchstaben


def is_lowercase(glyphname):
    if glyphname in LOWER:
        return True
    parts = glyphname.split(".")[0].split("_")
    return all(p in LOWER for p in parts)


def zones(glyphname):
    z = [0, 707]
    if is_lowercase(glyphname):
        z.append(460)
    return z


def fmt(v):
    return str(int(v)) if float(v).is_integer() else repr(v)


def snap_glyph(text, glyphname):
    changes = []
    out = []
    pos = 0
    for cm in re.finditer(r"<contour\b.*?</contour>", text, re.S):
        out.append(text[pos:cm.start()])
        contour = cm.group(0)
        lines = contour.split("\n")
        idx = [i for i, l in enumerate(lines) if "<point" in l]
        pts = []
        for i in idx:
            y = float(POINT.search(lines[i]).group(2))
            t = TYPE.search(lines[i])
            pts.append({"line": i, "y": y, "on": bool(t and t.group(1) != "offcurve"), "dy": 0.0})
        n = len(pts)
        for k, p in enumerate(pts):
            if not p["on"]:
                continue
            for z in zones(glyphname):
                d = z - p["y"]
                if 0 < abs(d) <= TOL:
                    p["dy"] = d
                    for nb in (pts[(k - 1) % n], pts[(k + 1) % n]):
                        if not nb["on"] and nb["dy"] == 0:
                            nb["dy"] = d
                    changes.append((p["y"], z))
                    break
        for p in pts:
            if p["dy"]:
                ny = p["y"] + p["dy"]
                lines[p["line"]] = POINT.sub(lambda m: m.group(1) + fmt(round(ny, 4)) + m.group(3),
                                             lines[p["line"]], count=1)
        out.append("\n".join(lines))
        pos = cm.end()
    out.append(text[pos:])
    return "".join(out), changes


def main():
    write = "--write" in sys.argv
    for path in GLYPHS.glob("*.glif"):
        text = path.read_text(encoding="utf-8")
        u = UNI.search(text)
        if u and unicodedata.category(chr(int(u.group(1), 16))) == "Ll":
            LOWER.add(NAME.search(text).group(1))
    total = 0
    for path in sorted(GLYPHS.glob("*.glif")):
        text = path.read_text(encoding="utf-8")
        name = NAME.search(text).group(1)
        new, changes = snap_glyph(text, name)
        if changes:
            total += len(changes)
            desc = ", ".join(f"{fmt(a)}→{b}" for a, b in changes)
            print(f"{name}: {desc}")
            if write:
                path.write_text(new, encoding="utf-8")
    print(f"\n{total} Punkte {'eingerastet' if write else 'würden eingerastet'}.")


if __name__ == "__main__":
    main()
