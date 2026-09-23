from fontTools.ttLib import TTFont
p = "HeldenliedMinuskel-Regular.otf"
f = TTFont(p)
f["name"].removeNames(platformID=1)      # Mac-Namenseinträge entfernen
f["OS/2"].recalcAvgCharWidth(f)          # xAvgCharWidth neu berechnen
for t in ("DSIG", "FFTM"):               # Altlasten entfernen, falls vorhanden
    if t in f: del f[t]
f.save(p)