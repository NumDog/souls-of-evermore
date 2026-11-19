# Boss nach dem Tod wieder ausloesen (v146b, Max: "beim Sumpf-Boss, wenn ich sterbe, wird der Boss nicht mehr getriggert").
# Sumpfmonster (Vorlage 106) auf Karte 0x01: Lauf-Ausloeser 98:8D67/8D72 pruefen Story-Flag 0x481 ("Kampf begonnen",
# 7E:22E8 Bit 0x02) und setzen es beim Start. soe_aufstehen laedt nach dem Tod den Raum neu, das Flag bleibt aber 1 -> kein Boss.
# Hier: beim Betreten der Karte (Karten-Hook in soe_aufstehen 'karte') das Flag merken (SRAM 30:7FA0, +0x0100 = gueltig),
# beim Tod in dieser Karte (soe_aufstehen 'unser') auf den gemerkten Stand zuruecksetzen. War der Boss beim Betreten schon
# erledigt, bleibt das Flag gesetzt. Weitere Bosse: Zeilen in BOSS ergaenzen (Karte, Flag-Byte, Maske).
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
EIN, TOD, MERK = 0xF1B7A0, 0xF1B7D0, 0x307FA0
KARTE, FLAG, MASKE = 0x01, 0x22E8, 0x02       # Sumpfmonster: Flag 0x481 = 2258 + 0x90, Bit 1
L = lambda a: [a&0xFF, (a>>8)&0xFF, a>>16]
karte_ist = [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,KARTE,0x00]
ein, l1 = assemble(EIN, [
  [0x08, 0xC2,0x30, 0x48, 0xA9,0x00,0x00, 0x8F]+L(0x307FB2), karte_ist, ('bra8',0xD0,'e_r'),   # v146h: Larven-Ersatz-Typ je Raumbesuch neu (soe_vulgor_larven)
  [0xAF]+L(0x7E0000|FLAG)+[0x29,MASKE,0x00, 0x09,0x00,0x01, 0x8F]+L(MERK),
  'e_r:', [0x68, 0x28, 0x6B],
])
tod, l2 = assemble(TOD, [
  [0x08, 0xC2,0x30, 0x48], karte_ist, ('bra8',0xD0,'t_r'),
  [0xAF]+L(MERK)+[0x89,0x00,0x01], ('bra8',0xF0,'t_r'),
  [0xE2,0x20, 0xAF]+L(0x7E0000|FLAG)+[0x29,0xFF^MASKE, 0x0F]+L(MERK)+[0x8F]+L(0x7E0000|FLAG),
  'e_r:' if False else 't_r:', [0xC2,0x20, 0x68, 0x28, 0x6B],
])
assert EIN + len(ein) <= TOD and TOD + len(tod) <= 0xF1B800
for a, blob in ((EIN, ein), (TOD, tod)):
    o = at(a); assert all(b == 0xFF for b in r[o:o+len(blob)]), "Platz belegt %X" % a; r[o:o+len(blob)] = blob
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Boss-Neustart nach Tod eingebaut")
