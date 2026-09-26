"""
Testdaten für Heldenlied Minuskel.

Hier werden Texte, Feature-Kombinationen und erwartete Ergebnisse
gepflegt. run_tests.py erzeugt daraus die Testdokumente (HTML, Writer,
LaTeX) und prüft die erwarteten Glyphenfolgen automatisch.
"""

# Testtexte: (Überschrift, Text). Jeder Text zielt auf bestimmte Features.
SAMPLES = [
    ("Buchstaben (v, w, j, i, Umlaute, Satzzeichen)",
     "Vier weise Jäger ziehen über Wälder, Äcker und Öde; wohin? Zur Burg: jetzt."),
    ("s, ss, ß und langes s",
     "Wasser, Fluss, dass, daß, Straße, Aussage, Ausstellung, Glasbläser, ſ"),
    ("f-Varianten und Ligaturen",
     "hoffen, Schiff, Schiffbau, Kopfhörer, Seeflug, höflich, Fläche, fährt, Föhn, fünf, Mittag, Stunde, Tisch, Gratis"),
    ("Oberlängen (ss01)",
     "Bald, Dach, Hof, Kalk, Laub, Wechsler – bdhkl BDHKL"),
    ("Titulus",
     "a\u0304 e\u0304 i\u0304 o\u0304 u\u0304 m\u0304 n\u0304 p\u0304 q\u0304 – ā ē ī ō ū"),
    ("Zahlen",
     "1, 12, 49, 99, 100, 872, 999, 1066, 1957, 2026, 3999 – 4711, 12345, 0 – 3,5 und 12:30"),
    ("Datum und Punkt hinter Zahlen",
     "Kapitel 12. Am 26.9.872 und am 1.1.1000 geschah es."),
]

# Feature-Kombinationen: (Bezeichnung, {Feature: 0/1}).
# Nicht genannte Features behalten ihren Standard (liga, calt usw. an).
COMBOS = [
    ("Standard", {}),
    ("Ohne liga und calt", {"liga": 0, "calt": 0}),
    ("ss01 Hohe Oberlängen", {"ss01": 1}),
    ("ss05 Römische Zahlen", {"ss05": 1}),
    ("ss07 Spätmittelalterliche Ziffern", {"ss07": 1}),
    ("ss05 + ss07 (ss07 hat Vorrang)", {"ss05": 1, "ss07": 1}),
    ("hist", {"hist": 1}),
    ("hist + ss01", {"hist": 1, "ss01": 1}),
    ("hist + ss07", {"hist": 1, "ss07": 1}),
    ("hist ohne liga", {"hist": 1, "liga": 0}),
    ("ss20", {"ss20": 1}),
    ("ss20 + ss01 + ss07", {"ss20": 1, "ss01": 1, "ss07": 1}),
]

# Erwartete Glyphenfolgen: (Text, Features, erwartete Glyphnamen).
# roman.null ist die unsichtbare Markierung innerhalb römischer Zahlen.
EXPECTED = [
    ("Wasser", {}, "W a s s e r"),
    ("Wasser", {"hist": 1}, "w.hist a longs_longs e r"),
    ("daß", {}, "d a germandbls"),
    ("dass", {"hist": 1}, "d a germandbls.hist"),
    ("daß", {"hist": 1}, "d a germandbls.hist"),
    ("Ausstellung", {"hist": 1}, "A u longs_longs t e l l u n g"),
    ("Aussage", {"hist": 1}, "A u longs_longs a g e"),
    ("vier", {}, "v i e r"),
    ("vier", {"hist": 1}, "v.hist i.hist e r"),
    ("Jäger", {"hist": 1}, "j.hist adieresis.hist g e r"),
    ("fährt", {}, "f_adieresis h r t"),
    ("fährt", {"hist": 1}, "f_adieresis.hist h r t"),
    ("fährt", {"liga": 0}, "f adieresis h r t"),
    ("Kopfhörer", {}, "K o p f.asc h odieresis r e r"),
    ("Schiffbau", {}, "S c h i f_f.asc b a u"),
    ("Glasbläser", {"hist": 1}, "G l a longs.asc b l adieresis.hist longs e r"),
    ("Mittag", {}, "M i t_t a g"),
    ("Föhn", {}, "f_odieresis h n"),
    ("Tisch", {}, "t_i s c h"),
    ("höflich", {}, "h odieresis f.asc l i c h"),
    ("höflich", {"ss01": 1}, "h.ss01 odieresis f_l.ss01 i c h.ss01"),
    ("Flug", {"ss01": 1}, "f_l.ss01 u g"),
    ("Wechsler", {"hist": 1}, "w.hist e c h longs.asc l e r"),
    ("Wechsler", {"hist": 1, "ss01": 1}, "w.hist e c h.ss01 longs_l.ss01 e r"),
    ("Stunde", {}, "S t_u n d e"),
    ("bdhkl", {"ss01": 1}, "b.ss01 d.ss01 h.ss01 k.ss01 l.ss01"),
    ("BDHKL", {"ss01": 1}, "B.ss01 D.ss01 H.ss01 K.ss01 L.ss01"),
    # HarfBuzz setzt i + kombinierendes Makron zum vorkomponierten ī zusammen
    ("i\u0304", {}, "imacron"),
    # Ohne vorkomponierte Form: Titulus als Mark über dem Buchstaben
    ("n\u0304", {}, "n uni0304"),
    ("Satz; Frage?", {"hist": 1}, "S a t z semicolon.hist space F r a g e question.hist"),
    ("12", {"ss05": 1}, "periodcentered x roman.null i.hist i.hist periodcentered"),
    ("Kapitel 12.", {"ss05": 1},
     "K a p i t e l space periodcentered x roman.null i.hist i.hist periodcentered"),
    ("26.9.872", {"ss05": 1},
     "periodcentered x x roman.null u i.hist periodcentered u i.hist i.hist i.hist i.hist "
     "periodcentered d c c c roman.null l x x roman.null i.hist i.hist periodcentered"),
    ("1, 2", {"ss05": 1},
     "periodcentered i.hist periodcentered space periodcentered i.hist i.hist periodcentered"),
    ("1000", {"ss05": 1}, "periodcentered m roman.null roman.null roman.null periodcentered"),
    ("2026", {"hist": 1},
     "periodcentered m m roman.null roman.null x x roman.null u i.hist periodcentered"),
    ("2026", {"hist": 1, "ss07": 1}, "two.hist zero.hist two.hist six.hist"),
    ("1957", {"ss07": 1}, "one.hist nine.hist five.hist seven.hist"),
    ("1957", {"ss05": 1, "ss07": 1}, "one.hist nine.hist five.hist seven.hist"),
    ("4711", {"ss05": 1}, "four seven one one"),
    ("4711", {"hist": 1}, "four.hist seven.hist one.hist one.hist"),
    ("3,5", {"ss05": 1}, "three comma five"),
    ("3,5", {"hist": 1}, "three.hist comma.hist five.hist"),
    ("12:30", {"ss05": 1}, "one two colon three zero"),
    ("0", {"ss05": 1}, "zero"),
    ("12345", {"ss20": 1}, "one.hist two.hist three.hist four.hist five.hist"),
    ("2026", {"ss20": 1},
     "periodcentered m m roman.null roman.null x x roman.null u i.hist periodcentered"),
]

# Features für die interaktive HTML-Testseite
INTERACTIVE = ["liga", "calt", "ss01", "ss05", "ss07", "hist", "ss20"]
