# ENDE-Bildschirm (Karte 0x63, Skript 93:D30x laeuft): unter „ENDE“ Portraet (32x32, 3 Graustufen) + drei Zeilen Text.
# Der Bildschirm ist eine BG3-Zeichenflaeche (2bpp): Spalte c / Zeile r -> Kachel 0x180 + c*20 + r (spaltenweise),
# sichtbar ab Bildzeile 4 / Spalte 4. Wir malen die Zeilen 13..17 der Flaeche per DMA (Kanal 7) in der Bildpause,
# aufgerufen aus dem NMI-Hook von soe_titel.py (JSL F0:8000), alle 32 Bilder erneut (falls das Spiel neu zeichnet).
import sys, os, json; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
import importlib.util
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
hier = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('s57', os.path.join(hier,'tools','schrift5x7.py')); s57 = importlib.util.module_from_spec(sp); sp.loader.exec_module(s57)
import soe_daten as D
PORT = json.load(open(os.path.join(hier,'tools','portrait48.json')))   # 48x48, Werte 0..3 (Graustufen, Palette 7)
CODE, DAT = 0xF08000, 0xF08100
R0, NR = 12, 7                                    # Flaechen-Zeilen 12..18 (56 Pixel hoch)
W = 24*8; Hh = NR*8
bild = [[0]*W for _ in range(Hh)]
# Portraet links (Flaechen-Spalte 2 -> x 16)
WEISS = 1                                          # BG3-Palette 0: 1 = weiss, 2 = schwarz, 3 = blau
PX0, PY0, PN = 8, 8, 48                            # Portraet: x 8..55, y 8..55 (Flaechen-Spalten 1..6, Zeilen 13..18)
for y in range(PN):
    for x in range(PN): bild[PY0+y][PX0+x] = PORT[y][x]
def zeile(z, X0, Y0):
    for ci, ch in enumerate(z):
        g = s57.G.get(ch, s57.G[' '])
        for y in range(7):
            for x in range(5):
                if g[y][x] == '1' and X0 + ci*6 + x < W: bild[Y0+y][X0+ci*6+x] = WEISS
oben = "NEW GAME+ FREIGESCHALTET"
zeile(oben, (W - len(oben)*6)//2, 0)
for zi, z in enumerate(["SOULS OF EVERMORE", "REMAKE 2026", D.NAME.upper()]):
    zeile(z, 66, PY0 + 12 + zi*11)
# Karten-Eintraege der Portraet-Kacheln auf Palette 7 (BG3-Karte Wort 0x800, Flaeche ab Bildzeile/-spalte 4)
PKARTE = b''
for c in range(PX0//8, (PX0+PN)//8):
    for rr in range(PY0//8, (PY0+PN)//8):
        t = 0x180 + c*20 + R0 + rr
        PKARTE += (0x800 + (R0+rr+4)*32 + c+4).to_bytes(2,'little') + (0x2000 | 7<<10 | t).to_bytes(2,'little')
PFARBEN = [0x0000, 0x2529, 0x4A52, 0x739C]           # Palette 7 = CGRAM 28..31: schwarz, dunkel-, mittel-, hellgrau
for zi, z in enumerate([]):
    for ci, ch in enumerate(z):
        g = s57.G.get(ch, s57.G[' '])
        for y in range(7):
            for x in range(5):
                if g[y][x] == '1':
                    X, Y = 56 + ci*6 + x, 6 + zi*11 + y
                    if X < W: bild[Y][X] = 3
def kachel(ox, oy):
    t = bytearray(16)
    for y in range(8):
        for x in range(8):
            v = bild[oy+y][ox+x]; s = 7-x
            if v & 1: t[2*y] |= 1<<s
            if v & 2: t[2*y+1] |= 1<<s
    return bytes(t)
SPALTEN = [c for c in range(24) if any(bild[y][x] for y in range(Hh) for x in range(c*8, c*8+8))]
blob = b''; tab = b''
for c in SPALTEN:
    src = DAT + len(blob)
    for rr in range(NR): blob += kachel(c*8, rr*8)
    vword = (0x180 + c*20 + R0) * 8
    tab += vword.to_bytes(2,'little') + (src & 0xFFFF).to_bytes(2,'little')
TAB = DAT + len(blob)
PK = TAB + len(tab)
ZAEHL = 0x7EE324
code, lab = assemble(CODE, [
  [0x08, 0xC2,0x30, 0x48, 0xDA],
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x63,0x00], ('bra8',0xD0,'aus0'),
  [0xAF,0x28,0x2F,0x7E], ('bra8',0xF0,'aus0'), [0xAA],                    # erster aktiver Faden
  [0xBF,0x02,0x00,0x7E, 0x29,0xFF,0x00, 0xC9,0x93,0x00], ('bra8',0xD0,'aus0'),
  [0xBF,0x00,0x00,0x7E, 0xC9,0x00,0xD3], ('bra8',0x90,'aus0'), [0xC9,0x30,0xD3], ('bra8',0xB0,'aus0'),
  [0xAF,ZAEHL&0xFF,(ZAEHL>>8)&0xFF,ZAEHL>>16, 0x1A, 0x8F,ZAEHL&0xFF,(ZAEHL>>8)&0xFF,ZAEHL>>16, 0x29,0x1F,0x00], ('bra8',0xD0,'aus0'),
  ('bra8',0x80,'weiter'), 'aus0:', ('jmp','aus'), 'weiter:',
  [0xE2,0x20, 0xA9,0x80, 0x8F,0x15,0x21,0x00, 0xA9,0x01, 0x8F,0x70,0x43,0x00, 0xA9,0x18, 0x8F,0x71,0x43,0x00, 0xA9,0xF0, 0x8F,0x74,0x43,0x00, 0xC2,0x20],
  [0xA2,0x00,0x00],
  'l:', [0xBF,TAB&0xFF,(TAB>>8)&0xFF,TAB>>16, 0x8F,0x16,0x21,0x00],
  [0xBF,(TAB+2)&0xFF,((TAB+2)>>8)&0xFF,TAB>>16, 0x8F,0x72,0x43,0x00],
  [0xA9,NR*16,0x00, 0x8F,0x75,0x43,0x00],
  [0xE2,0x20, 0xA9,0x80, 0x8F,0x0B,0x42,0x00, 0xC2,0x20],
  [0xE8,0xE8,0xE8,0xE8, 0xE0,len(tab)&0xFF,len(tab)>>8], ('bra8',0x90,'l'),
  [0xA2,0x00,0x00],                                                      # Portraet-Kacheln -> Palette 7
  'p:', [0xBF,PK&0xFF,(PK>>8)&0xFF,PK>>16, 0x8F,0x16,0x21,0x00, 0xBF,(PK+2)&0xFF,((PK+2)>>8)&0xFF,PK>>16, 0x8F,0x18,0x21,0x00],
  [0xE8,0xE8,0xE8,0xE8, 0xE0,len(PKARTE)&0xFF,len(PKARTE)>>8], ('bra8',0x90,'p'),
  [0xE2,0x20, 0xA9,28, 0x8F,0x21,0x21,0x00]] + [[0xA9,f&0xFF, 0x8F,0x22,0x21,0x00, 0xA9,f>>8, 0x8F,0x22,0x21,0x00] for f in PFARBEN] + [[0xC2,0x20],
  'aus:', [0xFA, 0x68, 0x28, 0x6B],
])
assert CODE + len(code) <= DAT and PK + len(PKARTE) <= 0xF08C00, hex(PK+len(PKARTE))
for adr, c in ((CODE, code), (DAT, blob + tab + PKARTE)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("ENDE-Bild eingebaut: %d Spalten" % len(SPALTEN))
