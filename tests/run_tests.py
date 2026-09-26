#!/usr/bin/env python3
"""
Standardisierte Tests für Heldenlied Minuskel.

1. Prüft erwartete Glyphenfolgen automatisch mit HarfBuzz (uharfbuzz).
2. Erzeugt Testdokumente in tests/output/:
   - test.html  (Webfont eingebettet, interaktiv + alle Kombinationen)
   - test.fodt  (LibreOffice Writer, nutzt die INSTALLIERTE Schrift)
   - test.tex / test.pdf (LaTeX mit fontspec, nutzt den gebauten OTF)

Aufruf aus dem Repo-Stammordner:
    python tests/run_tests.py              # alles
    python tests/run_tests.py --no-pdf     # ohne LaTeX-Lauf
    python tests/run_tests.py --engine lualatex
"""
import argparse
import base64
import html
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from testcases import COMBOS, EXPECTED, INTERACTIVE, SAMPLES  # noqa: E402

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
OUT = TESTS / "output"
NAME = "HeldenliedMinuskel-Regular"
FAMILY = "Heldenlied Minuskel"
DEFAULT_OTF = ROOT / "fonts" / "otf" / f"{NAME}.otf"
DEFAULT_WOFF2 = ROOT / "fonts" / "webfonts" / f"{NAME}.woff2"


# ---------------------------------------------------------------
# Hilfsfunktionen für Feature-Schreibweisen
# ---------------------------------------------------------------

def label_features(feats):
    return ", ".join(f"{'+' if v else '-'}{k}" for k, v in feats.items()) or "Standard"


def css_features(feats):
    return ", ".join(f'"{k}" {int(v)}' for k, v in feats.items()) or "normal"


def lo_fontname(feats):
    if not feats:
        return FAMILY
    return FAMILY + ":" + "&".join(k if v else f"-{k}" for k, v in feats.items())


def tex_features(feats):
    return ",".join(f"RawFeature={'+' if v else '-'}{k}" for k, v in feats.items())


def tex_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("#", r"\#"), ("_", r"\_"), ("$", r"\$"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return s


# ---------------------------------------------------------------
# 1. Automatische Prüfung mit HarfBuzz
# ---------------------------------------------------------------

def check_shaping(otf):
    try:
        import uharfbuzz as hb
    except ImportError:
        print("! uharfbuzz nicht installiert, automatische Prüfung übersprungen.")
        print("  Installation: pip install uharfbuzz")
        return None
    blob = hb.Blob.from_file_path(str(otf))
    font = hb.Font(hb.Face(blob))
    failures = []
    for text, feats, expected in EXPECTED:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {k: bool(v) for k, v in feats.items()})
        got = " ".join(font.glyph_to_string(i.codepoint) for i in buf.glyph_infos)
        if got != expected:
            failures.append((text, feats, expected, got))
    total = len(EXPECTED)
    print(f"Glyphenprüfung: {total - len(failures)} von {total} bestanden")
    for text, feats, expected, got in failures:
        print(f"  FEHLER  {text!r} [{label_features(feats)}]")
        print(f"          erwartet: {expected}")
        print(f"          erhalten: {got}")
    report = OUT / "shaping-report.txt"
    with report.open("w", encoding="utf-8") as f:
        f.write(f"{total - len(failures)} von {total} bestanden\n")
        for text, feats, expected, got in failures:
            f.write(f"\n{text!r} [{label_features(feats)}]\n  erwartet: {expected}\n  erhalten: {got}\n")
    return not failures


# ---------------------------------------------------------------
# 2a. HTML
# ---------------------------------------------------------------

def make_html(font_file, version):
    mime = "font/woff2" if font_file.suffix == ".woff2" else "font/otf"
    fmt = "woff2" if font_file.suffix == ".woff2" else "opentype"
    data = base64.b64encode(font_file.read_bytes()).decode("ascii")
    checkboxes = "\n".join(
        f'<label><input type="checkbox" data-feat="{f}"{" checked" if f in ("liga", "calt") else ""}> {f}</label>'
        for f in INTERACTIVE)
    blocks = []
    for label, feats in COMBOS:
        rows = "\n".join(
            f'<div class="row"><div class="cap">{html.escape(t)}</div>'
            f'<div class="hm" style="font-feature-settings: {html.escape(css_features(feats))}">{html.escape(s)}</div></div>'
            for t, s in SAMPLES)
        blocks.append(f'<section><h2>{html.escape(label)}</h2>'
                      f'<code>font-feature-settings: {html.escape(css_features(feats))}</code>\n{rows}</section>')
    default_text = "\n".join(s for _, s in SAMPLES)
    page = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heldenlied Minuskel – Featuretest</title>
<style>
@font-face {{
  font-family: "HM Test";
  src: url(data:{mime};base64,{data}) format("{fmt}");
}}
:root {{ --fg: #222; --bg: #fdfbf6; --muted: #777; --line: #ddd; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --fg: #eee; --bg: #1d1c1a; --muted: #999; --line: #444; }}
}}
body {{ font-family: system-ui, sans-serif; color: var(--fg); background: var(--bg);
       max-width: 70rem; margin: 0 auto; padding: 1.5rem; }}
.hm {{ font-family: "HM Test", monospace; font-size: 1.8rem; line-height: 1.4; }}
.cap {{ color: var(--muted); font-size: .8rem; margin-top: .6rem; }}
section {{ border-top: 1px solid var(--line); margin-top: 2rem; padding-top: .5rem; }}
code {{ color: var(--muted); }}
#controls label {{ margin-right: 1rem; white-space: nowrap; }}
textarea {{ width: 100%; min-height: 6rem; font-size: 1rem; box-sizing: border-box; }}
#live {{ white-space: pre-wrap; border: 1px solid var(--line); padding: .5rem; margin-top: .5rem; }}
</style>
</head>
<body>
<h1>Heldenlied Minuskel – Featuretest</h1>
<p>Font: <code>{html.escape(font_file.name)}</code>, {html.escape(version)} (eingebettet, unabhängig von installierten Schriften)</p>

<section>
<h2>Interaktiv</h2>
<div id="controls">{checkboxes}</div>
<p><code id="css"></code></p>
<textarea id="input">{html.escape(default_text)}</textarea>
<div id="live" class="hm"></div>
</section>

{"".join(blocks)}

<script>
const boxes = document.querySelectorAll("[data-feat]");
const input = document.getElementById("input");
const live = document.getElementById("live");
const css = document.getElementById("css");
function update() {{
  const parts = [...boxes].map(b => `"${{b.dataset.feat}}" ${{b.checked ? 1 : 0}}`);
  const value = parts.join(", ");
  live.style.fontFeatureSettings = value;
  css.textContent = "font-feature-settings: " + value;
  live.textContent = input.value;
}}
boxes.forEach(b => b.addEventListener("change", update));
input.addEventListener("input", update);
update();
</script>
</body>
</html>
"""
    (OUT / "test.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------
# 2b. LibreOffice Writer (Flat ODT)
# ---------------------------------------------------------------

def make_fodt(version):
    faces, styles, body = [], [], []
    faces.append('<style:font-face style:name="Label" svg:font-family="\'Liberation Sans\'"/>')
    for i, (label, feats) in enumerate(COMBOS):
        name = xml_escape(lo_fontname(feats), {"'": "&apos;"})
        faces.append(f'<style:font-face style:name="HM{i}" svg:font-family="&apos;{name}&apos;"/>')
        styles.append(f'<style:style style:name="HM{i}" style:family="paragraph">'
                      f'<style:paragraph-properties fo:margin-bottom="0.15cm"/>'
                      f'<style:text-properties style:font-name="HM{i}" fo:font-size="15pt"/></style:style>')
        body.append(f'<text:h text:style-name="H" text:outline-level="1">{xml_escape(label)}</text:h>')
        body.append(f'<text:p text:style-name="Code">Schriftname: {xml_escape(lo_fontname(feats))}</text:p>')
        for cap, sample in SAMPLES:
            body.append(f'<text:p text:style-name="Cap">{xml_escape(cap)}</text:p>')
            body.append(f'<text:p text:style-name="HM{i}">{xml_escape(sample)}</text:p>')
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">
<office:font-face-decls>
{chr(10).join(faces)}
</office:font-face-decls>
<office:automatic-styles>
<style:style style:name="H" style:family="paragraph">
 <style:paragraph-properties fo:margin-top="0.6cm" fo:margin-bottom="0.1cm" fo:break-before="auto"/>
 <style:text-properties style:font-name="Label" fo:font-size="13pt" fo:font-weight="bold"/></style:style>
<style:style style:name="Code" style:family="paragraph">
 <style:text-properties style:font-name="Label" fo:font-size="9pt" fo:color="#666666"/></style:style>
<style:style style:name="Cap" style:family="paragraph">
 <style:paragraph-properties fo:margin-top="0.2cm"/>
 <style:text-properties style:font-name="Label" fo:font-size="8pt" fo:color="#888888"/></style:style>
{chr(10).join(styles)}
</office:automatic-styles>
<office:body><office:text>
<text:h text:style-name="H" text:outline-level="1">Heldenlied Minuskel – Featuretest</text:h>
<text:p text:style-name="Code">Erwartete Version: {xml_escape(version)}. Writer nutzt die installierte Schrift: vorher die alte Version deinstallieren, die neue installieren und LibreOffice komplett neu starten.</text:p>
{chr(10).join(body)}
</office:text></office:body>
</office:document>
"""
    (OUT / "test.fodt").write_text(doc, encoding="utf-8")


# ---------------------------------------------------------------
# 2c. LaTeX
# ---------------------------------------------------------------

def make_tex(otf, version):
    shutil.copy2(otf, OUT / otf.name)          # Pfad ohne Leerzeichen für fontspec
    parts = []
    for label, feats in COMBOS:
        opts = tex_features(feats)
        parts.append(f"\\section*{{{tex_escape(label)}}}")
        parts.append(f"\\hmcode{{{tex_escape(opts or 'keine zusätzlichen Features')}}}\n")
        for cap, sample in SAMPLES:
            parts.append(f"\\hmcap{{{tex_escape(cap)}}}\n")
            add = f"\\addfontfeatures{{{opts}}}" if opts else ""
            parts.append(f"{{\\hm{add} {tex_escape(sample)}\\par}}\n")
    doc = f"""% Automatisch erzeugt von tests/run_tests.py – nicht von Hand bearbeiten
\\documentclass[a4paper,10pt]{{article}}
\\usepackage[margin=2cm]{{geometry}}
\\usepackage{{fontspec}}
\\usepackage{{iftex}}
\\ifLuaTeX\\defaultfontfeatures{{Renderer=HarfBuzz}}\\fi
\\newfontfamily\\hm{{{otf.name}}}[Path=./, Scale=1.6]
\\newcommand\\hmcode[1]{{{{\\small\\ttfamily #1}}}}
\\newcommand\\hmcap[1]{{\\par\\medskip{{\\footnotesize\\sffamily #1}}\\par}}
\\setlength\\parindent{{0pt}}
\\begin{{document}}
{{\\Large\\bfseries Heldenlied Minuskel -- Featuretest}}\\par
\\hmcode{{{tex_escape(otf.name)}, {tex_escape(version)}}}
{chr(10).join(parts)}
\\end{{document}}
"""
    (OUT / "test.tex").write_text(doc, encoding="utf-8")


def build_pdf(engine):
    exe = shutil.which(engine)
    if not exe:
        print(f"! {engine} nicht gefunden, PDF wird nicht erzeugt.")
        return False
    r = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", "test.tex"],
                       cwd=OUT, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"! {engine} ist fehlgeschlagen, Details in tests/output/test.log")
        return False
    print("  tests/output/test.pdf")
    return True


# ---------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--font", type=Path, default=DEFAULT_OTF, help="zu testender OTF")
    p.add_argument("--no-pdf", action="store_true", help="LaTeX-Lauf überspringen")
    p.add_argument("--engine", default="xelatex", choices=["xelatex", "lualatex"])
    args = p.parse_args()

    otf = args.font.resolve()
    if not otf.exists():
        sys.exit(f"Font nicht gefunden: {otf} – vorher python scripts/build.py ausführen.")
    OUT.mkdir(exist_ok=True)
    version = TTFont(otf)["name"].getDebugName(5) or "unbekannt"
    print(f"Teste {otf.name} ({version})")

    ok = check_shaping(otf)

    webfont = DEFAULT_WOFF2 if (args.font == DEFAULT_OTF and DEFAULT_WOFF2.exists()) else otf
    make_html(webfont, version)
    make_fodt(version)
    make_tex(otf, version)
    print("Testdokumente:\n  tests/output/test.html\n  tests/output/test.fodt\n  tests/output/test.tex")
    if not args.no_pdf:
        build_pdf(args.engine)

    if ok is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
