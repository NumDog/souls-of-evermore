# Waffen-Meldung: Bei einem Chaos-Waffenfund merkt sich soe_zufall_live.py die Waffe in SRAM $30:7EBA.
# Der Fund selbst laeuft als Zauberperle (0x807) durch das Fundskript, das dann Text 0x42 "Zauberperle gefunden!"
# (bzw. 0x3F "N Zauberperlen gefunden!") zeigt. Hook an 8C:D0F6 (Text-ID -> Zeiger): ist eine Waffe gemerkt,
# wird stattdessen "<Waffenname> erhalten!" (wie bei den Story-Waffen) aus einem Puffer in SRAM $30:7EC0 gezeigt.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
NAMEN = [0x07A0,0x077C,0x0789,0x0793,0x07AF,0x07BB,0x07C5,0x07CF,0x07D7,0x07DD,0x07E9,0x07F8]   # Waffen-ID 02..18, Bank C5
for p in NAMEN: assert r[0x50000+p-1] == 0
CODE, NTAB = 0xF03700, 0xF037E0
SUFFIX = b" erhalten!"
suf = []
for ch in SUFFIX: suf += [0xA9, ch, 0x9F,0xC0,0x7E,0x30, 0xE8]          # LDA #c ; STA $307EC0,X ; INX
code,_ = assemble(CODE, [
  [0xC9,0x42,0x00], ('bra8',0xF0,'pruef'), [0xC9,0x3F,0x00], ('bra8',0xF0,'pruef'), [0xC9,0x31,0x02], ('bra8',0xF0,'pruef'),   # 0x231 = "Du hast genug Zauberperlen!"
  'orig:', [0x85,0x26, 0xA9,0x92,0x00, 0x5C,0xFB,0xD0,0x8C],            # Original: STA $26 ; LDA #$0092 ; JML 8C:D0FB
  'pruef:', [0x48, 0xAF,0xBA,0x7E,0x30, 0x29,0xFF,0x00], ('bra8',0xD0,'waffe'), [0x68], ('bra8',0x80,'orig'),
  'waffe:', [0xDA, 0x5A],
  [0x4A, 0x3A, 0x0A, 0xAA, 0xBF,NTAB&0xFF,(NTAB>>8)&0xFF,NTAB>>16, 0x85,0x26, 0xA9,0xC5,0x00, 0x85,0x28],   # $26/$28 -> Name
  [0xE2,0x20, 0xA9,0x97, 0x8F,0xC0,0x7E,0x30, 0xA0,0x00,0x00, 0xA2,0x01,0x00],                        # Kopf 0x97
  'n:', [0xB7,0x26], ('bra8',0xF0,'n_ende'), [0x9F,0xC0,0x7E,0x30, 0xC8, 0xE8], ('bra8',0x80,'n'),
  'n_ende:', suf, [0xA9,0x00, 0x9F,0xC0,0x7E,0x30],
  [0xC2,0x20, 0xA9,0x00,0x00, 0x8F,0xBA,0x7E,0x30],                     # Merker loeschen
  [0xA9,0xC0,0x7E, 0x85,0x22, 0xA9,0x30,0x00, 0x85,0x24],               # $22/$24 -> Puffer $30:7EC0
  [0x7A, 0xFA, 0x68, 0x6B],                                             # PLY PLX PLA RTL (zurueck zum Aufrufer von D0F6)
])
ntab = b''.join(p.to_bytes(2,'little') for p in NAMEN)
assert CODE + len(code) <= NTAB
for adr,c in ((CODE,code),(NTAB,ntab)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
o = at(0x8CD0F6); assert bytes(r[o:o+5]) == bytes([0x85,0x26,0xA9,0x92,0x00]), bytes(r[o:o+5]).hex()
r[o:o+5] = bytes([0x5C, CODE&0xFF, (CODE>>8)&0xFF, CODE>>16, 0xEA])

# --- Spielanfang im Chaos auf Schwer: der Hund bringt das Laserschwert, der Junge sagt statt Text 0x657 etwas Eigenes.
# Hook an 8C:D0B8 (Dialogtext-ID -> Zeiger, Skriptbefehl 51). Merker SRAM $30:7EBC (gesetzt in soe_zufall_live.py).
# Steuerzeichen wie im Original: 0x96 = Junge spricht, 0x80 '=' 0x80 = kurze Pause, 0x86 = auf Knopf warten.
SPRUCH = (b"\x96Moment mal\x80=\x80 das ist ja ein LASERSCHWERT!\x86"
          b"Verdammt,\x80=\x80 wir haben SCHWER eingestellt!\x86"
          b"Na egal!\x80=\x80 Ab jetzt bin ich ein Jedi\x80=\x80 und Du bist mein haariger Kumpel!\x86"
          b"Los,\x80=\x80 wir schauen uns mal hier um!\x86\x00")
CODE2, TXT2 = 0xF03800, 0xF03860
SPRUCH2 = (b"\x96Moment mal\x80=\x80 ein LASERSCHWERT,\x80=\x80 eine ATOMAXT und eine LASERLANZE!\x86"
           b"Oh mein Gott,\x80=\x80 wo hast du denn das gefunden?\x86"
           b"Hast du das etwa in den Truemmern vom Raumschiff ausgebuddelt?\x86"
           b"Wuff?\x80=\x80 Ich nehme das mal als Ja!\x86"
           b"Los,\x80=\x80 wir schauen uns mal hier um!\x86\x00")   # v146z3 (Max): Leicht + Laserschwert/Atomaxt/Laserlanze
TXT3 = 0xF8FA00   # frei (v146z3)
TXT4, LEI = 0xF8FD00, 0xF8FC40   # v146z7 (Max): Leicht -> Text 0x63F (Bazooka ist weg) wird 'Bazooka ist noch da'
SPRUCH4 = (b"\x96Hey!\x80=\x80 Cooler Trip!\x80=\x80 Und KRASS,\x80=\x80 die BAZOOKA ist ja noch da!\x86"
           b"Mit voller Munition!\x80=\x80 Prehistorika,\x80=\x80 zieh dich warm an!\x86"
           b"Hm...\x80=\x80 Aber...\x80=\x80 wo bin ich hier eigentlich?\x80=\x80 Und...\x80=\x80 wo steckt dieser Hund?\x86\x00")
code2,lab2 = assemble(CODE2, [
  [0xC9,0x3F,0x06], ('bra8',0xD0,'n1'), [0x5C,LEI&0xFF,(LEI>>8)&0xFF,LEI>>16], 'n1:',
  [0xC9,0x57,0x06], ('bra8',0xF0,'pruef'),
  'orig:', [0x85,0x26, 0xA9,0x92,0x00, 0x5C,0xBD,0xD0,0x8C],            # Original: STA $26 ; LDA #$0092 ; JML 8C:D0BD
  'pruef:', [0x48, 0xAF,0xBC,0x7E,0x30, 0x29,0xFF,0x00], ('bra8',0xD0,'spruch'), [0x68], ('bra8',0x80,'orig'),
  'spruch:', [0xC9,0x02,0x00], ('bra8',0xF0,'sp2'), [0xA9,0x00,0x00, 0x8F,0xBC,0x7E,0x30, 0x68],
  [0xA9,TXT2&0xFF,(TXT2>>8)&0xFF, 0x85,0x22, 0xA9,TXT2>>16,0x00, 0x85,0x24, 0x6B],
  'sp2:', [0xA9,0x00,0x00, 0x8F,0xBC,0x7E,0x30, 0x68],
  [0xA9,TXT3&0xFF,(TXT3>>8)&0xFF, 0x85,0x22, 0xA9,TXT3>>16,0x00, 0x85,0x24, 0x6B],
])
assert CODE2 + len(code2) <= TXT2 and TXT2 + len(SPRUCH) <= 0xF03A00
ORIG = lab2['orig']
lei,_ = assemble(LEI, [[0x48, 0xAF,0x90,0x7E,0x30, 0x29,0x01,0x00], ('bra8',0xF0,'no'),
  [0xAF,0x90,0x7E,0x30, 0xEB, 0x29,0x07,0x00, 0xC9,0x01,0x00], ('bra8',0xD0,'no'),
  [0x68, 0xA9,TXT4&0xFF,(TXT4>>8)&0xFF, 0x85,0x22, 0xA9,TXT4>>16,0x00, 0x85,0x24, 0x6B],
  'no:', [0x68, 0x5C,ORIG&0xFF,(ORIG>>8)&0xFF,ORIG>>16]])
for adr,c in ((CODE2,code2),(TXT2,SPRUCH),(TXT3,SPRUCH2),(LEI,lei),(TXT4,SPRUCH4)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
o = at(0x8CD0B8); assert bytes(r[o:o+5]) == bytes([0x85,0x26,0xA9,0x92,0x00]), bytes(r[o:o+5]).hex()
r[o:o+5] = bytes([0x5C, CODE2&0xFF, (CODE2>>8)&0xFF, CODE2>>16, 0xEA])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Waffen-Meldung eingebaut, %d Bytes"%len(code))
