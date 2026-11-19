# NG+-Zyklen: Gegner in Zyklus z>=1 haben das (2+z)-fache an HP, Angriff, Verteidigung (NG+1 = x5, NG+2 = x6 ...).
# Zyklus-Zaehler: $7E:2257 (wird mit dem Spielstand gespeichert). Eigener Code in Bank $F0 (ROM wird auf 4 MB erweitert).
import sys
quelle, ziel = sys.argv[1], sys.argv[2]
d = open(quelle,'rb').read(); H = len(d) % 1024; hdr, r = d[:H], bytearray(d[H:])
assert len(r) in (0x300000, 0x400000)
if len(r) == 0x300000: r += b'\xff' * 0x100000          # auf 4 MB erweitern
ZYKLUS = (0x57,0x22,0x7E)                                  # $7E2257
def at(snes): return snes & 0x3FFFFF if (snes>>16) >= 0xC0 else (((snes>>16)&0x3F)<<16)|(snes&0xFFFF)
code = {}
# --- skalieren: A(16 bit) = A * (1 + 0.5*Zyklus), max $7FFF. X und Y bleiben erhalten.
SCALE = 0xF00100
s = bytes([
 0xDA,                    # PHX
 0x5A,                    # PHY
 0x48,                    # PHA                 1,S = Wert
 0xAF, *ZYKLUS,           # LDA $7E2257
 0x29, 0xFF, 0x00,        # AND #$00FF
 0xF0, 0x24,              # BEQ fertig
 0xC9, 100, 0x00,         # CMP #100            (Zyklus deckeln bei 99, v97; vorher 8)
 0x90, 0x03,              # BCC ok
 0xA9, 99, 0x00,          # LDA #99
 0x18, 0x69, 0x01, 0x00,  # ok: CLC ADC #$0001 -> Anzahl Additionen = z+1 (Faktor 2+z: NG+1 = x3)
 0xAA,                    # TAX
 0xA3, 0x01,              # LDA $01,S
 0x48,                    # PHA                 1,S = Wert, 3,S = Wert
 0xA3, 0x03,              # LDA $03,S
 0x18,                    # schleife: CLC
 0x63, 0x01,              # ADC $01,S
 0xB0, 0x07,              # BCS deckel
 0x30, 0x05,              # BMI deckel
 0xCA,                    # DEX
 0xD0, 0xF6,              # BNE schleife
 0x80, 0x03,              # BRA speichern
 0xA9, 0xFF, 0x7F,        # deckel: LDA #$7FFF
 0x83, 0x03,              # STA $03,S
 0x68,                    # PLA                 (Wert/2 weg)
 0x68,                    # fertig: PLA         A = Ergebnis
 0x7A,                    # PLY
 0xFA,                    # PLX
 0x6B,                    # RTL
])
code[SCALE] = s
# Pruefe Sprungweite BEQ fertig
fertig = s.index(bytes([0x68,0x7A,0xFA,0x6B])); beq = s.index(bytes([0xF0,0x24]))
assert fertig - (beq+2) == 0x24, fertig-(beq+2)
# --- Level-Bonus (nur NG+): A = K -> Ergebnis = skalierter Wert + K * Level * Zyklus (max $7FFF)
sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
BONUS = 0xF00180
bonus,_ = assemble(BONUS, [
  [0xDA,0x5A,0x48],                         # PHX PHY PHA      1,S=K 3,S=Y 5,S=X 7,S=Wert
  [0xAF,0x57,0x22,0x7E, 0x29,0xFF,0x00], ('bra8',0xF0,'keiner'),
  [0xC9,100,0x00], ('bra8',0x90,'z_ok'), [0xA9,99,0x00], 'z_ok:', [0xA8],    # Y = Zyklus (max 99, v97)
  [0xAF,0x50,0x0A,0x7E, 0x29,0xFF,0x03], ('bra8',0xF0,'keiner'), [0xAA],       # X = Level (bis 1023, v97: vorher 8 Bit)
  [0xA9,0x00,0x00], 'l1:', [0x18,0x63,0x01], ('bra8',0xB0,'deckel'), ('bra8',0x30,'deckel'), [0xCA], ('bra8',0xD0,'l1'), [0x83,0x01],   # 1,S = K*Level
  [0xA9,0x00,0x00], 'l2:', [0x18,0x63,0x01], ('bra8',0xB0,'deckel'), ('bra8',0x30,'deckel'), [0x88], ('bra8',0xD0,'l2'),            # A = K*Level*Zyklus (Ueberlauf -> Deckel)
  [0x18,0x63,0x07], ('bra8',0xB0,'deckel'), ('bra8',0x30,'deckel'), [0x83,0x07], ('bra8',0x80,'keiner'),
  'deckel:', [0xA9,0xFF,0x7F,0x83,0x07],
  'keiner:', [0x68,0x7A,0xFA,0x68,0x6B],    # PLA(K) PLY PLX PLA(Wert) RTL
])
code[BONUS] = bonus
# --- ATKX: Angriff skalieren, im NG+ + (Verteidigung Junge)/4, dann Level-Bonus
ATKX = 0xF00C00
atkx,_ = assemble(ATKX, [
  [0x22,SCALE&0xFF,(SCALE>>8)&0xFF,SCALE>>16, 0x48],                 # JSL SCALE ; PHA
  [0xAF,0x57,0x22,0x7E, 0x29,0xFF,0x00], ('bra8',0xF0,'skip'),
  [0xAF,0x41,0x0A,0x7E, 0x4A,0x4A, 0x18,0x63,0x01], ('bra8',0xB0,'cap'), ('bra8',0x30,'cap'), [0x83,0x01], ('bra8',0x80,'skip'),
  'cap:', [0xA9,0xFF,0x7F,0x83,0x01],
  'skip:', [0xA9,0x02,0x00, 0x4C,BONUS&0xFF,(BONUS>>8)&0xFF],
])
code[ATKX] = atkx
# --- STAERKE: ROM-Monsterwerte sind verdoppelt (Basis HART-nur-Monster). Schwer: Stufe aus $30:7E91 (x1,5 .. x10 vom Original),
#     Normal (Bit0 von $30:7E90): Wert/2 (= Original). Werte < 2 bleiben (Hilfsobjekte mit 1 HP).
STAERKE = 0xF00C40
staerke,_ = assemble(STAERKE, [
  [0x22,0x00,0x58,0xF0],                                                # Goldener Vulgor (soe_vulgor_gold.py): Vorlagen 119-121 /2, Rache-Raptor x5
  # Vulgors Rache: Raptor 89 (Vorlage $8E:D032) im Vulgor-Raum (Karte 0x18) -> Wert x1,5 (vor der Schwierigkeit)
  [0xE0,0x32,0xD0], ('bra8',0xD0,'kein_rap'), [0x48, 0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x18,0x00], ('bra8',0xF0,'rap_ja'),
  [0x68], ('bra8',0x80,'kein_rap'),                                      # (erst springen, dann PLA - PLA setzt Z neu!)
  'rap_ja:', [0xA3,0x01, 0x4A, 0x18, 0x63,0x01, 0x83,0x01, 0x68],        # A = v (vom Stapel) ; v/2 + v = x1,5 (Max: x3 war zu stark)
  'kein_rap:',
  [0xC9,0x02,0x00], ('bra8',0xB0,'gross'), [0x6B], 'gross:',
  [0x48, 0xAF,0x90,0x7E,0x30, 0x4A], ('bra8',0xB0,'normal'),
  # Schwer-Stufe ($30:7E91): ROM-Wert v ist x2 -> 0: v-v/4 (x1,5)  1: v (x2)  2: v+v/2 (x3)  3: 2v+v/2 (x5)  4: 5v (x10)
  [0xAF,0x90,0x7E,0x30, 0xEB, 0x29,0x07,0x00], ('bra8',0xF0,'l0'),
  [0xC9,0x01,0x00], ('bra8',0xF0,'l1'), [0xC9,0x02,0x00], ('bra8',0xF0,'l2'),
  [0xC9,0x03,0x00], ('bra8',0xF0,'l3'), [0xC9,0x04,0x00], ('bra8',0xF0,'l4'),
  'l0:', [0xA3,0x01, 0x4A,0x4A, 0x49,0xFF,0xFF, 0x38, 0x63,0x01], ('bra8',0x80,'st'),
  'l1:', [0xA3,0x01], ('bra8',0x80,'st'),
  'l2:', [0xA3,0x01, 0x4A, 0x18, 0x63,0x01], ('bra8',0x30,'cap'), ('bra8',0x80,'st'),
  'l3:', [0xA3,0x01, 0x0A], ('bra8',0x30,'cap'), [0x48, 0xA3,0x03, 0x4A, 0x18, 0x63,0x01, 0x83,0x01, 0x68], ('bra8',0x30,'cap'), ('bra8',0x80,'st'),
  'l4:', [0xA3,0x01, 0x0A], ('bra8',0x30,'cap'), [0x0A], ('bra8',0x30,'cap'), [0x18, 0x63,0x01], ('bra8',0x30,'cap'), ('bra8',0x80,'st'),
  'cap:', [0xA9,0xFF,0x7F],
  'st:', [0x83,0x01, 0x68, 0x6B],
  'normal:', [0x68, 0x4A],                                                                          # Normal: v/2
  # v146z3 (Max): Leicht = Normal-Bit + Stufe 1 ($30:7E91) -> Original x0,5
  [0x48, 0xAF,0x90,0x7E,0x30, 0xEB, 0x29,0x07,0x00, 0xC9,0x01,0x00], ('bra8',0xD0,'n_ok'),
  [0xA3,0x01, 0x4A, 0x83,0x01],                                             # v146z3 (Max: doch 0,5): Original x0,5
  'n_ok:', [0x68],
  'fertig:', [0x6B],
])
code[STAERKE] = staerke
# --- Trampoline: Original-LDA, skalieren, Level-Bonus
hooks = {0x8FB10C:(0x0F,10), 0x8FBFD7:(0x19,1), 0x8FC007:(0x1B,3)}       # HP, Angriff, Verteidigung: (Feld, K)
tramp = 0xF00010
for site, (feld,K) in hooks.items():
    o = at(site); assert r[o:o+4] == bytes([0xBF,feld,0x00,0x8E]), (hex(site), r[o:o+4].hex())
    # nur Monster (Vorlage in der ROM, X >= $8000) skalieren; Junge/Hund (Vorlage im RAM, X < $2000) unveraendert
    if False and feld == 0x19:   # (ATKX ausgeschaltet - Max: Staerke passt so) Angriff: Sonderweg ueber ATKX (+ Verteidigung des Jungen / 4 im NG+)
        code[tramp] = bytes([0xBF,feld,0x00,0x8E, 0xE0,0x00,0x80, 0xB0,0x01, 0x6B, 0x5C,ATKX&0xFF,(ATKX>>8)&0xFF,ATKX>>16])
    else:
        halb = [0x22,STAERKE&0xFF,(STAERKE>>8)&0xFF,STAERKE>>16] if feld in (0x0F,0x19) else []   # HP/Angriff: Schwer x3/4, Normal /2 (ROM-Werte sind x2)
        code[tramp] = bytes([0xBF,feld,0x00,0x8E, 0xE0,0x00,0x80, 0xB0,0x01, 0x6B] + halb +
                        [0x22,SCALE&0xFF,(SCALE>>8)&0xFF,SCALE>>16, 0x48, 0xA9,K,0x00, 0x4C,BONUS&0xFF,(BONUS>>8)&0xFF])
        assert len(code[tramp]) <= 0x30
    r[o:o+4] = bytes([0x22, tramp&0xFF, (tramp>>8)&0xFF, tramp>>16])
    tramp += 0x30
for a,b in code.items(): o=at(a); r[o:o+len(b)] = b
# Pruefsumme (4 MB)
h=0xFFC0
for _ in range(2):
    c=sum(r)&0xFFFF; r[h+0x1E:h+0x20]=c.to_bytes(2,'little'); r[h+0x1C:h+0x1E]=(c^0xFFFF).to_bytes(2,'little')
open(ziel,'wb').write(hdr+r); print("ok ->", ziel, "Pruefsumme %04X"%c)
