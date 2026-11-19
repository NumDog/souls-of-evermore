# Goldener Vulgor extra (v146p, Max): im goldenen Kampf (Karte 0x18, ZU 30:7FDC = 1 laeuft / 3 steht an)
#  - Saeureregen (beginnt mit Geraeusch 0x0A, Mesen gemessen): danach Gift auf den Jungen (Spiel-Gift wie Lavarex:
#    Y = 4E89, X = 0x90, JSL 91:B514) und das Herz heilt 25 % seiner Max-KP (HMAX = groesste gesehene Herz-KP).
#  - Wegschubsen (Geraeusch 0x3E aus dem Kampfskript): Verwirrung 10 s (Zaehler 7E:E340, soe_vigor VERW).
#  - Je Ereignis 300 Bilder Pause (der Regen spielt 0x0A zweimal).
# Hook: 8C:8662 (Geraeusch, A = Nr) - vorne vor soe_ton_fremd (bisher JML F1:90BC).
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
def w(v): return [v&0xFF, (v>>8)&0xFF]
CODE = 0xF8E000
ZU, OBJ = 0x307FDC, 0x307FDE          # soe_vulgor_gold: Zustand / Herz-Objekt
VZ = 0x7EE340                         # Verwirrung (Bilder)
HMAX, PREG, PSCH, TMP = 0x7EEE74, 0x7EEE76, 0x7EEE78, 0x7EEE7A
o = at(0x8C8662); assert r[o] == 0x5C; ALT = list(r[o+1:o+4])
code, lab = assemble(CODE, [
  'snd:', [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8F]+L(TMP),
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x18,0x00], ('bra8',0xF0,'s_18'), ('jmp','raus'),
  's_18:', [0xAF]+L(ZU)+[0x29,0xFF,0x00, 0xC9,0x03,0x00], ('bra8',0xD0,'s_n3'),
  [0xA9,0x00,0x00, 0x8F]+L(HMAX), ('jmp','raus'),                                        # Kampf steht an -> HMAX neu
  's_n3:', [0xC9,0x01,0x00], ('bra8',0xF0,'s_lauf'), ('jmp','raus'),
  's_lauf:',
  # HMAX = max(HMAX, Herz-KP)
  [0xAF]+L(OBJ)+[0xAA, 0xBF,0x2A,0x00,0x7E, 0xCF]+L(HMAX), ('bra8',0x90,'s_hm'), [0x8F]+L(HMAX), 's_hm:',
  # Pausen herunterzaehlen geschieht hier grob je Geraeusch nicht -> stattdessen Bildzaehler 7E:0100 als Uhr
  [0xAF]+L(TMP)+[0x29,0xFF,0x00, 0xC9,0x0A,0x00], ('bra8',0xD0,'s_n0a'),
  # ---- Saeureregen: Gift + Heilung (hoechstens alle 300 Bilder)
  [0xAF,0x00,0x01,0x7E, 0x38, 0xEF]+L(PREG)+[0xC9,0x2C,0x01], ('bra8',0xB0,'s_reg'), ('jmp','raus'),
  's_reg:', [0xAF,0x00,0x01,0x7E, 0x8F]+L(PREG),
  [0xA0,0x89,0x4E, 0xA2,0x90,0x00, 0x22,0x14,0xB5,0x91, 0xC2,0x30],                        # Gift (Spiel-Gift)
  [0xAF]+L(HMAX)+[0x4A,0x4A, 0x8F]+L(TMP),                                               # +25 %
  [0xAF]+L(OBJ)+[0xAA, 0xBF,0x2A,0x00,0x7E], ('bra8',0xF0,'raus_j'),                      # Herz tot -> nicht heilen
  [0x18, 0x6F]+L(TMP)+[0xCF]+L(HMAX), ('bra8',0x90,'s_hk'), [0xAF]+L(HMAX), 's_hk:',
  [0x9F,0x2A,0x00,0x7E], 'raus_j:', ('jmp','raus'),
  's_n0a:', [0xC9,0x3E,0x00], ('bra8',0xF0,'s_sch'), ('jmp','raus'),
  # ---- Wegschubsen: Verwirrung 10 s (hoechstens alle 300 Bilder)
  's_sch:', [0xAF,0x00,0x01,0x7E, 0x38, 0xEF]+L(PSCH)+[0xC9,0x2C,0x01], ('bra8',0xB0,'s_s2'), ('jmp','raus'),
  's_s2:', [0xAF,0x00,0x01,0x7E, 0x8F]+L(PSCH)+[0xA9,0x58,0x02, 0x8F]+L(VZ),
  'raus:', [0x7A, 0xFA, 0x68, 0x28, 0x5C]+ALT,
])
o2 = at(CODE); assert all(b == 0xFF for b in r[o2:o2+len(code)]); r[o2:o2+len(code)] = code
r[o:o+4] = bytes([0x5C]+L(lab['snd']))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Goldener Vulgor extra eingebaut, %d Bytes" % len(code))
