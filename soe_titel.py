# Titelbild: „SECRET“ im Logo wird zu „SOULS“ (Souls of Evermore). Die Logo-Grafik liegt komprimiert im ROM und wird im
# Vorspann (Bild ~437) vom Grafik-Lader 90:9350 Kachel fuer Kachel in den VRAM entpackt (JSL 8C:CC4F je Stueck, $2E = VRAM-Ziel).
# Hook auf diesen JSL (90:9360): nach jedem Stueck pruefen, ob unsere letzte Kachel schon geschrieben ist ($2E hinter ihr)
# UND im VRAM das Original-Logo steht (2 Woerter von Kachel 0x188 per $2139 lesen). Dann die 60 neuen 8x8-Kacheln
# (tools/titel_souls.bin: je 2 Byte Kachel-Nr + 32 Byte 4bpp) direkt in den VRAM schreiben. Danach passt die Signatur
# nicht mehr -> kein zweites Mal; beim naechsten Titel (Neustart) wieder.
import sys, json, os; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
hier = os.path.dirname(os.path.abspath(__file__))
DATA = open(os.path.join(hier,'tools','titel_souls.bin'),'rb').read()
J = json.load(open(os.path.join(hier,'tools','titel_souls.json')))
CODE, DAT = 0xF07000, 0xF07100
TRIG = 0x2000 + (J['max']+1)*16                     # $2E ab hier: alle unsere Kacheln geschrieben
SIGA = 0x2000 + J['sigtile']*16
code, lab = assemble(CODE, [
  [0x22,0x4F,0xCC,0x8C],                                                 # Original: Stueck entpacken
  [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A],
  [0xA5,0x2E, 0xC9,TRIG&0xFF,TRIG>>8], ('bra8',0x90,'aus'),
  [0xE2,0x20, 0xA9,0x80, 0x8F,0x15,0x21,0x00, 0xC2,0x20],
  [0xA9,SIGA&0xFF,SIGA>>8, 0x8F,0x16,0x21,0x00],
  [0xAF,0x39,0x21,0x00, 0xC9,J['sig1']&0xFF,J['sig1']>>8], ('bra8',0xD0,'aus'),
  [0xA9,(SIGA+1)&0xFF,(SIGA+1)>>8, 0x8F,0x16,0x21,0x00],                  # Adresse neu setzen (Lesezaehler laeuft nicht zuverlaessig weiter)
  [0xAF,0x39,0x21,0x00, 0xC9,J['sig2']&0xFF,J['sig2']>>8], ('bra8',0xD0,'aus'),
  [0xA2,0x00,0x00],
  'k:', [0xBF,DAT&0xFF,(DAT>>8)&0xFF,DAT>>16, 0x0A,0x0A,0x0A,0x0A, 0x18, 0x69,0x00,0x20, 0x8F,0x16,0x21,0x00, 0xE8,0xE8, 0xA0,0x10,0x00],
  'w:', [0xBF,DAT&0xFF,(DAT>>8)&0xFF,DAT>>16, 0x8F,0x18,0x21,0x00, 0xE8,0xE8, 0x88], ('bra8',0xD0,'w'),
  [0xE0,len(DATA)&0xFF,len(DATA)>>8], ('bra8',0x90,'k'),
  [0xA5,0x2E, 0x8F,0x16,0x21,0x00],                                     # VRAM-Adresse wie vorher
  'aus:', [0x7A, 0xFA, 0x68, 0x28, 0x6B],
])
assert CODE + len(code) <= DAT and DAT + len(DATA) <= 0xF07A00
for adr, c in ((CODE, code), (DAT, DATA)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
o = at(0x909360); assert bytes(r[o:o+4]) == bytes([0x22,0x4F,0xCC,0x8C]), bytes(r[o:o+4]).hex()
r[o:o+4] = bytes([0x22, CODE&0xFF, (CODE>>8)&0xFF, CODE>>16])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Titel-Logo SOULS eingebaut, %d Kacheln" % (len(DATA)//34))
