# Name der Mod im ROM-Kopf (21 Zeichen bei $FFC0): "SOULS OF EVERMORE". Letzter Schritt der Bau-Kette.
import sys
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
NAME = b"SOULS OF EVERMORE".ljust(21, b" ")
assert bytes(r[0xFFC0:0xFFD5]) in (b"SECRET OF EVERMORE   ", NAME), bytes(r[0xFFC0:0xFFD5])
r[0xFFC0:0xFFD5] = NAME
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("ROM-Name: SOULS OF EVERMORE")
