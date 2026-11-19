# DarkSoulCave v144, Etappe Kisten (Bauplan work/dsc/BAUPLAN_KNOTEN.md Etappe 4, MODUS B), Bank F4.
# Kisten = Kachel-Stempel mit der karteneigenen Truhe/Krug/Kuerbis (nur Karten mit Fund-Schalter 05/0E/28/29/4F, Zellzeiger
# zu/offen aus den Schalterdaten, work/dsc/funde/kisten_tab.py). Die "zu"-Kombis tragen schon Bit 0x8000 (B-Pruefung 8F:CDD4).
#  1. Hook 90:9270 hinter dem bisherigen Ziel (JSL F2:0000, zufallsraum): in einem Hoehlen-Gebiet (AKT, Karte nicht 5E/04,
#     TUERM 1..3) zeigt die B-Ausloeser-Liste ($1069/$106B) auf eine eigene Liste 7E:E400 OHNE Original-Eintraege
#     (Original-Kruege/Schnueffelstellen/Hebel setzen sonst Story-Flags) und mit je Kiste "y1 x1 y2 x2 F000+k".
#     Kistenkarte: Flutfuellung ab der Ankunft (Pool-Punkt aus GWAHL/POOLT, Ebene der Ankunft, Form 0, kein Bit 0x100),
#     Besucht-Merker = Bit 0 des Zellzeigers (alle Zeiger = $0FAA+8i), Warteschlange 7F:B600-BFFF (danach wieder 0).
#     5-10 Kisten (2x2) an Stellen, deren 4x4-Umfeld erreichbar ist, Abstand >= 4 Zellen zur Ankunft, >= 5 untereinander,
#     >= 3 Zellen zu jedem Lauf-Ausloeser. Zufall: xorshift16 mit Startwert FSEED je Gebiet (beim ersten Betreten des
#     Gebiets auf diesem Stockwerk gewuerfelt, Bit in GEPL) -> beim Wiederbetreten dieselben Kisten, geoeffnete bleiben
#     offen (Bits FOFF je Gebiet) -> nicht farmbar.
#  2. Hook 8F:ACF1 (B-Ausloeser-Treffer): id < F000 -> JML 8C:D241 (unveraendert, auch Lauf-Ausloeser/Tueren).
#     id F000+k: nur der Junge, Kiste noch zu -> Bit setzen, Zellen auf "offen" (7F) + VRAM-Ring $1172 (geklammert mit
#     INC/DEC $0F3C, Fensterpruefung $0F8E-$0F9C). Dann:
#       - Schalter-Kiste (k=0 im Gebiet SCHALTG): STAIROK=1 + Meldung FF9 "Ein Mechanismus rastet ein -", 150 Bilder
#         spaeter FF8 "die Treppe ist frei!" (eine Meldungszeile fasst nur ~39 Zeichen).
#       - Waffen-Orb: (Zufall mod 200) < Stockwerk und ORBST != Stockwerk -> WINC + Meldung FFE, ORBST = Stockwerk.
#       - sonst 7E:2391 = Beute (Zutat/Verbrauchsgut aus Tabelle) und Skript F4:8000 (Buecken, a3 3e/3f/41, bd) ueber 8C:D257.
#  Testhilfe: SRAM 30:70B0 = 4F52 -> Orb-Wurf gilt immer als Treffer (Deckel ORBST bleibt).
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
def w(v): return [v&0xFF,(v>>8)&0xFF]
CODE, KTAB, BITS, LOOT, RTAB, SKRIPT = 0xF42000, 0xF44000, 0xF44100, 0xF44140, 0xF44180, 0xF48000
# SRAM (soe_hoehle / Bauplan)
AKT, FLOOR, MSGP, TUERM = 0x307002, 0x307004, 0x307026, 0x307038
STAIROK, SCHALTG, GEPL, ORBST, GWAHL = 0x307082, 0x307084, 0x307086, 0x30708C, 0x307090
MSGV, MSGI = 0x307098, 0x30709A                              # verzoegerte Meldung (soe_knoten)
FSEED, FOFF, ORBTEST = 0x3070A0, 0x3070A8, 0x3070B0      # neu: +2*TUERM (TUERM 1..3), Testhilfe
POOLT, WINC = 0xF1F800, 0xF1B080
o = at(POOLT); assert bytes(r[o:o+6]) == bytes([0x29,0,0x48,0x01,0xD8,0x03]), bytes(r[o:o+6]).hex()   # erster Pool-Eintrag (29,328,984)
o = at(WINC); assert r[o] != 0xFF
# WRAM 7E (DB = 7E, absolut)
BL = 0xE400                                                   # eigene B-Liste (max 10 x 6 Byte)
KN, KSW, KTI, KK, CX, CY = 0xE500, 0xE502, 0xE504, 0xE506, 0xE508, 0xE50A
KCX, KCY = 0xE510, 0xE530                                    # je 10 Woerter
(VW, VH, VK, VLEV, VAX, VAY, RNG, QH, QT, NZ, TRY, T1, T2, T3, T4, TT, OX, OY, TRN,
 WX, WY, WNX, WNY, VMAP, PB, J, CUR, T5, TY1, TX1, TY2, TX2, P2M, P2I, P2N, QOV, RB, RC) = [0xE560+2*i for i in range(38)]
assert RC < 0xE600
Q, QCAP = 0x7FB600, 0x0A00                                   # Warteschlange 7F:B600-BFFF (0 beim Hook, danach wieder 0)
MAXK = 10
def a(op, adr): return [op]+w(adr)
LDA, STA, STZ, INC, DEC, CMP, ADC, SBC, EOR, ORA, AND = 0xAD,0x8D,0x9C,0xEE,0xCE,0xCD,0x6D,0xED,0x4D,0x0D,0x2D
LDX, LDY, STX, STY, CPX, CPY = 0xAE,0xAC,0x8E,0x8C,0xEC,0xCC
LDAX, STAX = 0xBD, 0x9D
def li(v): return [0xA9]+w(v)
def ci(v): return [0xC9]+w(v)
def ai(v): return [0x29]+w(v)
ASL, LSR, INA, DEA, INX, INY, DEX, DEY, TAX, TAY, TXA, TYA, CLC, SEC, XBA = 0x0A,0x4A,0x1A,0x3A,0xE8,0xC8,0xCA,0x88,0xAA,0xA8,0x8A,0x98,0x18,0x38,0xEB
SEP, REP = [0xE2,0x20], [0xC2,0x20]
NOP8 = [0xEA]*8
def ll(op, adr): return [op]+L(adr)                          # long: AF lda, 8F sta, BF lda,x, 9F sta,x, CF cmp, 2F and, 0F ora, 3F and,x

# ---- Kistentabelle: Karte, 0, zu(4 Woerter: (0,0) (1,0) (0,1) (1,1)), offen(4 Woerter); Ende FF
KISTEN = [
  (0x05, [0x2650,0x2658,0x26C8,0x26D0], [0x3520,0x3528,0x3530,0x3538]),   # Schalter 07 (Kuerbis)
  (0x0E, [0x0B48,0x0B50,0x0BC0,0x0BC8], [0x1158,0x1160,0x1168,0x1170]),   # Schalter 00 (nur untere Reihe mit 0x8000)
  (0x28, [0x43D4,0x43DC,0x4454,0x445C], [0x508C,0x5094,0x509C,0x50A4]),   # Schalter 20
  (0x29, [0x18B0,0x18B8,0x1928,0x1980], [0x2740,0x2748,0x2750,0x2758]),   # Schalter 01 (Krug, Bauplan GEPRUEFT)
  (0x4F, [0x13CA,0x13D2,0x1312,0x143A], [0x1B62,0x1B6A,0x1B72,0x1B7A]),   # Schalter 10
]
ktab = b''.join(bytes([m,0]) + b''.join(v.to_bytes(2,'little') for v in zu+auf) for m,zu,auf in KISTEN) + b'\xFF'
bits = b''.join((1<<i).to_bytes(2,'little') for i in range(16))
# Rand-Ring um eine 2x2-Kiste (12 Zellen, im Kreis), als Wort-Versatz zu (cy<<8|cx)
RING = [(-1,-1),(0,-1),(1,-1),(2,-1),(2,0),(2,1),(2,2),(1,2),(0,2),(-1,2),(-1,1),(-1,0)]
rtab = b''.join(((dy*256+dx) & 0xFFFF).to_bytes(2,'little') for dx,dy in RING)
# Beute: 21 Zutaten 0x200-0x215 ohne 0x205 (Matschpfeffer) + 11 Verbrauchsgueter (ohne 0x804 Fluegel, 0x807 Zauberperle)
BEUTE = [0x200+i for i in range(0x16) if i != 5] + [0x800]*3 + [0x801]*3 + [0x802]*2 + [0x803, 0x805, 0x806]
assert len(BEUTE) == 32
loot = b''.join(v.to_bytes(2,'little') for v in BEUTE)
# Fund-Skript (GEPRUEFT r_schnueffeln_pruef Variante B): Junge bueckt sich, Platz-Pruefung, geben + "X gefunden!" / "genug X", bd
skript = bytes.fromhex('bc78d01800b0a714a33e0985900405 00a33f040200a341bd0c9004b000'.replace(' ',''))
assert len(skript) == 29
SKP = ((SKRIPT>>16) - 0x93) << 15 | (SKRIPT & 0x7FFF)         # Zeiger fuer 8C:D2FD: Bank 0x93+(p>>15), Adresse 0x8000|(p&7FFF)

o9 = at(0x909270); assert r[o9] == 0x22; ALT9270 = list(r[o9+1:o9+4])          # bisher JSL F2:0000 (zufallsraum)
oa = at(0x8FACF1); assert bytes(r[oa:oa+4]) == bytes([0x5C,0x41,0xD2,0x8C]), bytes(r[oa:oa+4]).hex()

t = [
  # ================= Hook 90:9270 (Kartenaufbau fertig, Bild noch aus)
  'fk:', [0x22]+ALT9270,
  [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB, 0xD4,0x26, 0xD4,0x28],
  a(STZ,KN), a(STZ,KSW), a(STZ,QT), a(STZ,P2M), a(STZ,QOV),
  ll(0xAF,AKT)+ai(0xFF), ('bra8',0xD0,'f1'), ('jmp','raus'),
  'f1:', a(LDA,0x0ADB)+ai(0xFF)+ci(0x5E), ('bra8',0xD0,'f2'), ('jmp','raus'),
  'f2:', ci(0x04), ('bra8',0xD0,'f3'), ('jmp','raus'),
  'f3:', a(STA,VMAP),
  # eigene B-Liste (leer): Original-Eintraege gelten im Hoehlen-Gebiet nicht
  a(STZ,0x1069), li(BL)+a(STA,0x106B), SEP, [0xA9,0x7E]+a(STA,0x106D), REP,
  ll(0xAF,TUERM)+ai(0x03), ('bra8',0xD0,'f4'), ('jmp','raus'),
  'f4:', [ASL]+a(STA,TT),
  # Schalter-Gebiet? (frueh, damit jeder Ausstieg ohne Kiste die Treppe freigibt)
  ll(0xAF,TUERM)+ai(0x03)+ll(0xCF,SCHALTG), ('bra8',0xD0,'f5'), a(INC,KSW),
  'f5:',
  # Kistenkarte?
  [0xA2,0x00,0x00],
  'ft:', ll(0xBF,KTAB)+ai(0xFF)+ci(0xFF), ('bra8',0xD0,'ft1'), ('jmp','nf'),
  'ft1:', a(CMP,VMAP), ('bra8',0xF0,'fg'), [TXA,CLC,0x69,18,0x00,TAX], ('bra8',0x80,'ft'),
  'fg:', a(STX,KTI), ll(0xBF,KTAB+6)+[TAX, 0xBF,0x04,0x00,0x7F], ('bra8',0x30,'fg1'), ('jmp','nf'),   # Zeiger (0,1) muss 0x8000 tragen
  # Ankunft = Pool-Punkt der Seitentuer (GWAHL = Eintrag*6)
  'fg1:', a(LDX,TT), ll(0xBF,GWAHL)+ci(0xFFFF), ('bra8',0xD0,'fa'), ('jmp','nf'),
  'fa:', [TAX], ll(0xBF,POOLT)+ai(0xFF)+a(CMP,VMAP), ('bra8',0xF0,'fa1'), ('jmp','nf'),
  'fa1:', ll(0xBF,POOLT+2)+[LSR,LSR,LSR,LSR]+a(STA,VAX), ll(0xBF,POOLT+4)+[LSR,LSR,LSR,LSR]+a(STA,VAY),
  # Startwert je Gebiet (einmal je Stockwerk)
  'fs:', a(LDX,TT), ll(0xBF,BITS)+a(STA,T1), ll(0xAF,GEPL)+a(AND,T1), ('bra8',0xD0,'fs_ok'),
  [0x22,0x9B,0x85,0x80]+a(EOR,0x0100)+[0x09,0x01,0x00]+a(LDX,TT)+ll(0x9F,FSEED)+li(0)+ll(0x9F,FOFF),
  ll(0xAF,GEPL)+a(ORA,T1)+ll(0x8F,GEPL),
  'fs_ok:', a(LDX,TT), ll(0xBF,FSEED)+[0x09,0x01,0x00]+a(STA,RNG),
  # Kartenwerte
  a(LDA,0x08EE)+a(STA,VW), a(LDA,0x0FAA)+ai(7)+a(STA,VK),
  a(LDA,0x0FAA)+[LSR]+ll(0x8F,0x004204)+SEP+a(LDA,VW)+ll(0x8F,0x004206)+REP+NOP8+ll(0xAF,0x004214)+a(STA,VH),
  a(LDA,0x0F88)+a(STA,OX), a(LDA,0x0F8A)+a(STA,OY),
  a(LDA,0x1066)+[0x85,0x26]+a(LDA,0x1067)+[0x85,0x27]+a(LDA,0x1064)+a(STA,TRN),
  a(LDA,VW)+ci(0x100), ('bra8',0xB0,'f_weg'), a(LDA,VH)+ci(0x100), ('bra8',0x90,'fb'),
  'f_weg:', ('jmp','nf'),
  # Flutfuellung ab der Ankunft
  'fb:', a(LDA,VAY)+[XBA]+a(ORA,VAX)+a(STA,CUR), ('jsr','idx'), ('jsr','attr'), [0x89,0x0F,0x41], ('bra8',0xF0,'fb1'), ('jmp','fertig'),
  'fb1:', ai(0x30)+a(STA,VLEV),
  [0xBF,0x00,0x00,0x7F, 0x49,0x01,0x00, 0x9F,0x00,0x00,0x7F], a(STZ,QH), a(LDA,CUR)+ll(0x8F,Q)+li(2)+a(STA,QT),
  'bfs:', a(LDA,QH)+a(CMP,QT), ('bra8',0xD0,'bf0'), ('jmp','bfs_e'),
  'bf0:', [TAX]+ll(0xBF,Q)+a(STA,CUR)+[INX,INX]+a(STX,QH),
  a(LDA,CUR)+ai(0xFF)+[INA]+a(CMP,VW), ('bra8',0xB0,'bf1'), a(LDA,CUR)+[INA], ('jsr','try'),
  'bf1:', a(LDA,CUR)+ai(0xFF), ('bra8',0xF0,'bf2'), a(LDA,CUR)+[DEA], ('jsr','try'),
  'bf2:', a(LDA,CUR)+[XBA]+ai(0xFF)+[INA]+a(CMP,VH), ('bra8',0xB0,'bf3'), a(LDA,CUR)+[CLC,0x69,0x00,0x01], ('jsr','try'),
  'bf3:', a(LDA,CUR)+ai(0xFF00), ('bra8',0xF0,'bf4'), a(LDA,CUR)+[SEC,0xE9,0x00,0x01], ('jsr','try'),
  'bf4:', ('jmp','bfs'),
  'bfs_e:',
  # Anzahl 5..10
  ('jsr','rnd'), ll(0x8F,0x004204)+SEP+[0xA9,6]+ll(0x8F,0x004206)+REP+NOP8+ll(0xAF,0x004216)+[CLC,0x69,5,0]+a(STA,NZ),
  li(400)+a(STA,TRY), a(LDA,QT)+[LSR]+a(STA,T2),
  'pk:', a(LDA,KN)+a(CMP,NZ), ('bra8',0x90,'pk1'), ('jmp','fertig'),
  'pk1:', a(DEC,TRY), ('bra8',0xD0,'pk2'), ('jmp','p2'),
  'pk2:', ('jsr','rnd'), ai(0x0FFF),
  'md:', a(CMP,T2), ('bra8',0x90,'md_e'), a(SBC,T2), ('bra8',0x80,'md'),
  'md_e:', [ASL,TAX]+ll(0xBF,Q)+ai(0xFF)+a(STA,CX)+ll(0xBF,Q)+[XBA]+ai(0xFF)+a(STA,CY),
  ('jsr','pruef'), ('bra8',0xB0,'pk'),
  ('jsr','stempel'), a(INC,KN), ('bra8',0x80,'pk'),
  # Phase 2 (zu wenig Kisten nach 399 Zufallsversuchen): alle erreichbaren Zellen der Reihe nach ab Zufallsstart,
  # Kisten-Abstand nur Chebyshev >= 3, statt 4x4-frei gilt die Rand-Regel (pruef P2M=1). Nicht bei voller Warteschlange.
  'p2:', a(LDA,QOV), ('bra8',0xF0,'p2a'), ('jmp','fertig'),
  'p2a:', a(INC,P2M), a(LDA,T2)+a(STA,P2N), ('jsr','rnd'), ai(0x0FFF),
  'p2m:', a(CMP,T2), ('bra8',0x90,'p2s'), a(SBC,T2), ('bra8',0x80,'p2m'),
  'p2s:', a(STA,P2I),
  'p2l:', a(LDA,KN)+a(CMP,NZ), ('bra8',0x90,'p2b'), ('jmp','fertig'),
  'p2b:', a(LDA,P2N), ('bra8',0xD0,'p2c'), ('jmp','fertig'),
  'p2c:', a(DEC,P2N), a(LDA,P2I)+[ASL,TAX]+ll(0xBF,Q)+ai(0xFF)+a(STA,CX)+ll(0xBF,Q)+[XBA]+ai(0xFF)+a(STA,CY),
  a(INC,P2I)+a(LDA,P2I)+a(CMP,T2), ('bra8',0x90,'p2d'), a(STZ,P2I),
  'p2d:', ('jsr','pruef'), ('bra8',0xB0,'p2l'), ('jsr','stempel'), a(INC,KN), ('jmp','p2l'),
  # Schluss: Besucht-Bits weg, Warteschlange wieder 0, Schalter-Notfall
  'fertig:', a(LDA,VH)+[XBA]+a(ORA,VW)+ll(0x8F,0x004202)+[0xEA,0xEA,0xEA,0xEA]+ll(0xAF,0x004216)+[ASL]+a(STA,T1), [0xA2,0x00,0x00],
  'rl:', a(CPX,T1), ('bra8',0xB0,'rl_e'), [0xBF,0x00,0x00,0x7F]+ai(0xFFF8)+a(ORA,VK)+[0x9F,0x00,0x00,0x7F, INX,INX], ('bra8',0x80,'rl'),
  'rl_e:', [0xA2,0x00,0x00],
  'ql:', a(CPX,QT), ('bra8',0xB0,'ql_e'), li(0)+ll(0x9F,Q)+[INX,INX], ('bra8',0x80,'ql'),
  'ql_e:',
  'nf:', a(LDA,KSW), ('bra8',0xF0,'raus'), a(LDA,KN), ('bra8',0xD0,'raus'), li(1)+ll(0x8F,STAIROK),   # Schalter-Gebiet ohne Kiste -> Treppe frei (kein Festsitzen)
  'raus:', [0x68, 0x85,0x28, 0x68, 0x85,0x26, 0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],

  # ---- try: A = Zelle (cy<<8|cx) -> erreichbar? markieren + einreihen
  'try:', a(STA,T1), ('jsr','idx'), [0xBF,0x00,0x00,0x7F]+ai(7)+a(CMP,VK), ('bra8',0xD0,'t_r'),
  ('jsr','attr'), [0x89,0x0F,0x41], ('bra8',0xD0,'t_r'), ai(0x30)+a(CMP,VLEV), ('bra8',0xD0,'t_r'),
  a(LDA,QT)+ci(QCAP), ('bra8',0x90,'t_m'), a(INC,QOV), [0x60],                 # Warteschlange voll: nicht markieren, merken
  't_m:', [0xBF,0x00,0x00,0x7F, 0x49,0x01,0x00, 0x9F,0x00,0x00,0x7F],
  a(LDX,QT)+a(LDA,T1)+ll(0x9F,Q)+[INX,INX]+a(STX,QT),
  't_r:', [0x60],
  # ---- idx: A = cy<<8|cx -> X = 2*(cy*W+cx)
  'idx:', [0x48]+ai(0xFF00)+a(ORA,VW)+ll(0x8F,0x004202)+[0x68]+ai(0xFF)+[0xEA,0xEA,CLC]+ll(0x6F,0x004216)+[ASL,TAX,0x60],
  # ---- attr: X = Zelle -> A = Attribut (Besucht-Bits im Zeiger ausgeblendet), X bleibt
  'attr:', [0xBF,0x00,0x00,0x7F]+ai(0xFFF8)+a(ORA,VK)+[0xDA,TAX,0xBF,0x04,0x00,0x7F,0xFA,0x60],
  # ---- rnd: xorshift16
  'rnd:', a(LDA,RNG)+[ASL]*7+a(EOR,RNG)+a(STA,RNG)+[LSR]*9+a(EOR,RNG)+a(STA,RNG)+[XBA]+ai(0xFF00)+a(EOR,RNG)+a(STA,RNG)+[0x60],
  'absv:', ('bra8',0x10,'ab_r'), [0x49,0xFF,0xFF,INA], 'ab_r:', [0x60],
  # ---- jcell: Zelle J (0..3) der Kiste (CX,CY) -> X
  'jcell:', a(LDA,J)+[LSR,CLC]+a(ADC,CY)+[XBA]+a(STA,T5)+a(LDA,J)+ai(1)+[CLC]+a(ADC,CX)+a(ORA,T5), ('jsr','idx'), [0x60],
  # ---- pruef: Kiste bei (CX,CY) erlaubt? C=0 ja
  'pruef:', a(LDA,CX), ('bra8',0xF0,'pf'), [INA,INA]+a(CMP,VW), ('bra8',0xB0,'pf'),
  a(LDA,CY), ('bra8',0xF0,'pf'), [INA,INA]+a(CMP,VH), ('bra8',0xB0,'pf'),
  a(LDA,CX)+[SEC]+a(SBC,VAX), ('jsr','absv'), a(STA,T3), a(LDA,CY)+[SEC]+a(SBC,VAY), ('jsr','absv'), [CLC]+a(ADC,T3)+ci(4), ('bra8',0x90,'pf'),
  [0xA0,0x00,0x00],
  'pa:', a(CPY,KN), ('bra8',0xB0,'pa_e'), [TYA,ASL,TAX], a(LDA,CX)+[SEC,0xFD]+w(KCX), ('jsr','absv'), a(STA,T3),
  a(LDA,CY)+[SEC,0xFD]+w(KCY), ('jsr','absv'), a(STA,T4), a(LDA,P2M), ('bra8',0xD0,'pc'),
  a(LDA,T4)+[CLC]+a(ADC,T3)+ci(5), ('bra8',0x90,'pf'), ('bra8',0x80,'pn'),
  'pc:', a(LDA,T3)+ci(3), ('bra8',0xB0,'pn'), a(LDA,T4)+ci(3), ('bra8',0x90,'pf'),
  'pn:', [INY], ('jmp','pa'),
  'pf:', [SEC,0x60],
  'pa_e:', a(LDA,CX)+[CLC]+a(ADC,OX)+a(STA,T3), a(LDA,CY)+[CLC]+a(ADC,OY)+a(STA,T4), [0xA0,0x00,0x00],
  'tr:', a(CPY,TRN), ('bra8',0xB0,'tr_e'),
  [0xB7,0x26]+ai(0xFF)+a(STA,TY1)+[INY, 0xB7,0x26]+ai(0xFF)+a(STA,TX1)+[INY, 0xB7,0x26]+ai(0xFF)+a(STA,TY2)+[INY, 0xB7,0x26]+ai(0xFF)+a(STA,TX2)+[INY,INY,INY],
  a(LDA,TX2)+[CLC,0x69,3,0]+a(CMP,T3), ('bra8',0x90,'tr'), ('bra8',0xF0,'tr'),
  a(LDA,T3)+[CLC,0x69,5,0]+a(CMP,TX1), ('bra8',0x90,'tr'), ('bra8',0xF0,'tr'),
  a(LDA,TY2)+[CLC,0x69,3,0]+a(CMP,T4), ('bra8',0x90,'tr'), ('bra8',0xF0,'tr'),
  a(LDA,T4)+[CLC,0x69,5,0]+a(CMP,TY1), ('bra8',0x90,'tr'), ('bra8',0xF0,'tr'),
  'pf2:', [SEC,0x60],
  'tr_e:', a(LDA,P2M), ('bra8',0xF0,'tr_s'), ('jmp','rg0'),
  'tr_s:', a(LDA,CY)+[DEA]+a(STA,WY)+li(4)+a(STA,WNY),
  'wy:', a(LDA,CX)+[DEA]+a(STA,WX)+li(4)+a(STA,WNX),
  'wx:', a(LDA,WY)+[XBA]+a(ORA,WX), ('jsr','idx'), [0xBF,0x00,0x00,0x7F]+ai(7)+a(CMP,VK), ('bra8',0xF0,'pf2'),
  a(INC,WX)+a(DEC,WNX), ('bra8',0xD0,'wx'), a(INC,WY)+a(DEC,WNY), ('bra8',0xD0,'wy'),
  'pi0:', a(STZ,J),
  'pi:', ('jsr','jcell'), ('jsr','attr'), [0x89,0x4F,0xE1], ('bra8',0xD0,'pf2'), a(INC,J)+a(LDA,J)+ci(4), ('bra8',0x90,'pi'),
  [CLC,0x60],
  # Rand-Regel (Phase 2): die 4 Kistenzellen erreichbar; jede nicht erreichbare Randzelle ist echte Wand (Attribut & 0x010F),
  # die erreichbaren Randzellen bilden genau einen Bogen -> die Kiste trennt nichts ab.
  'rg0:', a(STZ,J),
  'rgk:', ('jsr','jcell'), [0xBF,0x00,0x00,0x7F]+ai(7)+a(CMP,VK), ('bra8',0xD0,'rgk1'), ('jmp','pf2'),
  'rgk1:', a(INC,J)+a(LDA,J)+ci(4), ('bra8',0x90,'rgk'),
  a(STZ,RB), a(STZ,RC),
  'rg:', a(LDX,RC)+ll(0xBF,RTAB)+a(STA,T5)+a(LDA,CY)+[XBA]+a(ORA,CX)+[CLC]+a(ADC,T5), ('jsr','idx'),
  [0xBF,0x00,0x00,0x7F]+ai(7)+a(CMP,VK), ('bra8',0xF0,'rg_w'), [SEC], ('bra8',0x80,'rg_b'),
  'rg_w:', ('jsr','attr'), [0x89,0x0F,0x01], ('bra8',0xD0,'rg_c'), ('jmp','pf2'),
  'rg_c:', [CLC],
  'rg_b:', [0x2E]+w(RB), a(INC,RC)+a(INC,RC)+a(LDA,RC)+ci(24), ('bra8',0x90,'rg'),
  a(LDA,RB)+[ASL]+a(STA,T5)+a(LDA,RB)+ai(0x0800), ('bra8',0xF0,'rg_d'), a(INC,T5),
  'rg_d:', a(LDA,T5)+ai(0x0FFF)+[0x49,0xFF,0xFF]+a(AND,RB)+a(STA,T5)+[DEA]+a(AND,T5), ('bra8',0xF0,'rg_ok'), ('jmp','pf2'),
  'rg_ok:', ('jmp','pi0'),
  # ---- stempel: Kiste KN an (CX,CY): Zeiger zu/offen, B-Listen-Eintrag F000+KN
  'stempel:', a(LDA,KN)+[ASL,TAX]+a(LDA,CX)+a(STAX,KCX)+a(LDA,CY)+a(STAX,KCY),
  ll(0xBF,BITS)+a(LDX,TT)+ll(0x3F,FOFF), ('bra8',0xF0,'st_z'), li(10), ('bra8',0x80,'st_1'),
  'st_z:', li(2), 'st_1:', a(STA,PB), a(STZ,J),
  'sl:', ('jsr','jcell'), a(STX,T1), a(LDA,J)+[ASL,CLC]+a(ADC,PB)+a(ADC,KTI)+[TAX]+ll(0xBF,KTAB)+a(LDX,T1)+[0x9F,0x00,0x00,0x7F],
  a(INC,J)+a(LDA,J)+ci(4), ('bra8',0x90,'sl'),
  a(LDA,KN)+[ASL]+a(ADC,KN)+[ASL,TAX],
  a(LDA,CY)+[CLC]+a(ADC,OY)+SEP+a(STAX,BL)+[CLC,0x69,2]+a(STAX,BL+2)+REP,
  a(LDA,CX)+[CLC]+a(ADC,OX)+SEP+a(STAX,BL+1)+[CLC,0x69,2]+a(STAX,BL+3)+REP,
  a(LDA,KN)+[0x09,0x00,0xF0]+a(STAX,BL+4), [TXA,CLC,0x69,6,0]+a(STA,0x1069), [0x60],

  # ================= Hook 8F:ACF1 (B-Ausloeser-Treffer, M=16 X=16, X = id, Y = $4C)
  'ok:', [0xE0,0x00,0xF0], ('bra8',0xB0,'ok_m'), [0x5C,0x41,0xD2,0x8C],
  'ok_m:', [0x8B, 0x5A, 0xF4,0x7E,0x7E, 0xAB,0xAB],
  [TXA]+ai(0x0FFF)+a(CMP,KN), ('bra8',0x90,'ok_k'), ('jmp','ok_r'),
  'ok_k:', a(STA,KK), ll(0xAF,AKT)+ai(0xFF), ('bra8',0xD0,'ok_a'), ('jmp','ok_r'),
  'ok_a:', a(LDA,0x0F44)+a(CMP,0x0F40), ('bra8',0xF0,'ok_j'), ('jmp','ok_r'),                    # nur der Junge
  'ok_j:', a(LDA,KK)+[ASL,TAX]+ll(0xBF,BITS)+a(STA,T1), ll(0xAF,TUERM)+ai(3)+[ASL,TAX], ll(0xBF,FOFF)+a(AND,T1), ('bra8',0xF0,'ok_o'), ('jmp','ok_r'),
  'ok_o:', ll(0xBF,FOFF)+a(ORA,T1)+ll(0x9F,FOFF),
  # Grafik oeffnen: 7F + VRAM-Ring (NMI ueberspringt den Ring solange $0F3C != 0)
  a(LDA,KK)+[ASL,TAX]+a(LDAX,KCX)+a(STA,CX)+a(LDAX,KCY)+a(STA,CY),
  a(INC,0x0F3C), a(LDY,0x1172), a(STZ,J),
  'og:', ('jsr','jcell'), a(STX,T1), a(LDA,J)+[ASL,CLC,0x69,10,0]+a(ADC,KTI)+[TAX]+ll(0xBF,KTAB)+a(LDX,T1)+[0x9F,0x00,0x00,0x7F, TAX],
  a(LDA,J)+ai(1)+[CLC]+a(ADC,CX)+a(STA,T3), a(LDA,J)+[LSR,CLC]+a(ADC,CY)+a(STA,T4),
  a(LDA,T4)+ai(0x1F)+[ASL,ASL,ASL,ASL,ASL]+a(STA,T5)+a(LDA,T3)+ai(0x1F)+a(ORA,T5)+a(STA,T5),          # VRAM-Adresse BG1
  a(LDA,T4)+a(CMP,0x0F8E), ('bra8',0x90,'og2'), a(CMP,0x0F90), ('bra8',0xB0,'og2'),
  a(LDA,T3)+a(CMP,0x0F92), ('bra8',0x90,'og2'), a(CMP,0x0F94), ('bra8',0xB0,'og2'),
  [0xBF,0x00,0x00,0x7F, 0x99,0x76,0x11]+a(LDA,T5)+[0x99,0xF6,0x11], ('jsr','yinc'),
  'og2:', a(LDA,T4)+a(CMP,0x0F96), ('bra8',0x90,'og3'), a(CMP,0x0F98), ('bra8',0xB0,'og3'),
  a(LDA,T3)+a(CMP,0x0F9A), ('bra8',0x90,'og3'), a(CMP,0x0F9C), ('bra8',0xB0,'og3'),
  [0xBF,0x02,0x00,0x7F, 0x99,0x76,0x11]+a(LDA,T5)+[0x09,0x00,0x04, 0x99,0xF6,0x11], ('jsr','yinc'),
  'og3:', a(INC,J)+a(LDA,J)+ci(4), ('bra8',0xB0,'og_e'), ('jmp','og'),
  'og_e:', a(STY,0x1172), a(DEC,0x0F3C),
  # Schalter-Kiste
  a(LDA,KK), ('bra8',0xD0,'ob'), a(LDA,KSW), ('bra8',0xF0,'ob'),
  li(1)+ll(0x8F,STAIROK)+li(0x0FF9)+ll(0x8F,MSGP)+li(0x0FF8)+ll(0x8F,MSGI)+li(150)+ll(0x8F,MSGV), ('jmp','ok_r'),   # 2. Zeile verzoegert (soe_knoten kbild)
  # Waffen-Orb: (Zufall mod 200) < Stockwerk, hoechstens einer je Stockwerk
  'ob:', [0x22,0x9B,0x85,0x80]+a(EOR,0x0100)+a(EOR,0x4EA3)+ll(0x8F,0x004204)+SEP+[0xA9,200]+ll(0x8F,0x004206)+REP+NOP8+ll(0xAF,0x004216)+a(STA,T1),
  ll(0xAF,ORBTEST)+ci(0x4F52), ('bra8',0xD0,'ob1'), a(STZ,T1),
  'ob1:', ll(0xAF,FLOOR)+ai(0xFF)+a(CMP,T1), ('bra8',0x90,'ob_n'), ('bra8',0xF0,'ob_n'),
  ll(0xCF,ORBST), ('bra8',0xF0,'ob_n'), ll(0x8F,ORBST),
  a(LDA,0x0ABA)+ai(0xFF)+[0x22]+L(WINC)+li(0x0FFE)+ll(0x8F,MSGP), ('jmp','ok_r'),
  # Beute: 7E:2391 direkt (ohne Fundsachen-Zufall 8C:DBC9), Skript F4:8000 als Faden (wie 8C:D241 ab D257)
  'ob_n:', [0x22,0x9B,0x85,0x80]+a(EOR,0x0100)+ai(0x1F)+[ASL,TAX]+ll(0xBF,LOOT)+a(STA,0x2391),
  li(SKP&0xFFFF)+[0x85,0x26]+li(SKP>>16)+[0x85,0x28], [0x7A, 0xAB, 0x5C,0x57,0xD2,0x8C],
  'ok_r:', [0x7A, 0xAB, 0x6B],
  'yinc:', [INY,INY,0xC0,0x80,0x00], ('bra8',0xD0,'yi_r'), [0xA0,0x00,0x00], 'yi_r:', [0x60],
]
code, lab = assemble(CODE, t)
assert len(code) <= 0x2000, hex(len(code))
for adr, c in ((CODE, code), (KTAB, ktab), (BITS, bits), (LOOT, loot), (RTAB, rtab), (SKRIPT, skript)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
assert KTAB + len(ktab) <= BITS and BITS + len(bits) <= LOOT and LOOT + len(loot) <= RTAB and RTAB + len(rtab) <= 0xF44200
def jsl(l): x = lab[l]; return bytes([0x22, x&0xFF, (x>>8)&0xFF, x>>16])
def jml(l): x = lab[l]; return bytes([0x5C, x&0xFF, (x>>8)&0xFF, x>>16])
r[o9:o9+4] = jsl('fk')
r[oa:oa+4] = jml('ok')
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Kisten eingebaut (%d Bytes)" % len(code))
