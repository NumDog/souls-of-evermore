# Bazooka-Munition beim Haendler (Max v127, Haendler-Zufall). soe_haendler.py waehlt fuer den Platz mit Verbrauchsgut 7
# eine Munitionssorte (Ware 70/71/72 in SRAM 30:7E84, Preis aus PTAB) und gibt dem Spiel 7. Hier die restlichen Stellen:
#  1. 8C:E6F6 LDA $8CE712,X (8 Bit, Ring-Byte der Ware): bei Ware 70..72 Ring-Byte 8..10.
#  2. 8E:9C07 ASL ; TAX ; LDA $C50114,X (Ring-Byte -> Ring-ID): eigene Tabelle mit 11 Eintraegen (8 Original + 42/44/46).
#  3. 8E:8E56 LDA $8E0006,X (Kauf, X = Beschreibung): Munition (8E:824C/8254/825C) -> Index | 0x80 in $12.
#  4. 8E:8E94 Kauf: Verbrauch wie Original (Zaehler 2315+X, hoechstens 6), Munition +10 auf 2345+Index/2 (nur unter 90).
#  5. 8E:A9ED LDA $8E0006,X (Anzeige „Du hast X“, danach LDA $7E2315,X): Munition -> Index/2 + 0x30 (= 2345 + Index/2).
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
CODE = 0xF1B300
TAB = CODE + 0x1C0
SCR = 0x307E84
MUN = [0x824C, 0x8254, 0x825C]
tab = bytes(r[at(0xC50114):at(0xC50114)+16]) + b''.join(i.to_bytes(2,'little') for i in (0x42,0x44,0x46))
def ist_mun(lbl):   # X = Beschreibung -> BEQ lbl, wenn Munition
    out = []
    for m in MUN: out += [[0xE0,m&0xFF,m>>8], ('bra8',0xF0,lbl)]
    return out
code, lab = assemble(CODE, [
  # 1. Ring-Byte (A 8 Bit)
  'ring:', [0xBF,0x12,0xE7,0x8C, 0x48, 0xAF]+L(SCR)+[0xC9,70], ('bra8',0x90,'r_n'), [0xC9,73], ('bra8',0xB0,'r_n'),
  [0x68, 0xAF]+L(SCR)+[0x38, 0xE9,62, 0x6B],
  'r_n:', [0x68, 0x6B],
  # 2. Ring-Byte -> Ring-ID (A 16 Bit)
  'rid:', [0x0A, 0xAA, 0xBF]+L(TAB)+[0x6B],
  # 3. Kauf: Beschreibung +6, Munition markieren
  'mark:', [0xBF,0x06,0x00,0x8E], *ist_mun('mk'), [0x6B], 'mk:', [0x09,0x80,0x00, 0x6B],
  # 4. Kauf ausfuehren: C = voll
  'kauf:', [0xA5,0x12, 0x89,0x80,0x00], ('bra8',0xD0,'k_mun'),
  [0xAA, 0xE2,0x20, 0xBF,0x15,0x23,0x7E, 0x1A, 0xC9,0x07], ('bra8',0x10,'k_voll'), [0x9F,0x15,0x23,0x7E, 0xC2,0x20, 0x18, 0x6B],
  'k_mun:', [0x29,0x7F,0x00, 0x4A, 0xAA, 0xE2,0x20, 0xBF,0x45,0x23,0x7E, 0xC9,90], ('bra8',0xB0,'k_voll'),
  [0x18, 0x69,10, 0x9F,0x45,0x23,0x7E, 0xC2,0x20, 0x18, 0x6B],
  'k_voll:', [0xC2,0x20, 0x38, 0x6B],
  # 5. Anzeige „Du hast“
  'zeig:', [0xBF,0x06,0x00,0x8E], *ist_mun('zm'), [0x6B], 'zm:', [0x4A, 0x18, 0x69,0x30,0x00, 0x6B],
])
assert len(code) <= 0x1C0
for adr, c in ((CODE, code), (TAB, tab)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
def jsl(lbl): a = lab[lbl]; return [0x22, a&0xFF, (a>>8)&0xFF, a>>16]
for site, alt, neu in (
    (0x8CE6F6, [0xBF,0x12,0xE7,0x8C], jsl('ring')),
    (0x8E9C07, [0x0A,0xAA,0xBF,0x14,0x01,0xC5], jsl('rid')+[0xEA,0xEA]),
    (0x8E8E56, [0xBF,0x06,0x00,0x8E], jsl('mark')),
    (0x8E8E94, [0xA6,0x12,0xE2,0x20,0xBD,0x15,0x23,0x1A,0xC9,0x07,0x30,0x0C], jsl('kauf')+[0x90,0x15, 0x80,0x04, 0xEA,0xEA,0xEA,0xEA]),
    (0x8EA9ED, [0xBF,0x06,0x00,0x8E], jsl('zeig'))):
    o = at(site); assert list(r[o:o+len(alt)]) == alt, (hex(site), bytes(r[o:o+len(alt)]).hex()); r[o:o+len(neu)] = bytes(neu)
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Munition beim Haendler eingebaut")
