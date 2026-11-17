# NG+: Mindestschaden gegen Junge/Hund = Level * Zyklus (Hook 8F:C1CC, dort wird $0076,Y von HP $002A,Y abgezogen)
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
DMG = 0xF00D00
code,_ = assemble(DMG, [
  [0xC0,0x89,0x4E], ('bra8',0xF0,'held'), [0xC0,0x37,0x4F], ('bra8',0xD0,'orig'),
  'held:', [0xB9,0x76,0x00], ('bra8',0xF0,'orig'),                         # kein Schaden -> nichts tun
  [0xAF,0x57,0x22,0x7E, 0x29,0xFF,0x00], ('bra8',0xF0,'orig'),              # Zyklus 0 -> normal
  [0xC9,0x09,0x00], ('bra8',0x90,'z_ok'), [0xA9,0x08,0x00], 'z_ok:',
  [0xDA,0xAA, 0xA9,0x00,0x00],                                              # PHX TAX LDA #0
  'l:', [0x18,0x6F,0x50,0x0A,0x7E, 0xCA], ('bra8',0xD0,'l'),                # A = Level * Zyklus
  [0xD9,0x76,0x00], ('bra8',0x90,'fertig'),                                 # CMP $0076,Y ; kleiner -> lassen
  [0x99,0x76,0x00],                                                         # Mindestschaden setzen
  'fertig:', [0xFA],
  'orig:', [0xB9,0x2A,0x00, 0x38, 0xF9,0x76,0x00, 0x6B],                    # LDA $002A,Y ; SEC ; SBC $0076,Y ; RTL
])
o = at(DMG); assert all(b == 0xFF for b in r[o:o+len(code)]); r[o:o+len(code)] = code
o = at(0x8FC1CC); assert bytes(r[o:o+7]) == bytes([0xB9,0x2A,0x00,0x38,0xF9,0x76,0x00]), bytes(r[o:o+7]).hex()
r[o:o+7] = bytes([0x22, DMG&0xFF, (DMG>>8)&0xFF, DMG>>16, 0xEA,0xEA,0xEA])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Mindestschaden eingebaut, %d Bytes"%len(code))
