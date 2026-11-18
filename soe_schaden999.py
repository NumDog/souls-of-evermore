# Schadensgrenze 999 pro Treffer aufheben (Max 18.11.: zweimal 999 zeigt 1998 am Gegner -> Anzeige kann mehr). Neue Grenze 9999.
# 8F:C09C allgemeiner Schaden ($0EA2), D1:9CE7 / 9D1B / 9DD7 Formel-Schaden/-Heilung vor JSL 8F:C068 bzw. C02F.
import sys
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
GRENZE = 9999
STELLEN = [(0x8FC09F, bytes.fromhex('c9e8039003a9e703'), bytes([0xC9,(GRENZE+1)&0xFF,(GRENZE+1)>>8, 0x90,0x03, 0xA9,GRENZE&0xFF,GRENZE>>8]))]
for s in (0xD19CE7, 0xD19D1B, 0xD19DD7):
    STELLEN.append((s, bytes.fromhex('c9e7033003a9e703'), bytes([0xC9,GRENZE&0xFF,GRENZE>>8, 0x30,0x03, 0xA9,GRENZE&0xFF,GRENZE>>8])))
for s, alt, neu in STELLEN:
    o = at(s); assert bytes(r[o:o+8]) == alt, (hex(s), bytes(r[o:o+8]).hex()); r[o:o+8] = neu
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Schadensgrenze 9999")
