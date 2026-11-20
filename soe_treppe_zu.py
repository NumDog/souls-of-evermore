# Treppe optisch zu (v148, Max: "Treppe visuell zumachen, mit den Bodenkacheln"). Hook 90:9270 (Kartenaufbau fertig, Bild noch aus;
# Kette: vorne, ruft erst den bisherigen Hook). In der Cave (AKT 30:7002) auf dem Schachbrett 5E, solange die Treppe gesperrt ist
# (SIEGEL 30:70C0 Bits 1-4 nicht alle gesetzt): die Zellen des Treppenlochs (Zeilen 34-40, Spalten 7-14 der 22 Zellen breiten
# Karte) zeigen auf Schachbrett-Boden: Kombi 139 (heller Streifen: Spalten 10/11, Zeilen 38/39) bzw. 140 (dunkel).
# Zellzeiger in 7F:0000 + 2*(y*22+x) = $0FAA + 8*Kombi (Mesen-Dump v148a). Beim naechsten Laden von 5E ist die Treppe wieder da.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
def w(v): return [v&0xFF,(v>>8)&0xFF]
CODE = 0xF90000
AKT, SIEGEL = 0x307002, 0x3070C0
BREITE = 22
ZELLEN = [(y, x) for y in range(34, 40) for x in range(7, 15)] + [(40, 8), (40, 13)]
o9 = at(0x909270); assert r[o9] == 0x22; vorher = list(r[o9+1:o9+4])
setz = []
for y, x in ZELLEN:
    hell = x in (10, 11) or y in (38, 39)
    setz += [0x98 if hell else 0x8A, 0x8F] + L(0x7F0000 + 2*(y*BREITE + x))      # TYA/TXA ; STA 7F:Zelle
code, lab = assemble(CODE, [
  'tz:', [0x22]+vorher,
  [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A],
  [0xAF]+L(AKT)+[0x29,0xFF,0x00], ('bra8',0xF0,'tz_n'),
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x5E,0x00], ('bra8',0xD0,'tz_n'),
  [0xAF]+L(SIEGEL)+[0x29,0x1E,0x00, 0xC9,0x1E,0x00], ('bra8',0xD0,'tz_ja'),
  'tz_n:', ('jmp','tz_r'), 'tz_ja:',
  [0xAF,0xAA,0x0F,0x7E, 0x18, 0x69]+w(8*140)+[0xAA],                      # X = Zeiger dunkler Boden
  [0xAF,0xAA,0x0F,0x7E, 0x18, 0x69]+w(8*139)+[0xA8],                      # Y = Zeiger heller Boden
  setz,
  'tz_r:', [0x7A, 0xFA, 0x68, 0x28, 0x6B],
])
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), 'F9 belegt'; r[o:o+len(code)] = code
r[o9:o9+4] = bytes([0x22]+L(lab['tz']))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Treppe optisch zu, %d Bytes" % len(code))
