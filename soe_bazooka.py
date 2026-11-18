# Bazooka +N (Max v127): Der Bazooka-Schaden kommt nur von der Munition. Beim Neuberechnen der Werte (8F:844B, Zweig fuer
# Waffe 1A) liest 8F:846C LDA $C40000,X den Angriff der Munitions-Vorlage (Donnergranaten 200 / Plasmaraketen 350 /
# Cyberbomben 800) und 8F:8470 schreibt ihn nach $0A3F. Hier: Angriff * (1 + N/2) wie bei allen Waffen (N = Bazooka-Plus,
# WGET aus soe_waffe99 mit A = 0x1A), hoechstens 8000 (danach rechnet das Spiel noch Aufladung x2/x4 vorzeichenbehaftet).
# M/X = 16 Bit, X = Zeiger auf die Munitions-Vorlage. Wirkt nach der naechsten Neuberechnung (Ausruesten/Sorte wechseln/Raum).
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
BAZ, WGET, KAPPE = 0xF1B200, 0xF1B000, 8000
code, _ = assemble(BAZ, [
  [0xBF,0x00,0x00,0xC4, 0xDA, 0x5A, 0x48],                    # LDA $C40000,X ; PHX PHY PHA (1,S = Kraft)
  [0xA9,0x1A,0x00, 0x22,WGET&0xFF,(WGET>>8)&0xFF,WGET>>16], ('bra8',0xF0,'fertig'),
  [0xAA, 0xA3,0x01, 0x4A, 0x48, 0xA3,0x03],                  # X = N ; 1,S = Kraft/2 ; A = Kraft
  'schleife:', [0x18, 0x63,0x01], ('bra8',0xB0,'kappe'), [0xC9,KAPPE&0xFF,KAPPE>>8], ('bra8',0xB0,'kappe'),
  [0xCA], ('bra8',0xD0,'schleife'), [0x83,0x03], ('bra8',0x80,'weg'),
  'kappe:', [0xA9,KAPPE&0xFF,KAPPE>>8, 0x83,0x03],
  'weg:', [0x68],
  'fertig:', [0x68, 0x7A, 0xFA, 0x6B]])
o = at(BAZ); assert all(b == 0xFF for b in r[o:o+len(code)]), "Platz belegt"; r[o:o+len(code)] = code
o = at(0x8F846C); assert bytes(r[o:o+4]) == bytes([0xBF,0x00,0x00,0xC4]), bytes(r[o:o+4]).hex()
r[o:o+4] = bytes([0x22, BAZ&0xFF, (BAZ>>8)&0xFF, BAZ>>16])
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Bazooka +N eingebaut")
