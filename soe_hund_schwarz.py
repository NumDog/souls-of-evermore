# Hund schwarz: Die vier Hundeformen haben je eine 16-Farben-Palette in der ROM (auch fuer das Hunde-Symbol unten rechts):
# 0x10AE10 Wolf (Praehistorika), 0x10AE30 Windhund (Antiqua), 0x10AE50 Pudel (Gotica), 0x10AE70 Toaster-Hund (Omnitopia).
# Jede Farbe wird zu dunklem Grau (Helligkeit gestaucht, leicht warm), kraeftiges Rot/Rosa (Zunge, Augen) bleibt.
import sys
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024
PALETTEN = [0x10AE10, 0x10AE30, 0x10AE50, 0x10AE70]
def schwarz(v, rot_behalten=True):
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    mx, mn = max(r,g,b), min(r,g,b)
    if rot_behalten and r == mx and r >= 12 and r - max(g,b) >= 6:          # Rot/Rosa: Zunge, Augen -> bleibt, etwas dunkler
        return (r*3//4) | ((g*3//4) << 5) | ((b*3//4) << 10)
    l = (r*30 + g*59 + b*11) / 100                          # Helligkeit 0..31
    n = 1 + l * 0.32                                        # -> 1..11: schwarz bis dunkelgrau
    rr, gg, bb = round(n*1.05), round(n), round(n*0.95)
    return min(rr,31) | (min(gg,31) << 5) | (min(bb,31) << 10)
for p in PALETTEN:
    o = H + p
    for i in range(1, 16):                                  # Farbe 0 = durchsichtig
        v = int.from_bytes(d[o+i*2:o+i*2+2], 'little')
        d[o+i*2:o+i*2+2] = schwarz(v, p != 0x10AE50).to_bytes(2, 'little')   # Pudel: Fell ist rosa -> alles dunkel
r = memoryview(d)[H:]; h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Hund schwarz eingefaerbt (%d Paletten)" % len(PALETTEN))
