#!/usr/bin/env python3
"""
Bereinigt Altlasten in der UFO-Quelle und in sources/svg (Oktober 2026).

1. PostScript-Hints aus der FontForge-Zeit entfernen (com.fontlab.hintData).
   Sie passen nicht mehr zu den Konturen und werden beim Build nicht verwendet.
2. top-Anker von y=697 auf y=460 setzen (Reste des alten Titulus-Features).
3. Glyphen auf die Namen umbenennen, die auch Fontra verwendet. Komponenten,
   features.fea sowie lib/groups/kerning (falls vorhanden) werden angepasst.
4. Glyphen entfernen, die nicht mehr gebraucht werden.
5. SVG-Vorlagen auf die heutigen Glyphennamen umbenennen.

Aufruf aus dem Repo-Stammordner (Fontra vorher schließen):
    python scripts/clean_ufo.py            # nur anzeigen
    python scripts/clean_ufo.py --write    # ausführen

Das Skript kann mehrfach laufen; ein zweiter Lauf ändert nichts mehr.
Konturen, Dickten und Codepoints bleiben unverändert.
"""
import argparse
import plistlib
import re
import sys
import unicodedata
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPointPen
from fontTools.ufoLib.glifLib import GlyphSet

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sources" / "HeldenliedMinuskel-Regular.ufo"
SVG_DIR = ROOT / "sources" / "svg"

# 1. Lib-Einträge, die aus den Glyphen entfernt werden
STALE_LIB_KEYS = ["com.fontlab.hintData"]
VARIABLE_COMPONENTS_KEY = "com.black-foundry.variable-components"

# 2. Anker: Glyphe -> (Ankername, altes y, neues y)
ANCHOR_FIXES = {name: ("top", 697, 460)
                for name in ["m", "p", "q", "M", "N", "P", "Q", "i.hist"]}

# 3. Glyphen: alter Name -> Name in Fontra
GLYPH_RENAMES = {
    "dotlessi": "idotless",
    "uni00A0": "nbspace",
    "uni204F": "reversedsemicolon",
    "uniA752": "Pflourish",
    "uniA753": "pflourish",
}

# 4. Glyphen, die entfallen
GLYPH_DELETIONS = ["uniF1E7"]    # Private-Use-Codepoint, Kontur = question.hist

# 5. SVG-Vorlagen: alter Dateiname -> Glyphenname (jeweils ohne ".svg").
#    Zuordnung nach Konturvergleich mit den Glyphen, nicht nach dem Namen:
#    bis 0.3 waren die historischen Formen der Standard und die modernen
#    lagen in ss06; seit 0.4 ist es umgekehrt (modern = Standard, alt = .hist).
SVG_RENAMES = {
    # Ziffern
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five.hist", "5.ss06": "five", "6": "six",
    "7": "seven.hist", "7.ss06": "seven", "8": "eight", "9": "nine",
    # Buchstaben
    "i": "i.hist", "i.ss06": "i",
    "j": "jdotless", "j.ss06": "j",
    "v.ss06": "v", "w.ss06": "w",
    "ß.ss06": "germandbls",
    "ä": "adieresis.hist", "ä.ss06": "adieresis",
    "ö": "odieresis.hist", "ö.ss06": "odieresis",
    "ü": "udieresis.hist", "ü.ss06": "udieresis",
    "f_ä": "f_adieresis.hist", "f_ä.ss06": "f_adieresis",
    "f_ö": "f_odieresis.hist", "f_ö.ss06": "f_odieresis",
    "f_ü": "f_udieresis.hist", "f_ü.ss06": "f_udieresis",
    "uniA753_p-pro": "pflourish",
    "titulus-uni0304": "macroncomb",
    # Satzzeichen
    "colon.ss06": "colon", "comma.ss06": "comma", "period.ss06": "period",
    "question.ss06": "question", "quotedbl.ss06": "quotedbl",
    "quotedblright.ss06": "quotedblright", "quotesingle.ss06": "quotesingle",
    "punctus": "periodcentered",
    "punctus-elevatus": "uni2E4E",
    "punctus_versus": "reversedsemicolon",
    "punctus_interrogativus-horizontal-tilde": "question.hist",
}


class Glyph:
    """Minimaler Container für die Attribute einer .glif-Datei."""


def heading(text):
    print(f"\n{text}")


def read_glyphs(glyph_set):
    glyphs = {}
    for name in glyph_set.keys():
        glyph, pen = Glyph(), RecordingPointPen()
        glyph_set.readGlyph(name, glyph, pen)
        glyphs[name] = (glyph, pen)
    return glyphs


def write_glyph(glyph_set, name, glyph, pen):
    if hasattr(glyph, "lib") and not glyph.lib:
        del glyph.lib
    glyph_set.writeGlyph(name, glyph, pen.replay, formatVersion=2)


def clean_glyphs(write):
    glyph_set = GlyphSet(str(SOURCE / "glyphs"))
    glyphs = read_glyphs(glyph_set)
    dirty = set()

    # 1. Hints
    hinted = []
    for name, (glyph, _) in glyphs.items():
        lib = getattr(glyph, "lib", None) or {}
        found = [key for key in STALE_LIB_KEYS if key in lib]
        for key in found:
            del lib[key]
        if found:
            hinted.append(name)
    dirty.update(hinted)
    heading(f"1. Alte Hints: {len(hinted)} Glyphen")
    if hinted:
        print("   " + " ".join(sorted(hinted)))

    # 2. Anker
    heading("2. Anker")
    count = 0
    for name, (anchor_name, old_y, new_y) in ANCHOR_FIXES.items():
        glyph = glyphs.get(name, (None,))[0]
        for anchor in getattr(glyph, "anchors", None) or []:
            if anchor.get("name") == anchor_name and anchor.get("y") == old_y:
                anchor["y"] = new_y
                dirty.add(name)
                count += 1
                print(f"   {name}: {anchor_name} y={old_y} -> y={new_y}")
    if not count:
        print("   nichts zu tun")

    # 3. Umbenennen
    heading("3. Glyphennamen")
    renames = {}
    for old, new in GLYPH_RENAMES.items():
        if old not in glyphs:
            continue
        if new in glyphs:
            print(f"   ÜBERSPRUNGEN {old}: '{new}' existiert bereits")
            continue
        renames[old] = new
    for old, new in renames.items():
        users = []
        for name, (glyph, pen) in glyphs.items():
            changed = False
            for i, (method, args, kwargs) in enumerate(pen.value):
                if method == "addComponent" and args[0] == old:
                    pen.value[i] = (method, (new,) + tuple(args[1:]), kwargs)
                    changed = True
            for component in (getattr(glyph, "lib", None) or {}).get(VARIABLE_COMPONENTS_KEY, []):
                if component.get("base") == old:
                    component["base"] = new
                    changed = True
            if changed:
                users.append(renames.get(name, name))
                dirty.add(name)
        note = f" (Komponente in: {', '.join(sorted(users))})" if users else ""
        print(f"   {old} -> {new}{note}")
    if not renames:
        print("   nichts zu tun")
    rename_in_features(renames, write)
    rename_in_plists(renames, write)

    # 4. Löschen
    heading("4. Entfernte Glyphen")
    fea_path = SOURCE / "features.fea"
    features = fea_path.read_text(encoding="utf-8") if fea_path.exists() else ""
    deletions = []
    for name in GLYPH_DELETIONS:
        if name not in glyphs:
            continue
        users = sorted(other for other, (_, pen) in glyphs.items()
                       if any(m == "addComponent" and a[0] == name for m, a, _ in pen.value))
        if users:
            print(f"   ÜBERSPRUNGEN {name}: wird als Komponente gebraucht in {', '.join(users)}")
            continue
        if token(name).search(features):
            print(f"   ÜBERSPRUNGEN {name}: wird in features.fea verwendet")
            continue
        deletions.append(name)
        print(f"   {name}")
    if not deletions:
        print("   nichts zu tun")
    rename_in_plists({}, write, deletions)

    if write:
        for name in deletions:
            glyph_set.deleteGlyph(name)
        for old in renames:
            glyph_set.deleteGlyph(old)
        for name in sorted(dirty | set(renames)):
            if name in deletions:
                continue
            glyph, pen = glyphs[name]
            write_glyph(glyph_set, renames.get(name, name), glyph, pen)
        if renames or deletions:
            glyph_set.writeContents()
    return renames, deletions


def token(name):
    """Regulärer Ausdruck für einen Glyphennamen als ganzes Wort."""
    return re.compile(rf"(?<![\w.\-]){re.escape(name)}(?![\w.\-])")


def rename_in_features(renames, write):
    path = SOURCE / "features.fea"
    if not path.exists():
        return
    with open(path, encoding="utf-8", newline="") as f:
        text = original = f.read()
    for old, new in renames.items():
        text, count = token(old).subn(new, text)
        if count:
            print(f"   features.fea: {old} -> {new} ({count}x)")
    if write and text != original:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)


def rename_in_plists(renames, write, deletions=()):
    """lib.plist, groups.plist und kerning.plist anpassen, falls vorhanden."""
    def fix_list(names):
        return [renames.get(n, n) for n in names if n not in deletions]

    def fix_keys(mapping):
        return {renames.get(k, k): v for k, v in mapping.items() if k not in deletions}

    for filename in ("lib.plist", "groups.plist", "kerning.plist"):
        path = SOURCE / filename
        if not path.exists():
            continue
        with open(path, "rb") as f:
            data = original = plistlib.load(f)
        if filename == "lib.plist":
            data = dict(data)
            for key in ("public.glyphOrder", "public.skipExportGlyphs"):
                if key in data:
                    data[key] = fix_list(data[key])
            for key in ("public.postscriptNames", "public.openTypeCategories"):
                if key in data:
                    data[key] = fix_keys(data[key])
        elif filename == "groups.plist":
            data = {group: fix_list(members) for group, members in data.items()}
        else:
            data = {first: fix_keys(seconds) for first, seconds in fix_keys(data).items()}
        if data != original:
            print(f"   {filename} angepasst")
            if write:
                with open(path, "wb") as f:
                    plistlib.dump(data, f, sort_keys=False)


def rename_svgs(glyph_names, write):
    heading("5. SVG-Vorlagen")
    if not SVG_DIR.exists():
        print("   Ordner sources/svg nicht gefunden")
        return
    # NFC, damit Umlaute im Dateinamen auf jedem Dateisystem erkannt werden
    present = {unicodedata.normalize("NFC", p.stem): p for p in SVG_DIR.glob("*.svg")}
    # Ketten (i.ss06 -> i, i -> i.hist): die zweite Stufe nur ausführen, solange
    # die erste noch aussteht. Sonst würde ein zweiter Lauf die neue Datei
    # erneut umbenennen.
    fed_by = {new: old for old, new in SVG_RENAMES.items()}
    todo = {old: new for old, new in SVG_RENAMES.items()
            if old in present and (old not in fed_by or fed_by[old] in present)}
    for old, new in list(todo.items()):
        if new in present and new not in todo:
            print(f"   ÜBERSPRUNGEN {old}.svg: {new}.svg existiert bereits")
            del todo[old]
    if not todo:
        print("   nichts zu tun")
        return
    for old, new in todo.items():
        note = "" if new in glyph_names else "   (keine Glyphe dieses Namens!)"
        print(f"   {old}.svg -> {new}.svg{note}")
    if write:
        # Zwei Schritte, damit sich Ketten und Tausche nicht überschreiben
        parked = {old: present[old].rename(present[old].with_suffix(".svg.umbenennen"))
                  for old in todo}
        for old, new in todo.items():
            parked[old].rename(SVG_DIR / f"{new}.svg")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="Änderungen ausführen")
    args = parser.parse_args()

    if not SOURCE.exists():
        sys.exit(f"Quelle nicht gefunden: {SOURCE}")

    print(("Bereinige " if args.write else "Probelauf für ") + str(SOURCE.relative_to(ROOT)))
    renames, deletions = clean_glyphs(args.write)

    glyph_names = set(GlyphSet(str(SOURCE / "glyphs")).keys())
    if not args.write:
        glyph_names = (glyph_names - set(renames) - set(deletions)) | set(renames.values())
    rename_svgs(glyph_names, args.write)

    if not args.write:
        print("\nNichts geändert. Zum Ausführen mit --write aufrufen.")


if __name__ == "__main__":
    main()
