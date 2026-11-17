# Geraeusche stummschalten – seit v69 NUR noch Vulgors Rache-Raptoren (Raum 0x18) und der Blutfleck-Kreis.
# (Frueher alle eingetauschten Gegner; das sperrte auch Ringmenue, Schwerthieb, Gegner-Angriffe.)
# Alte Beschreibung: Geraeusche fremder Gegner stummschalten. Jede Gegend laedt nur die Geraeusch-Samples ihrer Musik (siehe WISSEN „Sound“).
# Fremde Gegner (Chaos/Aehnlich/Gebiet-Tausch, Vulgors Rache-Raptoren) fordern Geraeusche an, die dann falsch klingen
# oder den Soundchip abstuerzen lassen. Hier:
#  - Beim Erscheinen (Vor-Hook F0:1980, um JSL GZ herum): urspruengliche Vorlage = heimisch, eingetauschte = fremd.
#    Rache-Raptor 89 im Vulgor-Raum (0x18) zaehlt als fremd. Listen je Raum in WRAM 7F:F000 (beim Kartenwechsel geleert).
#  - Geraeusch (8C:8662, A = Nr): Ist das ausloesende Objekt ($4C) ein fremder Gegner -> Nr als „passt nicht“ merken.
#    „passt nicht“-Nummern werden nie abgespielt (auch nicht vom Jungen, z. B. Schmerzschrei). Sonst normal.
#  - v68: Spielt ein HEIMISCHER Gegner eine Nr, ist sie „sicher“ (Bitfeld 7F:F0A0) -> nie stumm. Sonst sperrte ein fremder
#    Gegner allgemeine Geraeusche (Treffer usw.) fuer den ganzen Raum.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
CODE, MASK = 0xF04200, 0xF043F0
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
KARTE, NAT_N, NAT, FR_N, FR, BAD, GUT = 0x7FF000, 0x7FF002, 0x7FF004, 0x7FF032, 0x7FF034, 0x7FF080, 0x7FF0A0
ORIG, NR, MSK, TMP = 0x7FF0F0, 0x7FF0F4, 0x7FF0F6, 0x7FF0F8
RAPTOR89 = (0xB678 + 89*74) & 0xFFFF
def liste(name, n_adr, e_adr):
    # name_add: A = Vorlage -> in Liste (wenn nicht drin, max 16). name_hat: A = Vorlage -> Carry = drin
    return [
      f'{name}_hat:', [0x8F]+L(TMP), [0xAF]+L(n_adr), [0x29,0xFF,0x00, 0x0A, 0xAA],
      f'{name}_h1:', ('bra8',0xF0,f'{name}_nein'), [0xCA,0xCA, 0xBF]+L(e_adr), [0xCF]+L(TMP), ('bra8',0xF0,f'{name}_ja'),
      [0x8A], ('bra8',0x80,f'{name}_h1'),
      f'{name}_ja:', [0x38, 0x60],
      f'{name}_nein:', [0x18, 0x60],
      f'{name}_add:', ('jsr',f'{name}_hat'), ('bra8',0xB0,f'{name}_a_raus'),
      [0xAF]+L(n_adr), [0x29,0xFF,0x00, 0xC9,0x10,0x00], ('bra8',0xB0,f'{name}_a_raus'),
      [0x0A, 0xAA, 0xAF]+L(TMP), [0x9F]+L(e_adr), [0xAF]+L(n_adr), [0x1A, 0xE2,0x20, 0x8F]+L(n_adr), [0xC2,0x20],
      f'{name}_a_raus:', [0x60],
    ]
code, lab = assemble(CODE, [
  # ---- Karte gewechselt? -> Listen leeren
  'kartechk:', [0xAF,0xDB,0x0A,0x7E, 0x4F]+L(KARTE), [0x29,0xFF,0x00], ('bra8',0xF0,'k_gleich'),
  [0xA2,0xFE,0x00, 0xA9,0x00,0x00], 'k_leer:', [0x9F]+L(KARTE), [0xCA,0xCA], ('bra8',0x10,'k_leer'),
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0x8F]+L(KARTE),
  'k_gleich:', [0x60],
  # ---- Erscheinen: ersetzt JSL $F01A00 (Gegner-Zufall) im Vor-Hook F0:1980
  'spawn:', [0x08, 0xC2,0x30, 0x48,0xDA,0x5A], ('jsr','kartechk'), [0xA5,0x02, 0x8F]+L(ORIG), [0x7A,0xFA,0x68,0x28],
  [0x22,0x00,0x1A,0xF0],                                                         # Gegner-Zufall (GZ)
  [0x08, 0xC2,0x30, 0x48,0xDA,0x5A],
  [0xAF]+L(ORIG), [0xC9,RAPTOR89&0xFF,RAPTOR89>>8], ('bra8',0xD0,'s_nat'),
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x18,0x00], ('bra8',0xD0,'s_nat'),
  [0xAF]+L(ORIG), ('jsr','fr_add'), ('bra8',0x80,'s_fertig'),                     # Rache-Raptor = fremd
  's_nat:', [0xAF]+L(ORIG), ('jsr','nat_add'),                                  # v69: eingetauschte Gegner NICHT mehr fremd (Max: nur Kreis + Rache-Raptoren stumm)
  's_fertig:', [0x7A,0xFA,0x68,0x28, 0x6B],
  # ---- Geraeusch: JML von 8C:8662 (A = Nr)
  'snd:', [0x08, 0xC2,0x30, 0x48,0xDA,0x5A], ('jsr','kartechk'),
  [0xA5,0x4C, 0xCF,0xFA,0x7F,0x30], ('bra8',0xD0,'n_kein_fleck'),                 # Heilkreis am Blutfleck-Anker -> stumm
  [0xAF,0xF5,0x7F,0x30, 0x29,0xFF,0x00, 0xC9,0x02,0x00], ('bra8',0xD0,'n_kein_fleck'), ('jmp','n_stumm'),
  'n_kein_fleck:', [0xA3,0x05, 0x29,0xFF,0x00, 0x8F]+L(NR),   # Nr = gesichertes A (5,S)
  [0xAF]+L(NR), [0x29,0x07,0x00, 0xAA, 0xBF]+L(MASK), [0x29,0xFF,0x00, 0x8F]+L(MSK),   # Bitmaske
  [0xA6,0x4C, 0xE0,0xE5,0x3D], ('bra8',0x90,'n_pruef'), [0xE0,0x89,0x4E], ('bra8',0xB0,'n_pruef'),
  [0xBF,0x60,0x00,0x7E], ('jsr','fr_hat'), ('bra8',0x90,'n_nativ'),               # fremder Gegner?
  [0xA6,0x4C, 0xBF,0x60,0x00,0x7E], ('jsr','nat_hat'), ('bra8',0xB0,'n_nativ'),     # (X neu laden: _hat benutzt X) (auch heimisch -> nicht fremd)
  [0xAF]+L(NR), [0x4A,0x4A,0x4A, 0xAA, 0xE2,0x20, 0xBF]+L(BAD), [0x0F]+L(MSK), [0x9F]+L(BAD), [0xC2,0x20],   # „passt nicht“
  ('bra8',0x80,'n_pruef'),
  # heimischer Gegner -> Nr passt zum Sample-Set dieses Raums: „sicher“ merken (wird nie gesperrt, auch nicht fuer Junge/Hund)
  'n_nativ:', [0xAF]+L(NR), [0x4A,0x4A,0x4A, 0xAA, 0xE2,0x20, 0xBF]+L(GUT), [0x0F]+L(MSK), [0x9F]+L(GUT), [0xC2,0x20],
  'n_pruef:', [0xAF]+L(NR), [0x4A,0x4A,0x4A, 0xAA, 0xBF]+L(BAD), [0x2F]+L(MSK), [0x29,0xFF,0x00], ('bra8',0xF0,'n_spielen'),
  [0xBF]+L(GUT), [0x2F]+L(MSK), [0x29,0xFF,0x00], ('bra8',0xD0,'n_spielen'),           # gesperrt, aber als sicher bekannt -> spielen
  'n_stumm:', [0x7A,0xFA,0x68,0x28, 0x6B],                                                    # stumm
  'n_spielen:', [0x7A,0xFA,0x68,0x28],
  [0xE2,0x20, 0x8D,0x51,0x0E, 0xC2,0x20, 0xA8, 0xA9,0x04,0x00, 0x5C,0xF1,0x84,0x8C],   # Original 8C:8662
] + liste('nat', NAT_N, NAT) + liste('fr', FR_N, FR))
assert CODE + len(code) <= MASK, hex(CODE + len(code))
for adr, c in ((CODE, code), (MASK, bytes([1,2,4,8,16,32,64,128]))):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
o = at(0xF01980); assert bytes(r[o:o+4]) == bytes([0x22,0x00,0x1A,0xF0]); r[o:o+4] = bytes([0x22]+L(lab['spawn']))
o = at(0x8C8662); assert bytes(r[o:o+4]) == bytes([0xE2,0x20,0x8D,0x51]); r[o:o+4] = bytes([0x5C]+L(lab['snd']))
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Fremde Gegner-Geraeusche stumm eingebaut, %d Bytes, stumm bei %X, spielen bei %X" % (len(code), lab['n_spielen']-5, lab['n_spielen']))
