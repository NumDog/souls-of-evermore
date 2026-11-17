# ENDE-Bildschirm (Karte 0x63): unten wechselnde Zeilen in der Untertitel-Schrift (8C:C8E4) – Mod-Hinweis, Name, New Game +.
# Jedes Bild in der Hauptschleife (vor dem Goldenen Vulgor: ersetzt dessen JSL $91C62E). Alle 240 Bilder naechste Zeile.
# SRAM: 30:7FE6 Zaehler, 30:7FE8 Zeile.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
import soe_daten as D
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
CODE = 0xF05C00
ZEILEN = ["Souls of Evermore",
          "Mod-Design und Idee: " + D.NAME,
          "Umsetzung: " + D.NAME,
          "Neues Spiel starten = New Game +",
          "Gegner staerker - Schaetze bleiben!",
          "Danke fuers Spielen!"]
for z in ZEILEN: assert len(z) <= 36 and z.isascii(), z
code, lab = assemble(CODE, [
  'tick:', [0x22,0x2E,0xC6,0x91, 0x08, 0xC2,0x30, 0x48, 0xDA],
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x63,0x00], ('bra8',0xF0,'ende'),
  [0xA9,0x3C,0x00, 0x8F,0xE6,0x7F,0x30, 0xA9,0x00,0x00, 0x8F,0xE8,0x7F,0x30], ('bra8',0x80,'aus'),   # 1 s nach Ankunft erste Zeile
  'ende:', [0xAF,0xE6,0x7F,0x30, 0x3A, 0x8F,0xE6,0x7F,0x30], ('bra8',0xD0,'aus'),
  [0xA9,0xF0,0x00, 0x8F,0xE6,0x7F,0x30],
  [0xAF,0xE8,0x7F,0x30, 0x0A, 0xAA, 0xBF,0xFF,0xFF,0xF0, 0x85,0x22, 0xA9,0xF0,0x00, 0x85,0x24, 0x22,0xE4,0xC8,0x8C],
  [0xAF,0xE8,0x7F,0x30, 0x1A, 0xC9,len(ZEILEN),0x00], ('bra8',0x90,'z_ok'), [0xA9,0x00,0x00],
  'z_ok:', [0x8F,0xE8,0x7F,0x30],
  'aus:', [0xFA, 0x68, 0x28, 0x6B],
])
code = bytearray(code)
TAB = CODE + len(code) + (len(code) & 1)
blob = bytearray(); ptr = []
TXT = TAB + 2*len(ZEILEN)
for z in ZEILEN: ptr.append(TXT + len(blob)); blob += z.encode('ascii') + b'\x00'
i = code.index(bytes([0xBF,0xFF,0xFF,0xF0])); code[i+1:i+3] = (TAB & 0xFFFF).to_bytes(2,'little')
alles = bytes(code) + (b'\xFF' if len(code) & 1 else b'') + b''.join((p & 0xFFFF).to_bytes(2,'little') for p in ptr) + bytes(blob)
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(alles)]) and CODE + len(alles) <= 0xF05E00; r[o:o+len(alles)] = alles
# Goldener Vulgor tick (F0:5800 ff.) beginnt mit JSL $91C62E -> auf uns umbiegen
o = at(0xF05800); seg = bytes(r[o:o+0x200]); i = seg.index(bytes([0x22,0x2E,0xC6,0x91]))
r[o+i:o+i+4] = bytes([0x22, CODE&0xFF, (CODE>>8)&0xFF, CODE>>16])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("ENDE-Text eingebaut, %d Zeilen, %d Bytes" % (len(ZEILEN), len(alles)))
