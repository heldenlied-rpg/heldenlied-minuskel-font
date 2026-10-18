#!/usr/bin/env python3
"""Setzt die Sidebearings aller Glyphen eines UFO auf 0.

    python scripts/zero_sidebearings.py [pfad/zum/Font.ufo] [--dry-run]

Ablauf:
  1. Bounding-Box aller Glyphen im Ausgangszustand messen (inkl. Komponenten).
  2. Jeden Glyphen um -xMin verschieben (Konturen, Anker, Hilfslinien),
     Dickte = xMax - xMin.
  3. Komponenten-Offsets ausgleichen, damit Composites (Akzente etc.)
     optisch unveraendert bleiben, obwohl sich ihre Basisglyphen bewegen.

Uebersprungen werden:
  - leere Glyphen (space, nbspace ...) - sie haben keine Sidebearings
  - Glyphen mit Dickte 0 (kombinierende Akzente), ausser mit --include-zero-width

Verschoben wird um ganze Einheiten, damit keine neuen Kommakoordinaten
entstehen. Liegt ein Kurvenextremum nicht auf einer ganzen Einheit, bleibt
ein Rest von < 1 Einheit im Sidebearing.
"""

import argparse
import sys
from pathlib import Path

from fontTools.misc.roundTools import otRound
from fontTools.misc.transform import Transform
from ufoLib2 import Font

DEFAULT_UFO = (
    Path(__file__).resolve().parent.parent
    / "sources"
    / "HeldenliedMinuskel-Regular.ufo"
)


def check_components(layer):
    """Sucht Zirkelbezuege und fehlende Basisglyphen in den Komponenten.

    Liefert (zyklen, fehlende): zyklen als Liste von Namensketten
    (z. B. ["i", "idotless", "i"]), fehlende als Liste (glyph, basis).
    """
    missing = [
        (glyph.name, component.baseGlyph)
        for glyph in layer
        for component in glyph.components
        if component.baseGlyph not in layer
    ]

    cycles = []
    done = set()

    def visit(name, path):
        if name in path:
            cycles.append(path[path.index(name):] + [name])
            return
        if name in done or name not in layer:
            return
        for component in layer[name].components:
            visit(component.baseGlyph, path + [name])
        done.add(name)

    for name in sorted(layer.keys()):
        visit(name, [])
    return cycles, missing


def measure(font, include_zero_width):
    """Liefert {glyphname: (dx, neue_dickte)} und die Liste der Uebersprungenen."""
    layer = font.layers.defaultLayer
    plan, skipped = {}, []
    for glyph in layer:
        bounds = glyph.getBounds(layer)
        if bounds is None:
            skipped.append((glyph.name, "leer"))
            continue
        if glyph.width == 0 and not include_zero_width:
            skipped.append((glyph.name, "Dickte 0"))
            continue
        x_min, x_max = otRound(bounds.xMin), otRound(bounds.xMax)
        plan[glyph.name] = (-x_min, x_max - x_min)
    return plan, skipped


def apply(glyph, dx, width, plan):
    for contour in glyph.contours:
        for point in contour.points:
            point.x += dx

    for anchor in glyph.anchors:
        anchor.x += dx

    for guideline in glyph.guidelines:
        if guideline.x is not None:
            guideline.x += dx

    for component in glyph.components:
        # Die Basis wandert um base_dx; durch die Komponenten-Transformation
        # wird daraus (xx * base_dx, xy * base_dx). Das wird hier herausgerechnet.
        base_dx = plan.get(component.baseGlyph, (0, 0))[0]
        xx, xy, yx, yy, off_x, off_y = component.transformation
        component.transformation = Transform(
            xx, xy, yx, yy,
            off_x + dx - xx * base_dx,
            off_y - xy * base_dx,
        )

    glyph.width = width


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ufo", nargs="?", type=Path, default=DEFAULT_UFO)
    parser.add_argument(
        "--dry-run", action="store_true", help="nur anzeigen, nichts speichern"
    )
    parser.add_argument(
        "--include-zero-width",
        action="store_true",
        help="auch Glyphen mit Dickte 0 (kombinierende Akzente) bearbeiten",
    )
    args = parser.parse_args()

    font = Font.open(args.ufo, lazy=False)

    cycles, missing = check_components(font.layers.defaultLayer)
    if cycles or missing:
        print("Abbruch, nichts geaendert - fehlerhafte Komponenten im UFO:")
        for chain in cycles:
            print("  Zirkelbezug: " + " -> ".join(chain))
        for glyph_name, base_name in missing:
            print(f"  {glyph_name} verweist auf fehlenden Glyphen {base_name}")
        sys.exit(1)

    plan, skipped = measure(font, args.include_zero_width)

    default_layer = font.layers.defaultLayer
    changed = 0
    for name in sorted(plan):
        dx, width = plan[name]
        old_width = default_layer[name].width
        if dx == 0 and width == old_width:
            continue
        changed += 1
        print(f"{name:<28} dx {dx:+5d}   Dickte {old_width:g} -> {width}")

    if not args.dry_run:
        # Alle Ebenen mitziehen, damit Hintergrund-Skizzen deckungsgleich bleiben.
        for layer in font.layers:
            for glyph in layer:
                if glyph.name in plan:
                    dx, width = plan[glyph.name]
                    apply(glyph, dx, width, plan)
        font.save()

    print()
    for name, reason in sorted(skipped):
        print(f"uebersprungen: {name} ({reason})")
    status = "wuerden geaendert (dry-run)" if args.dry_run else "geaendert"
    print(f"\n{changed} Glyphen {status}, {len(skipped)} uebersprungen.")


if __name__ == "__main__":
    main()
