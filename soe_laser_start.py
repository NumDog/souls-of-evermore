# Startwaffe: Schwer immer Laserschwert (08). Normal: Chaos Laserschwert, Gebiet/Aehnlich Drachentoeter (04), sonst Knochenknueppel (02). Das Spiel vergibt die Startwaffe beim Spielbeginn (auch nach dem Tod ohne
# Spielstand, ohne Vorspann) in 8F:8093 (LDA #$0002 ; STA $2441 = Knochenknueppel). Im Chaos stattdessen 08 = Laserschwert.
# Die Hund-Szene (soe_zufall_live.py) gibt dann nichts doppelt, sondern nur den Spruch.
# Diese Vergabe laeuft bei jedem Start/Neustart -> vorher den Lade-Merker (Bit7 von $2256) setzen, damit sie nie als +1 zaehlt.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
CODE = 0xF03A00
code,_ = assemble(CODE, [
  # Startwaffe: Chaos 08 Laserschwert; Gebiet/Aehnlich 04 Drachentoeter; Original: Schwer 08, Normal 02
  [0xAF,0x90,0x7E,0x30, 0x29,0x18,0x00, 0xC9,0x10,0x00], ('bra8',0xD0,'nicht_chaos'),
  [0xA9,0x08,0x00], ('bra8',0x80,'setzen'),
  'nicht_chaos:', [0xC9,0x00,0x00], ('bra8',0xF0,'original'),
  [0xA9,0x04,0x00], ('bra8',0x80,'setzen'),
  'original:', [0xAF,0x90,0x7E,0x30, 0x29,0x01,0x00], ('bra8',0xD0,'knochen'),
  [0xA9,0x08,0x00], ('bra8',0x80,'setzen'),
  'knochen:', [0xA9,0x02,0x00],
  'setzen:', [0x8F,0x41,0x24,0x7E, 0x6B],
  # Nach der Vergabe (8F:8099 JSL 8F:91E6): Waffe-+N-Zaehler 2250-2256 leeren -> Startwaffe nie mit Plus,
  # auch nicht nach Tod/Neustart (Zaehler lagen noch im Speicher -> +5, +6, +7 ...). 2257 (NG+-Zyklus) bleibt.
  'nachher:', [0x22,0xE6,0x91,0x8F, 0x08, 0xC2,0x20, 0x48, 0xA9,0x00,0x00,
               0x8F,0x50,0x22,0x7E, 0x8F,0x52,0x22,0x7E, 0x8F,0x54,0x22,0x7E,
               0xE2,0x20, 0x8F,0x56,0x22,0x7E, 0xC2,0x20, 0x22,0x40,0xB1,0xF1, 0x68, 0x28, 0x6B],   # v122: + WCLR
])
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]); r[o:o+len(code)] = code
o = at(0x8F8093); assert bytes(r[o:o+6]) == bytes([0xA9,0x02,0x00,0x8D,0x41,0x24]), bytes(r[o:o+6]).hex()
r[o:o+6] = bytes([0x22, CODE&0xFF, (CODE>>8)&0xFF, CODE>>16, 0xEA, 0xEA])
NACH = CODE + code.index(bytes([0x22,0xE6,0x91,0x8F]))
o = at(0x8F8099); assert bytes(r[o:o+4]) == bytes([0x22,0xE6,0x91,0x8F]), bytes(r[o:o+4]).hex()
r[o:o+4] = bytes([0x22, NACH&0xFF, (NACH>>8)&0xFF, NACH>>16])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Laserschwert als Startwaffe im Chaos eingebaut, %d Bytes" % len(code))
