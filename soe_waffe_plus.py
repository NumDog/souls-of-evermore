# Waffe +1: doppelt erhaltene Waffe -> Zaehler +1 (Nibble in $7E2250-$7E2256), jeder Punkt +50 % Angriffskraft. Beim Laden (8D:B2A0) wird die Waffe neu 'gegeben' -> Merkzeichen Bit7 von $7E2256 unterdrueckt dann +1.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
assert len(r) == 0x400000, "erst soe_ngplus_patch.py anwenden (4 MB)"
def at(s): return s & 0x3FFFFF if (s>>16) >= 0xC0 else (((s>>16)&0x3F)<<16)|(s&0xFFFF)
# Gemeinsam: A(16) = Waffen-ID (gerade) -> X = Byte-Index, Y = 0/1 (unteres/oberes Nibble)
NIB = [0x4A, 0x3A, 0x48, 0x4A, 0xAA, 0x68, 0x29,0x01,0x00, 0xA8]        # LSR DEC PHA LSR TAX PLA AND#1 TAY
# --- Erhalten: an 8F:92AA (LDA $C50026,X), Y = Adresse des Besitz-Bytes, X = Waffen-ID
GRANT = 0xF00200
g, gl = assemble(GRANT, [
  # Nur ECHTE Gaben zaehlen (Merker SRAM $30:7EB8, gesetzt von Story-Skripten und Chaos-Funden in soe_zufall_live.py).
  # Das Spiel "vergibt" die Waffe auch beim Auswaehlen im Ring-Menue (8E:91E8), bei jedem Raumwechsel (90:8F52),
  # beim Laden (8D:B2A3) und beim Spielstart (8F:8096) -> das war frueher jedes Mal +1 (Laserschwert +15).
  [0x08,0xE2,0x20],             # PHP SEP #$20
  [0xAF,0xB8,0x7E,0x30],        # LDA $307EB8     echte Gabe?
  ('bra8',0xD0,'echt'),
  [0x28],                       # PLP
  ('bra8',0x80,'ende'),         # nein -> kein +1
  'echt:',
  [0xA9,0x00, 0x8F,0xB8,0x7E,0x30],   # Merker loeschen
  [0x28],                       # PLP
  [0xBF,0x26,0x00,0xC5],        # LDA $C50026,X   Bit der Waffe
  [0x39,0x00,0x00],             # AND $0000,Y     schon im Besitz?
  ('bra8',0xF0,'ende'),         # BEQ ende        nein -> normal
  [0xDA,0x5A,0x08],             # PHX PHY PHP
  [0x8A], NIB,                  # TXA ; Nibble-Position
  [0xE2,0x20],                  # SEP #$20
  [0xBF,0x50,0x22,0x7E],        # LDA $7E2250,X
  [0xC0,0x00,0x00],             # CPY #0
  ('bra8',0xD0,'oben'),         # BNE oben
  [0x48,0x29,0x0F,0xC9,0x0F],   # PHA AND #$0F CMP #$0F
  [0x68],                       # PLA
  ('bra8',0xF0,'voll'),         # BEQ voll
  [0x1A],                       # INC A
  ('bra8',0x80,'schreib'),
  'oben:',
  [0xC9,0xF0],                  # CMP #$F0
  ('bra8',0xB0,'voll'),         # BCS voll (>= $F0)
  [0x18,0x69,0x10],             # CLC ADC #$10
  'schreib:',
  [0x9F,0x50,0x22,0x7E],        # STA $7E2250,X
  'voll:',
  [0x28,0x7A,0xFA],             # PLP PLY PLX
  'ende:',
  [0xBF,0x26,0x00,0xC5],        # LDA $C50026,X   (Original-Befehl)
  [0x6B],                       # RTL
])
# --- Angriff: an 8F:847C (LDA $C40000,X), X = Zeiger, $12 = Waffen-ID
ATK = 0xF00280
a, al = assemble(ATK, [
  [0xBF,0x00,0x00,0xC4],        # LDA $C40000,X   Angriffskraft
  [0xDA,0x5A,0x48],             # PHX PHY PHA     1,S = Kraft
  [0xA5,0x12], NIB,             # LDA $12 ; Nibble-Position
  [0xBF,0x50,0x22,0x7E],        # LDA $7E2250,X  (16 bit, nur Low-Byte zaehlt)
  [0xC0,0x00,0x00],             # CPY #0
  ('bra8',0xF0,'unten'),
  [0x4A,0x4A,0x4A,0x4A],        # LSR x4
  'unten:',
  [0x29,0x0F,0x00],             # AND #$000F
  ('bra8',0xF0,'fertig'),       # kein Bonus
  [0xAA],                       # TAX  = Plus-Zahl
  [0xA3,0x01,0x4A,0x48],        # LDA 1,S ; LSR ; PHA      1,S = Kraft/2, 3,S = Kraft
  [0xA3,0x03],                  # LDA 3,S
  'schleife:',
  [0x18,0x63,0x01],             # CLC ADC 1,S
  [0xCA],                       # DEX
  ('bra8',0xD0,'schleife'),
  [0x83,0x03],                  # STA 3,S
  [0x68],                       # PLA
  'fertig:',
  [0x68,0x7A,0xFA],             # PLA PLY PLX   A = Kraft (mit Bonus)
  [0x6B],
])
LOAD = 0xF00300
l, ll = assemble(LOAD, [
  [0xAD,0xBA,0x0A],             # LDA $0ABA       (Original)
  [0x8F,0x41,0x24,0x7E],        # STA $7E2441     (Original)
  ('bra8',0xF0,'raus'),         # keine Waffe -> kein Merkzeichen
  [0xE2,0x20,0xAF,0x56,0x22,0x7E,0x09,0x80,0x8F,0x56,0x22,0x7E,0xC2,0x20],  # SEP; LDA; ORA #$80; STA; REP
  'raus:',
  [0x6B],
])
o = at(0x8DB2A0); assert bytes(r[o:o+7]) == bytes([0xAD,0xBA,0x0A,0x8F,0x41,0x24,0x7E]), bytes(r[o:o+7]).hex()
r[o:o+7] = bytes([0x22, LOAD&0xFF, (LOAD>>8)&0xFF, LOAD>>16, 0xEA,0xEA,0xEA])
for addr, code in ((GRANT,g),(ATK,a),(LOAD,l)):
    o = at(addr); assert all(b == 0xFF for b in r[o:o+len(code)]), "Platz belegt"; r[o:o+len(code)] = code
for site, orig, tgt in ((0x8F92AA, bytes([0xBF,0x26,0x00,0xC5]), GRANT), (0x8F847C, bytes([0xBF,0x00,0x00,0xC4]), ATK)):
    o = at(site); assert bytes(r[o:o+4]) == orig, (hex(site), bytes(r[o:o+4]).hex()); r[o:o+4] = bytes([0x22, tgt&0xFF, (tgt>>8)&0xFF, tgt>>16])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Waffe +1 eingebaut, Pruefsumme %04X"%c)
