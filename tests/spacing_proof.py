#!/usr/bin/env python3
"""
Spacing-Prüfung für Heldenlied Minuskel.

Erzeugt tests/output/spacing.html mit
  1. einer Messtabelle: optische Vor-/Nachbreite jeder Grundglyphe,
     verglichen mit einer Referenzglyphe (n oder o), mit Korrekturvorschlag,
  2. Composites, deren Breite oder Lage von ihrer Basisglyphe abweicht,
  3. Kontrollzeilen (nn?nn oo?oo) für alle Glyphen, auch ohne Unicode,
  4. optional Wortproben mit Features und Kerning (wenn der Font gebaut ist
     und uharfbuzz installiert ist).

Gezeichnet wird direkt aus der UFO-Quelle, ein Build ist für 1–3 nicht nötig.

Aufruf aus dem Repo-Stammordner:
    python tests/spacing_proof.py
    python tests/spacing_proof.py --tolerance 4 --depth 100

Messprinzip
-----------
Für jede Seite wird in Zeilen von 5 Einheiten zwischen Grundlinie und
x-Höhe der Abstand vom Rand der Dickte bis zur ersten Kontur gemessen.
Tiefen über --depth werden abgeschnitten (offene Formen wie r oder c sollen
nicht unendlich „hell“ zählen). Der Mittelwert ist die optische Vor- bzw.
Nachbreite: die Weißfläche je Zeile. Spitze Serifen oder Ein-/Ausstriche
verfälschen diesen Wert kaum, anders als die geometrische Vorbreite
(Abstand zum Extrempunkt).

Seiten mit ähnlicher Form sollen ähnlich viel Weiß haben. Welche Seite mit
welcher Referenz verglichen wird, steht in REFERENCE unten; Seiten ohne
Eintrag gelten als „frei“ und werden nur angezeigt, nicht bewertet.
"""
import argparse
import html
import math
import sys
from pathlib import Path

from fontTools.misc.transform import DecomposedTransform, Transform
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.recordingPen import RecordingPointPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ufoLib import UFOReader

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sources" / "HeldenliedMinuskel-Regular.ufo"
OTF = ROOT / "fonts" / "otf" / "HeldenliedMinuskel-Regular.otf"
OUT = ROOT / "tests" / "output" / "spacing.html"

# ---------------------------------------------------------------------------
# Referenzen: Seite -> Glyphe, deren optisches Weiß auf derselben Seite
# als Soll gilt. "n" für gerade Stämme, "o" für runde Seiten.
# Nicht aufgeführte Seiten sind frei (nur Kontrollzeilen, kein Vorschlag).
# Versalien sind Composites der Kleinbuchstaben und folgen automatisch.
# ---------------------------------------------------------------------------
REFERENCE = {
    "left": {
        "b": "n", "h": "n", "i": "n", "k": "n", "l": "n", "m": "n",
        "p": "n", "r": "n", "u": "n", "v": "n", "w": "n",
        "thorn": "n", "germandbls": "n", "idotless": "n", "i.hist": "n",
        "b.ss01": "n", "h.ss01": "n", "k.ss01": "n", "l.ss01": "n",
        "v.hist": "n", "w.hist": "n",
        "c": "o", "d": "o", "e": "o", "q": "o", "eth": "o", "oe": "o",
        "d.ss01": "o", "zero": "o",
    },
    "right": {
        "d": "n", "h": "n", "i": "n", "l": "n", "m": "n",
        "q": "n", "u": "n", "idotless": "n", "i.hist": "n",
        "d.ss01": "n", "h.ss01": "n", "l.ss01": "n", "v.hist": "n",
        "w.hist": "n",
        "b": "o", "p": "o", "thorn": "o", "b.ss01": "o", "zero": "o",
    },
}

# Nachbarn für die Kontrollzeilen
CONTROL = [("n", "n"), ("o", "o"), ("n", "o")]

# Wortproben (nur mit gebautem Font und uharfbuzz)
WORDS = [
    ("", "Heldenlied – das Schicksal der Helden"),
    ("", "Wasserstraße, Flußufer, Kieselsteine, Mondsee und Ruhn"),
    ("", "minimum illum nulli lumen; quoniam tu mecum es."),
    ("", "„Waldgeister“, ‚Zwerge‘, «Alben» – (Drachen) [Elfen] 26.9.872"),
    ("hist", "Wasserstraße, Flußufer, Kieselsteine, Mondsee und Ruhn"),
    ("hist", "psalmus david 23: dominus regit me et nihil mihi deerit"),
    ("ss01", "Heldenlied – das Schicksal der Helden, hoch und blühend"),
    ("", "Frühstück für Øystein, Łukasz, Çağla, Ðorđe und Þóra"),
]

VC_KEY = "com.black-foundry.variable-components"


class Glyph:
    """Minimales Glyphenobjekt für UFOReader.readGlyph."""

    def __init__(self):
        self.width = 0
        self.unicodes = []
        self.lib = {}
        self.anchors = []


class Source:
    def __init__(self, path):
        self.reader = UFOReader(path)
        glyphset = self.reader.getGlyphSet()
        self.glyphs = {}
        for name in glyphset.keys():
            g = Glyph()
            rec = RecordingPointPen()
            glyphset.readGlyph(name, g, rec)
            g.rec = rec
            g.components = [(v[1][0], tuple(v[1][1]))
                            for v in rec.value if v[0] == "addComponent"]
            self.glyphs[name] = g
        info = Glyph()
        self.reader.readInfo(info)
        self.xheight = getattr(info, "xHeight", 460) or 460
        self.ascender = getattr(info, "openTypeHheaAscender", 960) or 960
        self.descender = getattr(info, "openTypeHheaDescender", -310) or -310
        self.order = self._order()

    def _order(self):
        lib = self.reader.readLib()
        order = [n for n in lib.get("public.glyphOrder", []) if n in self.glyphs]
        rest = sorted(set(self.glyphs) - set(order),
                      key=lambda n: (min(self.glyphs[n].unicodes or [0x110000]), n))
        return order + rest

    def draw(self, name, pen):
        """Zeichnet die Glyphe vollständig aufgelöst (auch Fontra-Komponenten)."""
        g = self.glyphs[name]
        g.rec.replay(_ComponentResolver(self, pen))
        for vc in g.lib.get(VC_KEY, []):
            t = vc.get("transformation", {})
            dt = DecomposedTransform(**{k: t[k] for k in (
                "translateX", "translateY", "rotation", "scaleX", "scaleY",
                "skewX", "skewY", "tCenterX", "tCenterY") if k in t})
            self.draw(vc["base"], TransformPen(pen, dt.toTransform()))

    def is_mark(self, name):
        return self.glyphs[name].width == 0


class _ComponentResolver(PointToSegmentPen):
    def __init__(self, source, pen):
        super().__init__(pen)
        self.source = source
        self.target = pen

    def addComponent(self, baseGlyph, transformation, **kw):
        if baseGlyph in self.source.glyphs:
            self.source.draw(baseGlyph, TransformPen(self.target, transformation))


class _PolygonPen(BasePen):
    """Sammelt Konturen als Polygone (Kurven angenähert)."""

    def __init__(self):
        super().__init__(None)
        self.polys = []
        self.cur = []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, 9):
            t = i / 8
            mt = 1 - t
            self.cur.append((
                mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0],
                mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, 9):
            t = i / 8
            mt = 1 - t
            self.cur.append((mt**2 * p0[0] + 2 * mt * t * p1[0] + t**2 * p2[0],
                             mt**2 * p0[1] + 2 * mt * t * p1[1] + t**2 * p2[1]))

    def _closePath(self):
        if len(self.cur) > 2:
            self.polys.append(self.cur)
        self.cur = []

    _endPath = _closePath


def side_profile(source, name, y0, y1, step=5):
    """Pro Zeile: (linker Abstand, rechter Abstand) zur Kontur oder None."""
    pen = _PolygonPen()
    source.draw(name, pen)
    width = source.glyphs[name].width
    rows = []
    y = y0
    while y <= y1:
        xs = []
        for poly in pen.polys:
            n = len(poly)
            for i in range(n):
                (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
                if (ay <= y < by) or (by <= y < ay):
                    xs.append(ax + (y - ay) / (by - ay) * (bx - ax))
        rows.append((min(xs), width - max(xs)) if xs else None)
        y += step
    return rows


def optical(rows, depth):
    """Mittleres Weiß je Seite; Zeilen ohne Kontur zählen als volle Tiefe."""
    if not rows or all(r is None for r in rows):
        return None, None
    left = [min(r[0], depth) if r else depth for r in rows]
    right = [min(r[1], depth) if r else depth for r in rows]
    return sum(left) / len(left), sum(right) / len(right)


def bounds(source, name):
    bp = BoundsPen(None)
    source.draw(name, bp)
    return bp.bounds


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

CSS = """
:root { --ink:#1d1a16; --paper:#fbf8f2; --muted:#6f675c; --line:#ddd5c7;
        --ok:#2f7d4f; --warn:#b26b00; --bad:#b3261e; --box:#7aa2d6; }
body { font: 14px/1.45 system-ui, sans-serif; color: var(--ink);
       background: var(--paper); margin: 0 auto; max-width: 1200px; padding: 16px; }
h1 { font-size: 22px; } h2 { font-size: 18px; margin-top: 2em;
     border-bottom: 1px solid var(--line); padding-bottom: 4px; }
p.note { color: var(--muted); max-width: 70ch; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 3px 8px; border-bottom: 1px solid var(--line); text-align: right; }
th:first-child, td:first-child, td.l { text-align: left; }
th { position: sticky; top: 0; background: var(--paper); }
td.ok { color: var(--ok); } td.warn { color: var(--warn); font-weight: 600; }
td.bad { color: var(--bad); font-weight: 700; } td.free { color: var(--muted); }
.row { display: flex; align-items: center; gap: 12px; border-bottom: 1px solid var(--line);
       padding: 2px 0; }
.row .name { width: 170px; flex: none; font-size: 12px; color: var(--muted);
             overflow: hidden; text-overflow: ellipsis; }
.row.flag .name { color: var(--bad); font-weight: 600; }
svg.line { height: 64px; overflow: visible; }
svg.word { height: 56px; overflow: visible; }
.boxes .adv { display: none; }
body.showboxes .boxes .adv { display: inline; }
.controls { position: sticky; top: 0; background: var(--paper); padding: 6px 0;
            z-index: 2; border-bottom: 1px solid var(--line); }
.filter { margin-left: 16px; }
"""

JS = """
function toggleBoxes(cb){ document.body.classList.toggle('showboxes', cb.checked); }
function onlyFlagged(cb){
  document.querySelectorAll('#proof .row').forEach(r => {
    r.style.display = (cb.checked && !r.classList.contains('flag')) ? 'none' : '';
  });
}
"""


class SVGLib:
    def __init__(self, source):
        self.source = source
        self.ids = {}
        self.defs = []

    def ref(self, name):
        if name not in self.ids:
            gid = f"g{len(self.ids)}"
            self.ids[name] = gid
            pen = SVGPathPen(None)
            self.source.draw(name, pen)
            self.defs.append(f'<path id="{gid}" d="{pen.getCommands()}"/>')
        return self.ids[name]

    def line(self, names, css="line", positions=None):
        """names: Liste von Glyphennamen; positions: optional (dx, advance)."""
        src = self.source
        x = 0
        parts = []
        for i, n in enumerate(names):
            if positions:
                xo, adv = positions[i]
            else:
                xo, adv = 0, src.glyphs[n].width
            gid = self.ref(n)
            parts.append(f'<use href="#{gid}" x="{x + xo:.0f}" transform="scale(1,-1)" y="0"/>')
            parts.append(f'<rect class="adv" x="{x:.0f}" y="{-src.ascender}" width="{max(adv, 1):.0f}" '
                         f'height="{src.ascender - src.descender}" fill="none" '
                         f'stroke="var(--box)" stroke-width="2"/>')
            x += adv
        top, bottom = src.ascender, -src.descender
        width = max(x, 1)
        h = 64 if css == "line" else 56
        return (f'<svg class="{css} boxes" viewBox="0 {-top} {width:.0f} {top + bottom}" '
                f'style="width:{width * h / (top + bottom):.0f}px">'
                f'<g fill="currentColor">{"".join(parts)}</g></svg>')


def fmt(v):
    return "–" if v is None else f"{round(v) + 0:.0f}"


def classify(delta, tol):
    if delta is None:
        return "free"
    a = abs(delta)
    return "ok" if a <= tol else ("warn" if a <= 2 * tol else "bad")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ufo", default=str(SOURCE))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--depth", type=float, default=None,
                    help="maximale Messtiefe in Einheiten (Standard: 25 %% der x-Höhe)")
    ap.add_argument("--tolerance", type=float, default=5,
                    help="erlaubte Abweichung vom Soll in Einheiten (Standard 5)")
    args = ap.parse_args()

    src = Source(args.ufo)
    depth = args.depth or round(src.xheight * 0.25)
    tol = args.tolerance
    svg = SVGLib(src)

    names = [n for n in src.order if not src.is_mark(n) and n not in (".notdef",)]
    # Composites: nur Komponenten, keine eigenen Konturen
    composites = {n for n in names if src.glyphs[n].components
                  and not any(v[0] == "beginPath" for v in src.glyphs[n].rec.value)}

    # Messung
    measure = {}
    for n in names:
        rows = side_profile(src, n, 0, src.xheight)
        measure[n] = optical(rows, depth)

    def target(side, n):
        ref = REFERENCE[side].get(n)
        if not ref or ref not in measure:
            return None
        return measure[ref][0 if side == "left" else 1]

    table = []
    flagged = set()
    for n in names:
        g = src.glyphs[n]
        base_comp = g.components[0][0] if len(g.components) >= 1 else None
        # Composites mit Basis an x=0 und gleicher Breite erben das Spacing
        if n in composites and base_comp and base_comp in src.glyphs:
            continue
        ol, orr = measure[n]
        if ol is None:
            continue
        tl, tr = target("left", n), target("right", n)
        dl = None if tl is None else tl - ol
        dr = None if tr is None else tr - orr
        b = bounds(src, n)
        lsb = b[0] if b else None
        rsb = g.width - b[2] if b else None
        cl, cr = classify(dl, tol), classify(dr, tol)
        if "warn" in (cl, cr) or "bad" in (cl, cr):
            flagged.add(n)
        table.append((n, g, lsb, rsb, ol, orr, dl, dr, cl, cr))

    # Composites (Basis + Akzente), die von der Basis abweichen, und
    # Glyphen, deren Kontur weit über die Dickte hinausragt
    comp_issues = []
    for n in names:
        g = src.glyphs[n]
        msgs = []
        base = ""
        accented = (n in composites and g.components[0][0] in src.glyphs
                    and not src.is_mark(g.components[0][0])
                    and all(c in src.glyphs and src.is_mark(c) for c, _ in g.components[1:]))
        if accented:
            base, t = g.components[0]
            bw = src.glyphs[base].width
            if abs(g.width - bw) > 0.5:
                msgs.append(f"Breite {g.width:.0f} statt {bw:.0f}")
            if abs(t[4]) > 0.5:
                msgs.append(f"Basis um x {t[4]:+.0f} verschoben")
            if tuple(t[:4]) != (1, 0, 0, 1):
                msgs.append("Basis skaliert/gedreht")
        bb = bounds(src, n)
        if bb and (bb[0] < -20 or bb[2] > g.width + 20):
            # bei Composites nur melden, wenn die Basis nicht schon übersteht
            bbase = bounds(src, base) if base else None
            if not (bbase and bbase[0] <= bb[0] + 1 and bbase[2] >= bb[2] - 1
                    and abs(g.width - src.glyphs[base].width) < 0.5):
                msgs.append(f"Kontur ragt über die Dickte (x {bb[0]:.0f} … {bb[2]:.0f}, "
                            f"Breite {g.width:.0f})")
        if msgs:
            comp_issues.append((n, base or "–", msgs))
            flagged.add(n)

    # ---------------- HTML zusammensetzen ----------------
    out = []
    out.append("<h1>Heldenlied Minuskel – Spacing-Prüfung</h1>")
    out.append(f'<p class="note">Quelle: <code>{html.escape(str(Path(args.ufo).name))}</code> · '
               f'Messband 0–{src.xheight} (x-Höhe) · Messtiefe {depth:.0f} · Toleranz ±{tol:.0f}. '
               f'Referenzwerte: n links {fmt(measure["n"][0])} / rechts {fmt(measure["n"][1])}, '
               f'o links {fmt(measure["o"][0])} / rechts {fmt(measure["o"][1])}. '
               f'{len(flagged)} Glyphen auffällig.</p>')

    out.append("<h2>1 · Messtabelle</h2>")
    out.append('<p class="note"><b>Optisch</b> = mittleres Weiß je Seite (siehe Kopf des Skripts). '
               '<b>Vorschlag</b> = um so viele Einheiten die Vor-/Nachbreite ändern, damit die Seite '
               'so viel Weiß hat wie ihre Referenz (+ = mehr Abstand). Grün im Rahmen, orange bis '
               'doppelte Toleranz, rot darüber, grau = frei (nur Augenmaß). Der Vorschlag ist ein '
               'Ausgangspunkt – die Kontrollzeilen entscheiden.</p>')
    out.append("<table><tr><th>Glyphe</th><th>Breite</th><th>LSB</th><th>RSB</th>"
               "<th>optisch L</th><th>optisch R</th><th>Vorschlag L</th><th>Vorschlag R</th>"
               "<th>Ref L</th><th>Ref R</th></tr>")
    for n, g, lsb, rsb, ol, orr, dl, dr, cl, cr in table:
        out.append(
            f"<tr><td>{html.escape(n)}</td><td>{g.width:.0f}</td><td>{fmt(lsb)}</td><td>{fmt(rsb)}</td>"
            f"<td>{fmt(ol)}</td><td>{fmt(orr)}</td>"
            f'<td class="{cl}">{"frei" if dl is None else f"{round(dl) + 0:+.0f}"}</td>'
            f'<td class="{cr}">{"frei" if dr is None else f"{round(dr) + 0:+.0f}"}</td>'
            f'<td class="l">{REFERENCE["left"].get(n, "")}</td>'
            f'<td class="l">{REFERENCE["right"].get(n, "")}</td></tr>')
    out.append("</table>")

    out.append("<h2>2 · Composites mit eigenem Spacing, Überhänge</h2>")
    if comp_issues:
        out.append('<p class="note">Akzent-Composites, die Breite oder Lage ihrer '
                   'Basisglyphe nicht übernehmen, und Glyphen, deren Kontur mehr als 20 Einheiten '
                   'über die Dickte hinausragt. Beides kann gewollt sein (breiter Akzent auf i, '
                   'überhängender Caron bei ď), sollte aber bewusst so sein.</p><table><tr><th>Glyphe</th><th>Basis</th>'
                   '<th class="l">Befund</th><th class="l">Probe</th></tr>')
        for n, base, msgs in comp_issues:
            ctx = ["n", "n", n, "n", "n"] if "n" in src.glyphs else [n]
            out.append(f'<tr><td>{html.escape(n)}</td><td class="l">{html.escape(base)}</td>'
                       f'<td class="l">{html.escape("; ".join(msgs))}</td>'
                       f'<td class="l">{svg.line(ctx)}</td></tr>')
        out.append("</table>")
    else:
        out.append('<p class="note">Keine Abweichungen.</p>')

    out.append('<h2>3 · Kontrollzeilen</h2>')
    out.append('<p class="note">Jede Glyphe zwischen nn, oo und n…o, ohne Kerning und ohne '
               'Features. Rot markierte Namen sind in Tabelle 1 oder 2 auffällig.</p>')
    out.append('<div class="controls"><label><input type="checkbox" onchange="toggleBoxes(this)"> '
               'Dickten anzeigen</label><label class="filter"><input type="checkbox" '
               'onchange="onlyFlagged(this)"> nur auffällige</label></div><div id="proof">')
    for n in names:
        seq = []
        for a, b in CONTROL:
            if a in src.glyphs and b in src.glyphs:
                seq += [a, a, n, b, b, "space"] if "space" in src.glyphs else [a, a, n, b, b]
        cls = "row flag" if n in flagged else "row"
        out.append(f'<div class="{cls}"><span class="name">{html.escape(n)}</span>{svg.line(seq)}</div>')
    out.append("</div>")

    # Wortproben
    words_html = word_samples(svg)
    out.append("<h2>4 · Wortproben (gebauter Font, mit Features und Kerning)</h2>")
    out.append(words_html)

    page = (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Spacing-Prüfung</title><style>{CSS}</style><script>{JS}</script></head><body>"
        f'<svg width="0" height="0" style="position:absolute"><defs>{"".join(svg.defs)}</defs></svg>'
        + "\n".join(out) + "</body></html>")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    print(f"{out_path} geschrieben – {len(table)} Grundglyphen gemessen, "
          f"{len(flagged)} auffällig, {len(comp_issues)} Composites mit eigenem Spacing.")


def word_samples(svg):
    """Wortproben mit HarfBuzz aus dem gebauten OTF. Gezeichnet wird aus der
    UFO-Quelle; Glyphennamen werden über die Glyphenreihenfolge des OTF
    zugeordnet (fontmake benennt Glyphen beim Export teils um)."""
    try:
        import uharfbuzz as hb
        from fontTools.ttLib import TTFont
    except ImportError:
        return '<p class="note">uharfbuzz nicht installiert – übersprungen.</p>'
    if not OTF.exists():
        return ('<p class="note">Kein gebauter Font gefunden – zuerst '
                '<code>python scripts/build.py</code> ausführen.</p>')
    tt = TTFont(OTF)
    order = tt.getGlyphOrder()
    # Produktionsnamen -> UFO-Namen: über Unicode, sonst public.postscriptNames
    lib = svg.source.reader.readLib()
    ps = {v: k for k, v in lib.get("public.postscriptNames", {}).items()}
    cmap = tt.getBestCmap()
    for name, g in svg.source.glyphs.items():
        for u in g.unicodes:
            if u in cmap:
                ps.setdefault(cmap[u], name)
    face = hb.Face(OTF.read_bytes())
    font = hb.Font(face)
    parts = []
    stale = False
    for feats, text in WORDS:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {f: True for f in feats.split(",") if f})
        names, pos = [], []
        for info, p in zip(buf.glyph_infos, buf.glyph_positions):
            name = order[info.codepoint]
            name = ps.get(name, name)
            if name not in svg.source.glyphs:
                stale = True
                continue
            names.append(name)
            pos.append((p.x_offset, p.x_advance))
        label = f"[{feats}] " if feats else ""
        parts.append(f'<div class="row"><span class="name">{html.escape(label + text)}</span>'
                     f'{svg.line(names, "word", pos)}</div>')
    note = ""
    if stale:
        note = ('<p class="note">Hinweis: Der gebaute Font enthält Glyphen, die es in der '
                'Quelle nicht mehr gibt – bitte neu bauen.</p>')
    return note + "".join(parts)


if __name__ == "__main__":
    main()
