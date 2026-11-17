# Formel +N: Setzt ein Skript das "Formel gelernt"-Bit (Flag 0..34 bei $2258..) erneut, steigt der Formel-Zaehler +N
# (Nibble je Formel in 7E:20B0..20C1, max 15; v88 – vorher Alchemie-Stufe +1). Schaden x1,25 je +N siehe soe_formel_kraft.py.
# Hook: 8C:DC49 (ORA $0000,X ; STA $0000,X im Skriptbefehl "Flag setzen", A = 8 bit Maske, X = Flag-Byte-Adresse)
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
ALCH = 0xF00E00
code,_ = assemble(ALCH, [
  [0x48],                                     # PHA (Maske)
  [0x3D,0x00,0x00], ('bra8',0xF0,'neu'),      # AND $0000,X ; noch nicht gesetzt -> normal
  [0xE0,0x58,0x22], ('bra8',0x90,'neu'),      # CPX #$2258
  [0xE0,0x5D,0x22], ('bra8',0xB0,'neu'),      # CPX #$225D
  [0xDA,0x5A,0x08, 0xC2,0x30],                # PHX PHY PHP REP #$30
  [0x8A,0x38,0xE9,0x58,0x22,0x0A,0x0A,0x0A,0xA8],   # Y = (X-$2258)*8
  [0xE2,0x20, 0xA3,0x06],                     # SEP #$20 ; LDA 6,S (Maske)
  'such:', [0x4A], ('bra8',0xB0,'gefunden'), [0xC8], ('bra8',0x80,'such'),
  'gefunden:', [0xC2,0x20, 0x98, 0xC9,35,0x00], ('bra8',0xB0,'raus'),
  # v88 (Max): nicht mehr Stufe +1, sondern eigener Zaehler +N (Nibble in 7E:20B0 + i/2, gerade i = unten), max 15
  [0x8F,0x30,0xE3,0x7E],                      # Formel-Nr. fuer die Meldung (7E:E330)
  [0x4A, 0xAA, 0xE2,0x20, 0xBF,0xB0,0x20,0x7E], ('bra8',0xB0,'hoch'),          # Carry = ungerade
  [0x29,0x0F, 0xC9,0x0F], ('bra8',0xF0,'z_voll'), [0xBF,0xB0,0x20,0x7E, 0x1A], ('bra8',0x80,'z_st'),
  'hoch:', [0x29,0xF0, 0xC9,0xF0], ('bra8',0xF0,'z_voll'), [0xBF,0xB0,0x20,0x7E, 0x18, 0x69,0x10],
  'z_st:', [0x9F,0xB0,0x20,0x7E],
  'z_voll:', [0xC2,0x20],
  'raus:', [0x28,0x7A,0xFA],                  # PLP PLY PLX
  'neu:', [0x68, 0x1D,0x00,0x00, 0x9D,0x00,0x00, 0x6B],   # PLA ; ORA $0000,X ; STA $0000,X ; RTL
])
o = at(ALCH); assert all(b == 0xFF for b in r[o:o+len(code)]); r[o:o+len(code)] = code
o = at(0x8CDC49); assert bytes(r[o:o+6]) == bytes([0x1D,0x00,0x00,0x9D,0x00,0x00]), bytes(r[o:o+6]).hex()
r[o:o+6] = bytes([0x22, ALCH&0xFF, (ALCH>>8)&0xFF, ALCH>>16, 0xEA, 0xEA])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Formel +1 eingebaut, %d Bytes"%len(code))
