# Speichern in der Souls Cave sauber sperren (v146a, Max: "Spielstand speichern geht nicht").
# Bisher: soe_speicher ueberspringt in der Hoehle (SRAM 30:7002 != 0) nur das eigentliche Speichern (8D:AF89).
# Das Spiel hatte aber VORHER schon den Platz als belegt markiert ($0B39 |= Bit, 8D:D130) und "letzter Platz"
# geschrieben (30:6001, 8D:D125) -> leerer Platz mit "LV 0 KP 0" und die Meldung "Spiel gespeichert!".
# Jetzt: in der Hoehle beides auslassen und statt "Spiel gespeichert!" (8D:D43E) einen Hinweis zeigen.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
CODE, TEXT = 0xF1B700, 0xF1B780
AKT = [0xAF,0x02,0x70,0x30, 0x29,0xFF,0x00]                       # LDA $30:7002 ; AND #$00FF
code, lab = assemble(CODE, [
  # ---- 8D:D125 (M 8 Bit, A = Platz): STA $30:6001 nur ausserhalb der Hoehle
  'sl:', [0x08, 0x48, 0xC2,0x20], AKT, [0xE2,0x20], ('bra8',0xD0,'sl_n'),
  [0x68, 0x8F,0x01,0x60,0x30, 0x28, 0x6B],
  'sl_n:', [0x68, 0x28, 0x6B],
  # ---- 8D:D130 (M 16 Bit, A = Platz-Bit): $0B39 |= A nur ausserhalb der Hoehle
  'mk:', [0x48], AKT, ('bra8',0xD0,'mk_n'),
  [0x68, 0x0F,0x39,0x0B,0x7E, 0x8F,0x39,0x0B,0x7E, 0x6B],
  'mk_n:', [0x68, 0x6B],
  # ---- 8D:D43E (M 16 Bit): Titeltext [$22]/$24 = "Spiel gespeichert!" bzw. Hinweis in der Hoehle
  'tx:', AKT, ('bra8',0xD0,'tx_h'),
  [0xA9,0x77,0x23, 0x85,0x22, 0xA9,0xC5,0x00, 0x85,0x24, 0x6B],
  'tx_h:', [0xA9,TEXT&0xFF,(TEXT>>8)&0xFF, 0x85,0x22, 0xA9,TEXT>>16,0x00, 0x85,0x24, 0x6B],
])
assert CODE + len(code) <= TEXT
txt = b'Kein Speichern in der Cave!\x00'
for a, blob in ((CODE, code), (TEXT, txt)):
    o = at(a); assert all(b == 0xFF for b in r[o:o+len(blob)]), "Platz belegt %X" % a; r[o:o+len(blob)] = blob
def jsl(lbl): a = lab[lbl]; return bytes([0x22, a&0xFF, (a>>8)&0xFF, a>>16])
def setze(adr, alt, neu):
    o = at(adr); assert bytes(r[o:o+len(alt)]) == bytes(alt), (hex(adr), bytes(r[o:o+len(alt)]).hex()); r[o:o+len(neu)] = neu
setze(0x8DD125, [0x8F,0x01,0x60,0x30], jsl('sl'))
setze(0x8DD130, [0x0D,0x39,0x0B, 0x8D,0x39,0x0B], jsl('mk')+b'\xEA\xEA')
setze(0x8DD43E, [0xA9,0x77,0x23, 0x85,0x22, 0xA9,0xC5,0x00, 0x85,0x24], jsl('tx')+b'\xEA'*6)
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Speicher-Sperre Cave eingebaut")
