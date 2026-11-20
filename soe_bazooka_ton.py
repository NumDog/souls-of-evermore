# Bazooka-Geraeusche ausserhalb von Omnitopia stumm (v146z23, Livestream-Tester: Dauerrauschen in Praehistorika/Antiqua mit der
# Bazooka aus dem Leicht-Modus). Die Bazooka gibt es im Original erst in Omnitopia -> ihre Samples (Schuss 0x30, Einschlag 0x18,
# Mesen v146z22 Karte 0x67) fehlen in den anderen Geraeusch-Saetzen; der Soundchip spielt dann Muell in Dauerschleife.
# Hook 8C:8662 (Geraeusch, A = Nr, per JSL gerufen) vorne: A = 0x30/0x18 und ausgeruestete Waffe 0ABA = 0x1A (Bazooka) und
# Karte nicht Omnitopia -> RTL (kein Geraeusch). Sonst weiter zum bisherigen Hook.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
CODE = 0xF8F200
OMNI = [0x00, 0x3F, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x54, 0x61, 0x7E]   # editor/gebiete.json "Omnitopia"
o = at(0x8C8662); assert r[o] == 0x5C; ALT = list(r[o+1:o+4])
teile = ['bt:', [0x08, 0xC2,0x30, 0x48, 0x29,0xFF,0x00, 0xC9,0x30,0x00], ('bra8',0xF0,'bt_w'), [0xC9,0x18,0x00], ('bra8',0xD0,'bt_n'),
         'bt_w:', [0xAF,0xBA,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x1A,0x00], ('bra8',0xD0,'bt_n'),
         [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00]]
for k in OMNI: teile += [[0xC9,k,0x00], ('bra8',0xF0,'bt_n')]
teile += [[0x68, 0x28, 0x6B],                          # stumm: zurueck zum Rufer
          'bt_n:', [0x68, 0x28, 0x5C]+ALT]
code, lab = assemble(CODE, teile)
o2 = at(CODE); assert all(b == 0xFF for b in r[o2:o2+len(code)]), "Platz belegt"; r[o2:o2+len(code)] = code
r[o:o+4] = bytes([0x5C]+L(lab['bt']))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Bazooka-Ton ausserhalb Omnitopia stumm, %d Bytes" % len(code))
