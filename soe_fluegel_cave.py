# Fluegel in der Cave = Tod (v146z33, Max: "Fluegel bei der Anwendung im Cave einen toeten, dann fliegt man raus, falls man
# stecken bleibt"). Jedes Bild (Kette F0:4000, vorne): sinkt der Fluegel-Zaehler 7E:2319 (Verbrauchsgut 0x804) in der Cave
# (AKT 30:7002), wird der Cave-Tod-Merker TOD 30:7008 gesetzt (wie soe_hoehle 'tod'). Der Sprung der Fluegel geht durch den
# Tuer-Hook (soe_hoehle 'tuer'): TOD -> raus aus der Cave an den Brunnen, Beute/Flags wie beim Tod zurueck.
# Merker des letzten Zaehlerstands: 7E:EEA8.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
CODE = 0xF8F300
o0 = at(0xF04000); assert r[o0] == 0x22; vorbild = list(r[o0+1:o0+4])
code, lab = assemble(CODE, [
  'fl:', [0x08, 0xC2,0x30, 0x48],
  [0xAF,0x19,0x23,0x7E, 0x29,0xFF,0x00, 0x48],                         # 1,S = Fluegel jetzt
  [0xAF,0x02,0x70,0x30, 0x29,0xFF,0x00], ('bra8',0xF0,'fl_m'),
  [0xA3,0x01, 0xCF,0xA8,0xEE,0x7E], ('bra8',0xB0,'fl_m'),               # nicht weniger -> nur merken
  [0xA9,0x01,0x00, 0x8F,0x08,0x70,0x30],                                # TOD = 1
  'fl_m:', [0x68, 0x8F,0xA8,0xEE,0x7E, 0x68, 0x28, 0x22,0x00,0x04,0xF9, 0x22]+vorbild+[0x6B],   # v150: JSL F9:0400 Testhilfe (ft)
])
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), "Platz belegt"; r[o:o+len(code)] = code
# v150 (Max: Fluegel sollen einen mit 100000 Schaden toeten, BAM, sichtbar): Verbrauchsgut-Handler 8E:8CF9 (LDA C5:00F8,X ; TAX ;
# JSL 91:973E = Effekt starten). In der Cave statt der Fluegel-Wirkung (Typ 0x20): echter Treffer auf den Jungen ueber 8F:C068
# (A = Schaden, Y = Objekt; Anzeige hoechstens 9999, die Zahl 100000 kommt als Meldung FF4 ueber soe_knoten qpl F3:000C).
# Der Tod laeuft wie jeder Cave-Tod (soe_hoehle 'tod' -> raus am Brunnen). Testhilfe: 30:70B6 = 5A -> einmal ausloesen.
CODE2 = 0xF90400
oh = at(0x8E8CF9); assert bytes(r[oh:oh+9]) == bytes.fromhex('bff800c5aa223e9791'), bytes(r[oh:oh+9]).hex()
code2, lab2 = assemble(CODE2, [
  # Testhilfe aus der Bildkette (fest bei F9:0400)
  'ft:', [0x08, 0xC2,0x30, 0x48, 0xAF,0xB6,0x70,0x30, 0x29,0xFF,0x00, 0xC9,0x5A,0x00], ('bra8',0xD0,'ft_r'),
  [0xA9,0x00,0x00, 0x8F,0xB6,0x70,0x30, 0x22]+L(0)+[], 'ft_r:', [0x68, 0x28, 0x6B],
  'fe:', [0xBF,0xF8,0x00,0xC5, 0xAA, 0xE0,0x20,0x00], ('bra8',0xD0,'fe_n'),
  [0xAF,0x02,0x70,0x30, 0x29,0xFF,0x00], ('bra8',0xF0,'fe_n'),
  'bam:', [0x08, 0xC2,0x30, 0xDA, 0x5A, 0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB, 0xA0,0x89,0x4E, 0xA9,0x0F,0x27, 0x22,0x68,0xC0,0x8F, 0xC2,0x30, 0xA9,0xF4,0x0F, 0x22,0x0C,0x00,0xF3, 0xAB, 0x7A, 0xFA, 0x28, 0x6B],
  'fe_n:', [0x22,0x3E,0x97,0x91, 0x6B],
])
assert lab2['ft'] == 0xF90400
code2 = bytearray(code2); i = lab2['ft_r'] - CODE2 - 3; code2[i:i+3] = bytes(L(lab2['bam']))
o = at(CODE2); assert all(b == 0xFF for b in r[o:o+len(code2)]), "F9:0400 belegt"; r[o:o+len(code2)] = code2
r[oh:oh+9] = bytes([0x22]+L(lab2['fe'])+[0xEA]*5)
r[o0:o0+4] = bytes([0x22]+L(lab['fl']))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d)
print("Fluegel in der Cave = Tod, %d Bytes" % len(code))
