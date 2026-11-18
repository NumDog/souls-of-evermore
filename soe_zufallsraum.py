# DarkSoulCave: echte Zufalls-Grundrisse (Prototyp v140, Max 18.11.: "mach jetzt mal random dungeons")
# Jeder Hoehlenraum (AKT != 0, Karte nicht 0x5E Treppenhaus und nicht 0x04 Brunnen) bekommt beim Betreten einen neuen Grundriss:
#  1. Hook 90:9270 (JSL $90A325): Tilemap 7F:0000 und Kombis 7F:[$0FAA] sind fertig, Grafik/Bild noch nicht geladen.
#  2. Kandidaten = begehbare Zellen der Ebene der Ankunftszelle (Form 0, keine Sonderbits 0x6140, nicht am Kartenrand).
#     Zustand je Zelle steckt waehrend der Arbeit in den unteren 3 Bits des Zellzeigers (Zeiger = $0FAA + 8i, also Bits 0-2 = $0FAA&7 = K fest):
#     0 = kein Kandidat (bleibt), 1 = Kandidat/Wand, 2 = gegraben (Boden), 4-7 = BFS besucht, Elternrichtung = Zustand-4.
#  3. Graben: Kreuz (3 Zellen je Richtung) um die Ankunft, dann Gaenge (3-10 Zellen geradeaus ab zufaelliger gegrabener Zelle)
#     und 3x3-Raeume (nur ueber Kandidaten) bis 3/8 der von der Ankunft aus erreichbaren Kandidaten (Flutfuellung).
#  4. Ausgaenge: BFS von allen gegrabenen Zellen ueber Kandidaten (Warteschlange 7F:B000-BFFF), dann fuer jeden kleinen
#     Lauf-Ausloeser der Karte (Liste [$1066], Laenge $1064, 6 Byte y1 x1 y2 x2 id, Ursprung $0F88/$0F8A) die Zellen im
#     Rechteck +1 Rand zurueck bis ins Netz graben (gleiche id nur einmal).
#  5. Schluss: gegraben -> Original-Kombi, Kandidat ungegraben -> Wand (haeufigste Form-F-Kombi der Karte, als 2x2-Muster).
#  6. Gegner (Objekte 7E:3DE5+k*8E, k<30, +60 >= 8000, +2A KP): 240 Bilder lang pro Bild pruefen, steckt einer in einer Wand
#     (Form != 0), auf eine zufaellige freie Zelle derselben Ebene (>= 64 px vom Jungen) setzen. Steckt der Junge in den
#     letzten 100 Bildern davon in einer Wand (Raumskript laeuft ihn hinein), kommt er auf die naechste gegrabene Zelle (8 Richtungen,
#     Radius 1-8, sonst die Ankunftszelle).
#  Begehbare Nicht-Kandidaten (Rampe 0x2000, 0x40, 0x4000) bleiben unveraendert, gelten aber fuer Gaenge/BFS als Weg (Zustand 3).
#  7. Ankunft: x/y px aus dem Stapel des Tuer-Befehls 22 (Ruecksprung 8C:DF85 suchen), Kopie in SRAM 30:7040/7042.
# Zufall: Spiel-RNG 80:859B ^ Bildzaehler 7E:0100 ^ Ankunftszelle als Startwert fuer xorshift16.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
def w(v): return [v&0xFF,(v>>8)&0xFF]
CODE = 0xF20000
AKT = 0x307002
# SRAM-Variablen (30:7040-705F)
ARX, ARY, ENZ, EBE, HSR, EXOK, CANDS, DUGS = 0x307040, 0x307042, 0x307044, 0x307046, 0x307048, 0x30704A, 0x30704C, 0x30704E
TCX, TCY, TT, TRY, MOVED, ZAEHL = 0x307050, 0x307052, 0x307054, 0x307056, 0x307058, 0x30705A
JX0, JY0, RAD = 0x30705C, 0x30705E, 0x307060
DXT, DYT = 0xF20F00, 0xF20F10     # 8 Richtungen (dx, dy) fuer die Suche nach freiem Boden
# Arbeitsvariablen in 7F:C200-C2FF (DB = 7F, absolut), Warteschlange 7F:B000-BFFF (geprueft: nach dem Laden nicht gelesen)
V = 0xC200
Wv, Hv, W2, FAA, Kv, Ev, ACv, AXv, AYv, RNG = [V+2*i for i in range(10)]
CUR, DIR, STEP, DUG, TGT, CAND, QH, QT, T1, T2 = [V+0x14+2*i for i in range(10)]
T9, Xv, Yv, ROW, P0, BESTN, BESTI, PHX, PHY, ABRT = [V+0x28+2*i for i in range(10)]
LEN, EI, IDv, NSEEN, X1, X2, Y1, Y2, XS, XE = [V+0x3C+2*i for i in range(10)]
YS, YE, CX, CY, HIT, OX, OY = [V+0x50+2*i for i in range(7)]
OFF = V+0x60     # 4 Woerter: +2, -2, +2W, -2W
WAL = V+0x68     # 4 Woerter: Wand-Muster (0,0) (1,0) (0,1) (1,1)
SEEN = V+0x80    # bis 32 ids
OFF8 = V+0xC0    # 8 Woerter: Nachbarn fuer 3x3-Raeume
MASK, LENC = V+0xD0, V+0xD2
MP, NB = V+0xD4, V+0xD6     # v141: Karte (Tabellen-Suche), Wand-Zaehlung nur mit Boden darunter (1) / alle (0)
ERL = 0xF20FC0     # v142: nur gemauerte Karten umbauen (Naturkarten mit Baum-/Buschwaenden sahen kaputt aus, Max-Bild 05)
ERL_DATEN = []   # v142 AUS (Max: "sieht katastrophal aus" - Einzelkachel-Tausch zerreisst grosse Wandgrafiken). Spaeter: eigene Kachelsaetze je Thema mit Auto-Kanten.
# ERL_DATEN = [0x28,0x29,0x0E,0x70,0x3A,0x4C]
KT = 0xF20F20     # v141: echte Startpunkte je Karte (Raumskript setzt den Jungen um): Karte, x, y; Ende FFFF
KT_DATEN = [(0x05,328,760),(0x28,264,1192),(0x70,56,312),(0x0E,264,360),(0x3A,88,216),(0x4F,216,600),(0x4C,176,504),(0x3E,208,328),(0x21,72,168),(0x68,392,704)]
Q = 0xB000
def a(op, adr): return [op]+w(adr)
LDA, STA, STZ, INC, DEC, CMP, ADC, SBC, EOR, ORA = 0xAD,0x8D,0x9C,0xEE,0xCE,0xCD,0x6D,0xED,0x4D,0x0D
LDX, LDY, STX, STY, CPX, CPY = 0xAE,0xAC,0x8E,0x8C,0xEC,0xCC
LDAX, STAX, LDAY, STAY, ADCY, STZX = 0xBD,0x9D,0xB9,0x99,0x79,0x9E
def li(v): return [0xA9]+w(v)          # LDA #
def ci(v): return [0xC9]+w(v)          # CMP #
def ai(v): return [0x29]+w(v)          # AND #
ASL, LSR, INA, DEA, INX, INY, DEX, DEY, TAX, TAY, TXA, TYA, CLC, SEC = 0x0A,0x4A,0x1A,0x3A,0xE8,0xC8,0xCA,0x88,0xAA,0xA8,0x8A,0x98,0x18,0x38

t = [
  # ================= Hook 90:9270
  'zr:', [0x22,0x25,0xA3,0x90, 0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B, 0xA9,0x00,0x00, 0x8F]+L(ENZ),   # v141: ENZ=0
  [0xAF]+L(AKT)+ai(0xFF), ('bra8',0xD0,'z_1'), ('jmp','raus'),
  'z_1:', [0xAF,0xDB,0x0A,0x7E]+ai(0xFF)+ci(0x5E), ('bra8',0xD0,'z_2'), ('jmp','raus'),
  'z_2:', ci(0x04), ('bra8',0xD0,'z_3'), ('jmp','raus'),
  # Ankunft: der Tuer-Befehl 22 (8C:DF82 JSL -> Tuer-Hook -> F0:0700 -> 90:8E95) liegt noch auf dem Stapel:
  # Ruecksprung 8C:DF85 (Bytes 85 DF 8C), direkt darueber y px und x px (vom Tuer-Hook schon angepasst)
  'z_3:', [0x48, 0xA2,0x00,0x00],
  'zw1:', [0xBF]+L(ERL)+ai(0xFF)+ci(0xFF), ('bra8',0xF0,'zw_n'), [0xC3,0x01], ('bra8',0xF0,'zw_j'), [INX], ('bra8',0x80,'zw1'),
  'zw_n:', [0x68], ('jmp','raus'),
  'zw_j:', [0x68, 0xBA, 0xA0,40,0x00],
  'sc:', [0xBF,0x01,0x00,0x00]+ci(0xDF85), ('bra8',0xD0,'sn'), [0xBF,0x03,0x00,0x00]+ai(0xFF)+ci(0x8C), ('bra8',0xD0,'sn'),
  [0xBF,0x04,0x00,0x00, 0x8F]+L(ARY)+[0xBF,0x06,0x00,0x00, 0x8F]+L(ARX), ('bra8',0x80,'sf'),
  'sn:', [INX, DEY], ('bra8',0xD0,'sc'), ('jmp','raus'),
  'sf:', [0xF4,0x7F,0x7F, 0xAB,0xAB],
  [0xAF,0xDB,0x0A,0x7E]+ai(0xFF)+a(STA,MP)+[0xA2,0x00,0x00],
  'kt:', [0xBF]+L(KT)+ci(0xFFFF), ('bra8',0xF0,'kt_e'), a(CMP,MP), ('bra8',0xF0,'kt_t'), [INX,INX,INX,INX,INX,INX], ('bra8',0x80,'kt'),
  'kt_t:', [0xBF]+L(KT+2)+[0x8F]+L(ARX)+[0xBF]+L(KT+4)+[0x8F]+L(ARY),
  'kt_e:',                                                          # DB = 7F
  [0xAF,0xEE,0x08,0x7E]+a(STA,Wv)+[ASL]+a(STA,W2), [0xAF,0xAA,0x0F,0x7E]+a(STA,FAA)+ai(7)+a(STA,Kv),
  a(LDA,FAA)+ci(0x9000), ('bra8',0x90,'z_4'), ('jmp','raus'),
  'z_4:', a(LDA,Wv)+ci(4), ('bra8',0xB0,'z_5'), ('jmp','raus'),
  'z_5:', a(STZ,Hv)+a(LDA,FAA),
  'dv:', a(CMP,W2), ('bra8',0x90,'dv_e'), a(SBC,W2)+a(INC,Hv), ('bra8',0x80,'dv'),
  'dv_e:', a(LDA,Hv)+ci(4), ('bra8',0xB0,'z_6'), ('jmp','raus'),
  'z_6:', a(LDA,Hv)+[0x8F]+L(HSR),
  [0xAF,0x88,0x0F,0x7E]+a(STA,OX)+[0xAF,0x8A,0x0F,0x7E]+a(STA,OY),
  li(2)+a(STA,OFF)+li(0xFFFE)+a(STA,OFF+2)+a(LDA,W2)+a(STA,OFF+4)+[0x49,0xFF,0xFF, INA]+a(STA,OFF+6),
  li(2)+a(STA,OFF8)+li(0xFFFE)+a(STA,OFF8+2)+a(LDA,W2)+a(STA,OFF8+4)+a(LDA,OFF+6)+a(STA,OFF8+6),
  a(LDA,W2)+[INA,INA]+a(STA,OFF8+8)+a(LDA,W2)+[DEA,DEA]+a(STA,OFF8+10)+a(LDA,OFF+6)+[INA,INA]+a(STA,OFF8+12)+a(LDA,OFF+6)+[DEA,DEA]+a(STA,OFF8+14),
  # Ankunftszelle (muss innen liegen)
  [0xAF]+L(ARX)+[LSR,LSR,LSR,LSR]+a(STA,AXv)+[0xAF]+L(ARY)+[LSR,LSR,LSR,LSR]+a(STA,AYv),
  a(LDA,AXv), ('bra8',0xF0,'z_r1'), [INA]+a(CMP,Wv), ('bra8',0xB0,'z_r1'),
  a(LDA,AYv), ('bra8',0xF0,'z_r1'), [INA]+a(CMP,Hv), ('bra8',0x90,'z_7'),
  'z_r1:', ('jmp','raus'),
  'z_7:', a(LDA,AXv)+[ASL]+a(LDX,AYv),
  'm1:', ('bra8',0xF0,'m2'), [CLC]+a(ADC,W2)+[DEX], ('bra8',0x80,'m1'),
  'm2:', a(STA,ACv)+[TAX]+a(LDAX,0)+[TAY]+a(LDAY,4)+ai(0x30)+a(STA,Ev)+[0x8F]+L(EBE),
  # Startwert
  [0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB, 0x22,0x9B,0x85,0x80, 0xAB, 0x4F,0x00,0x01,0x7E]+a(EOR,ACv)+[0x4F]+L(ARY),
  ('bra8',0xD0,'s_1'), li(0xACE1), 's_1:', a(STA,RNG),
  # ---- Wand: haeufigste Form-F-Kombi zaehlen (Zaehler in Q)
  li(1)+a(STA,NB),
  'c00:', [0xA2]+w(0x0FFE), 'c0:', a(STZX,Q)+[DEX,DEX], ('bra8',0x10,'c0'),
  [0xA2,0x00,0x00],
  'c1:', a(LDAX,0)+[TAY]+a(LDAY,4)+ai(0xF)+ci(0xF), ('bra8',0xD0,'c2'),
  a(LDA,NB), ('bra8',0xF0,'c1z'), a(STY,T1)+[TXA,CLC]+a(ADC,W2)+a(ADC,W2)+a(CMP,FAA), ('bra8',0xB0,'c2'),
  [TAY]+a(LDAY,0)+[TAY]+a(LDAY,4)+ai(0xF), ('bra8',0xD0,'c2'), a(LDY,T1),
  'c1z:',
  [TYA, SEC]+a(SBC,FAA)+[LSR,LSR]+ci(0x1000), ('bra8',0xB0,'c2'), [TAY]+a(LDAY,Q)+[INA]+a(STAY,Q),
  'c2:', [INX,INX]+a(CPX,FAA), ('bra8',0x90,'c1'),
  a(STZ,BESTN)+a(STZ,BESTI)+[0xA0,0x00,0x00],
  'c3:', a(LDAY,Q)+a(CMP,BESTN), ('bra8',0x90,'c4'), ('bra8',0xF0,'c4'), a(STA,BESTN)+a(STY,BESTI),
  'c4:', [INY,INY, 0xC0]+w(0x1000), ('bra8',0x90,'c3'),
  a(LDA,BESTN), ('bra8',0xD0,'c5'), a(LDA,NB), ('bra8',0xD0,'c6'), ('jmp','raus'),
  'c6:', a(STZ,NB), ('jmp','c00'),
  'c5:', a(LDA,BESTI)+[ASL,ASL,CLC]+a(ADC,FAA)+a(STA,P0),
  a(STA,WAL)+a(STA,WAL+2)+a(STA,WAL+4)+a(STA,WAL+6)+a(STZ,PHX)+a(STZ,PHY),
  # 2x2-Muster suchen: Zelle P0 mit Form F rechts, unten, unten rechts
  a(STZ,Yv)+[0xA2,0x00,0x00],
  'p1:', a(STX,ROW)+a(STZ,Xv),
  'p2:', a(LDAX,0)+a(CMP,P0), ('bra8',0xD0,'p3'),
  a(LDAX,2)+[TAY]+a(LDAY,4)+ai(0xF)+ci(0xF), ('bra8',0xD0,'p3'),
  [TXA,CLC]+a(ADC,W2)+[TAY]+a(LDAY,0)+a(STA,T1)+a(LDAY,2)+a(STA,T2),
  a(LDY,T1)+a(LDAY,4)+ai(0xF)+ci(0xF), ('bra8',0xD0,'p3'),
  a(LDY,T2)+a(LDAY,4)+ai(0xF)+ci(0xF), ('bra8',0xD0,'p3'),
  a(LDAX,2)+a(STA,WAL+2)+a(LDA,T1)+a(STA,WAL+4)+a(LDA,T2)+a(STA,WAL+6),
  a(LDA,Xv)+ai(1)+a(STA,PHX)+a(LDA,Yv)+ai(1)+a(STA,PHY), ('jmp','pf'),
  'p3:', [INX,INX]+a(INC,Xv)+a(LDA,Xv)+[INA]+a(CMP,Wv), ('bra8',0x90,'p2'),
  a(LDA,ROW)+[CLC]+a(ADC,W2)+[TAX]+a(INC,Yv)+a(LDA,Yv)+[INA]+a(CMP,Hv), ('bra8',0xB0,'pf'), ('jmp','p1'),
  'pf:',
  # ---- Durchgang 1: Kandidaten markieren, alle Zeiger normieren (Bits 0-2 = Zustand)
  a(STZ,CAND)+a(STZ,ABRT)+a(STZ,Yv)+[0xA2,0x00,0x00],
  'q1:', a(STX,ROW)+a(STZ,Xv),
  'q2:', a(LDAX,0)+[TAY]+ai(0xFFF8)+a(STA,T1),
  a(LDA,Xv), ('bra8',0xF0,'qn'), [INA]+a(CMP,Wv), ('bra8',0xB0,'qn'),
  a(LDA,Yv), ('bra8',0xF0,'qn'), [INA]+a(CMP,Hv), ('bra8',0xB0,'qn'),
  a(LDAY,4)+ai(0x614F), ('bra8',0xD0,'qp'), a(LDAY,4)+ai(0x30)+a(CMP,Ev), ('bra8',0xD0,'qp'),
  a(LDA,T1)+[0x09,0x01,0x00]+a(STAX,0)+a(INC,CAND), ('bra8',0x80,'q3'),
  # begehbar, aber nicht umbaubar (Rampe 0x2000, Sonderfall 0x40, Ausgang 0x4000): Zustand 3, BFS darf durch
  'qp:', a(LDAY,4)+ai(0x010F), ('bra8',0xD0,'qn'), a(LDAY,4)+ai(0x2040), ('bra8',0xD0,'qp3'), a(LDAY,4)+ai(0x30)+a(CMP,Ev), ('bra8',0xD0,'qn'),
  'qp3:', a(LDA,T1)+[0x09,0x03,0x00]+a(STAX,0), ('bra8',0x80,'q3'),
  'qn:', a(LDA,T1)+a(STAX,0),
  'q3:', [INX,INX]+a(INC,Xv)+a(LDA,Xv)+a(CMP,Wv), ('bra8',0x90,'q2'),
  a(LDA,ROW)+[CLC]+a(ADC,W2)+[TAX]+a(INC,Yv)+a(LDA,Yv)+a(CMP,Hv), ('bra8',0xB0,'q4'), ('jmp','q1'),
  'q4:',
  # Flutfuellung ab der Ankunft: wie viele Kandidaten sind von hier ueberhaupt erreichbar (R)? Markierung 4/5, danach zurueck auf 1/3
  a(STZ,QH)+a(STZ,QT)+a(STZ,T2)+a(LDA,ACv), ('jsr','push'),
  'fl1:', a(LDA,QH)+a(CMP,QT), ('bra8',0xF0,'flf'),
  [TAY]+a(LDAY,Q)+a(STA,CUR)+[TYA,CLC,0x69,0x02,0x00]+ai(0x0FFF)+a(STA,QH)+[0xA0,0x00,0x00],
  'fl2:', a(LDA,CUR)+[CLC]+a(ADCY,OFF)+[TAX]+a(LDAX,0)+ai(7)+ci(1), ('bra8',0xF0,'fl_c'), ci(3), ('bra8',0xD0,'fl_n'),
  a(LDAX,0)+ai(0xFFF8)+[0x09,0x05,0x00]+a(STAX,0), ('bra8',0x80,'fl_p'),
  'fl_c:', a(LDAX,0)+ai(0xFFF8)+[0x09,0x04,0x00]+a(STAX,0)+a(INC,T2),
  'fl_p:', [TXA,0x5A], ('jsr','push'), [0x7A],
  'fl_n:', [INY,INY,0xC0,0x08,0x00], ('bra8',0x90,'fl2'), ('bra8',0x80,'fl1'),
  'flf:', [0xA2,0x00,0x00],
  'fr:', a(LDAX,0)+ai(7)+ci(4), ('bra8',0xD0,'fr1'), a(LDAX,0)+ai(0xFFF8)+[0x09,0x01,0x00]+a(STAX,0), ('bra8',0x80,'fr2'),
  'fr1:', ci(5), ('bra8',0xD0,'fr2'), a(LDAX,0)+ai(0xFFF8)+[0x09,0x03,0x00]+a(STAX,0),
  'fr2:', [INX,INX]+a(CPX,FAA), ('bra8',0x90,'fr'),
  a(LDA,T2)+[0x8F]+L(CANDS),
  # Ziel = 3/8 der erreichbaren Kandidaten, hoechstens 1600
  a(LDA,T2)+[LSR,LSR,LSR]+a(STA,T1)+[ASL,CLC]+a(ADC,T1)+ci(1600), ('bra8',0x90,'tg'), li(1600), 'tg:', a(STA,TGT),
  # ---- Kreuz um die Ankunft
  a(STZ,DUG)+a(LDX,ACv), ('jsr','graben'), [0xA0,0x00,0x00],
  'k1:', a(LDX,ACv)+li(3)+a(STA,T1),
  'k2:', [TXA,CLC]+a(ADCY,OFF)+[TAX]+a(LDAX,0)+ai(7), ('bra8',0xF0,'k3'), ('jsr','graben'), a(DEC,T1), ('bra8',0xD0,'k2'),
  'k3:', [INY,INY, 0xC0,0x08,0x00], ('bra8',0x90,'k1'),
  a(LDA,DUG), ('bra8',0xD0,'k4'), li(1)+a(STA,ABRT), ('jmp','fin'),
  # ---- Gaenge + Raeume: zufaellige gegrabene Zelle (Liste in Q), Gang 3-10 Zellen geradeaus (nur Kandidaten),
  #      am Ende mit 1/4 ein 3x3-Raum. Bis 3/8 der erreichbaren Kandidaten gegraben sind (hoechstens 1600) oder 2000 Versuche.
  'k4:', li(2000)+a(STA,STEP),
  'wl:', a(LDA,DUG)+a(CMP,TGT), ('bra8',0xB0,'wfj'), a(DEC,STEP), ('bra8',0xD0,'w0'), 'wfj:', ('jmp','wf'),
  'w0:', li(1)+a(STA,MASK),
  'wm:', a(LDA,MASK)+a(CMP,DUG), ('bra8',0xB0,'wme'), [ASL,0x09,0x01,0x00]+a(STA,MASK), ('bra8',0x80,'wm'),
  'wme:', ('jsr','rnd'), a(0x2D,MASK)+a(CMP,DUG), ('bra8',0xB0,'wl'),
  [ASL,TAY]+a(LDAY,Q)+a(STA,CUR), ('jsr','rnd'), ai(6)+a(STA,DIR), ('jsr','rnd'), ai(7)+[CLC,0x69,0x03,0x00]+a(STA,LENC),
  'wc:', a(LDY,DIR)+a(LDA,CUR)+[CLC]+a(ADCY,OFF)+[TAX]+a(LDAX,0)+ai(7), ('bra8',0xF0,'we'),
  a(STX,CUR), ('jsr','graben'), a(DEC,LENC), ('bra8',0xD0,'wc'),
  'we:', ('jsr','rnd'), ai(3), ('bra8',0xD0,'wl'), [0xA0,0x00,0x00],
  'wr:', a(LDA,CUR)+[CLC]+a(ADCY,OFF8)+[TAX], ('jsr','graben'), [INY,INY,0xC0,0x10,0x00], ('bra8',0x90,'wr'), ('jmp','wl'),
  'wf:',
  # ---- BFS von allen gegrabenen Zellen
  a(STZ,QH)+a(STZ,QT)+[0xA2,0x00,0x00],
  'b0:', a(LDAX,0)+ai(7)+ci(2), ('bra8',0xD0,'b1'), [TXA], ('jsr','push'),
  'b1:', [INX,INX]+a(CPX,FAA), ('bra8',0x90,'b0'),
  'b2:', a(LDA,QH)+a(CMP,QT), ('bra8',0xF0,'bf'),
  [TAY]+a(LDAY,Q)+a(STA,CUR)+[TYA,CLC]+[0x69,0x02,0x00]+ai(0x0FFF)+a(STA,QH)+[0xA0,0x00,0x00],
  'b3:', a(LDA,CUR)+[CLC]+a(ADCY,OFF)+[TAX]+a(LDAX,0)+ai(7)+ci(1), ('bra8',0xF0,'b_v'), ci(3), ('bra8',0xD0,'b4'),
  # begehbare Nicht-Kandidaten-Zelle erreicht: Weg bis hierher graben, Zelle zaehlt ab jetzt als Netz
  [0x5A,0xDA]+a(LDX,CUR), ('jsr','spur'), [0xFA,0x7A]+a(LDAX,0)+ai(0xFFF8)+[0x09,0x02,0x00]+a(STAX,0)+[TXA,0x5A], ('jsr','push'), [0x7A], ('bra8',0x80,'b4'),
  'b_v:', [TYA,LSR]+[0x49,0x01,0x00]+[0x09,0x04,0x00]+a(STA,T1)+a(LDAX,0)+ai(0xFFF8)+a(ORA,T1)+a(STAX,0),
  [TXA,0x5A], ('jsr','push'), [0x7A],
  'b4:', [INY,INY,0xC0,0x08,0x00], ('bra8',0x90,'b3'), ('bra8',0x80,'b2'),
  'bf:',
  # ---- Ausgaenge (Lauf-Ausloeser)
  [0xAF,0x66,0x10,0x7E, 0x85,0x26, 0xAF,0x67,0x10,0x7E, 0x85,0x27, 0xAF,0x64,0x10,0x7E]+a(STA,LEN),
  a(STZ,EI)+a(STZ,NSEEN)+[0xA9,0,0, 0x8F]+L(EXOK),
  'e1:', a(LDA,EI)+a(CMP,LEN), ('bra8',0x90,'e2'), ('jmp','fin'),
  'e2:', [TAY,INY,INY,INY,INY, 0xB7,0x26]+a(STA,IDv)+[0xA2,0x00,0x00],
  'e3:', a(CPX,NSEEN), ('bra8',0xB0,'e4'), a(LDAX,SEEN)+a(CMP,IDv), ('bra8',0xD0,'e3n'), ('jmp','en'), 'e3n:', [INX,INX], ('bra8',0x80,'e3'),
  'e4:', [0xE0,0x40,0x00], ('bra8',0xB0,'e5'), a(LDA,IDv)+a(STAX,SEEN)+[INX,INX]+a(STX,NSEEN),
  'e5:', a(LDY,EI)+[0xB7,0x26]+ai(0xFF)+[SEC]+a(SBC,OY)+a(STA,Y1),
  [INY,0xB7,0x26]+ai(0xFF)+[SEC]+a(SBC,OX)+a(STA,X1),
  [INY,0xB7,0x26]+ai(0xFF)+[SEC]+a(SBC,OY)+a(STA,Y2),
  [INY,0xB7,0x26]+ai(0xFF)+[SEC]+a(SBC,OX)+a(STA,X2),
  a(LDA,X2)+[SEC]+a(SBC,X1)+[DEA]+ci(6), ('bra8',0x90,'e6'), ('jmp','en'),
  'e6:', a(LDA,Y2)+[SEC]+a(SBC,Y1)+[DEA]+ci(6), ('bra8',0x90,'e7'), ('jmp','en'),
  'e7:', a(LDA,X1)+[DEA], ('bra8',0x30,'e8'), ('bra8',0xD0,'e9'), 'e8:', li(1), 'e9:', a(STA,XS),
  a(LDA,Wv)+[DEA,DEA]+a(STA,T1)+a(LDA,X2), ('bra8',0x10,'e10'), ('jmp','en'), 'e10:', a(CMP,T1), ('bra8',0x90,'e11'), a(LDA,T1), 'e11:', a(STA,XE),
  a(LDA,Y1)+[DEA], ('bra8',0x30,'e12'), ('bra8',0xD0,'e13'), 'e12:', li(1), 'e13:', a(STA,YS),
  a(LDA,Hv)+[DEA,DEA]+a(STA,T1)+a(LDA,Y2), ('bra8',0x10,'e14'), ('jmp','en'), 'e14:', a(CMP,T1), ('bra8',0x90,'e15'), a(LDA,T1), 'e15:', a(STA,YE),
  a(LDA,XE)+a(CMP,XS), ('bra8',0xB0,'e16'), ('jmp','en'), 'e16:', a(LDA,YE)+a(CMP,YS), ('bra8',0xB0,'e17'), ('jmp','en'),
  'e17:', a(STZ,HIT)+a(LDA,YS)+a(STA,CY),
  'r1:', li(0)+a(LDX,CY),
  'r1m:', ('bra8',0xF0,'r2'), [CLC]+a(ADC,W2)+[DEX], ('bra8',0x80,'r1m'),
  'r2:', a(STA,ROW)+a(LDA,XS)+a(STA,CX),
  'r3:', a(LDA,CX)+[ASL,CLC]+a(ADC,ROW)+[TAX]+a(LDAX,0)+ai(7)+ci(2), ('bra8',0xF0,'r3h'), ci(4), ('bra8',0x90,'r4'),
  ('jsr','spur'), 'r3h:', li(1)+a(STA,HIT),
  'r4:', a(INC,CX)+a(LDA,XE)+a(CMP,CX), ('bra8',0xB0,'r3'),
  a(INC,CY)+a(LDA,YE)+a(CMP,CY), ('bra8',0xB0,'r1'),
  a(LDA,HIT), ('bra8',0xF0,'en'), [0xAF]+L(EXOK)+[INA,0x8F]+L(EXOK),
  'en:', a(LDA,EI)+[CLC,0x69,0x06,0x00]+a(STA,EI), ('jmp','e1'),
  # ---- Schluss: Zeiger zurueck bzw. Wand
  'fin:', a(LDA,DUG)+[0x8F]+L(DUGS)+a(STZ,Yv)+[0xA2,0x00,0x00],
  'f1:', a(STX,ROW)+a(STZ,Xv),
  'f2:', a(LDA,ABRT), ('bra8',0xD0,'fb'), a(LDAX,0)+ai(7)+ci(1), ('bra8',0xF0,'fw'), ci(4), ('bra8',0xB0,'fw'),
  'fb:', a(LDAX,0)+ai(0xFFF8)+a(ORA,Kv)+a(STAX,0), ('bra8',0x80,'f3'),
  'fw:', a(LDA,Xv)+a(EOR,PHX)+ai(1)+a(STA,T1)+a(LDA,Yv)+a(EOR,PHY)+ai(1)+[ASL]+a(ORA,T1)+[ASL,TAY]+a(LDAY,WAL)+a(STAX,0),
  'f3:', [INX,INX]+a(INC,Xv)+a(LDA,Xv)+a(CMP,Wv), ('bra8',0x90,'f2'),
  a(LDA,ROW)+[CLC]+a(ADC,W2)+[TAX]+a(INC,Yv)+a(LDA,Yv)+a(CMP,Hv), ('bra8',0xB0,'f4'), ('jmp','f1'),
  'f4:', li(240)+[0x8F]+L(ENZ)+[0xAF]+L(ZAEHL)+[INA,0x8F]+L(ZAEHL)+li(0)+[0x8F]+L(MOVED),
  'raus:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  # ---- Unterprogramme (DB = 7F)
  'graben:', a(LDAX,0)+ai(7)+ci(1), ('bra8',0xF0,'g_d'), ci(4), ('bra8',0x90,'g_r'),
  'g_d:', a(LDAX,0)+ai(0xFFF8)+[0x09,0x02,0x00]+a(STAX,0)+[0x5A]+a(LDA,DUG)+ci(0x800), ('bra8',0xB0,'g_n'), [ASL,TAY,TXA]+a(STAY,Q),
  'g_n:', [0x7A]+a(INC,DUG), 'g_r:', [0x60],
  'spur:', a(LDAX,0)+ai(7)+ci(4), ('bra8',0x90,'sp_r'), [SEC,0xE9,0x04,0x00,ASL,TAY],
  a(LDAX,0)+ai(0xFFF8)+[0x09,0x02,0x00]+a(STAX,0)+a(INC,DUG)+[TXA,CLC]+a(ADCY,OFF)+[TAX], ('bra8',0x80,'spur'),
  'sp_r:', [0x60],
  'push:', [0x48]+a(LDA,QT)+[CLC,0x69,0x02,0x00]+ai(0x0FFF)+a(CMP,QH), ('bra8',0xF0,'pu_v'),
  a(LDY,QT)+a(STA,QT)+[0x68]+a(STAY,Q)+[0x60], 'pu_v:', [0x68, 0x60],
  'rnd:', a(LDA,RNG)+a(STA,T9)+[ASL]*7+a(EOR,T9)+a(STA,T9)+[0xEB]+ai(0xFF)+[LSR]+a(EOR,T9)+a(STA,T9)+[0xEB]+ai(0xFF00)+a(EOR,T9)+a(STA,RNG)+[0x60],


  # ================= jedes Bild: steckende Gegner versetzen
  'bild:', [0x22,0,0,0],          # VORHER (wird unten eingesetzt)
  [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB],
  [0xAF]+L(ENZ), ('bra8',0xD0,'zb1'), ('jmp','zb_r'),
  'zb1:', [DEA, 0x8F]+L(ENZ)+[0xAF]+L(AKT)+ai(0xFF), ('bra8',0xD0,'zb2'), [0x8F]+L(ENZ), ('jmp','zb_r'),
  'zb2:', [0xA2]+w(0x3DE5),
  'z2:', a(LDAX,0x60), ('bra8',0x10,'z9'), a(LDAX,0x2A), ('bra8',0xF0,'z9'),
  a(LDAX,0x1A)+[LSR,LSR,LSR,LSR,0x8F]+L(TCX)+a(LDAX,0x1C)+[LSR,LSR,LSR,LSR,0x8F]+L(TCY),
  ('jsr','zelle'), ci(0xFFFF), ('bra8',0xF0,'z9'), ai(0xF)+ci(0xF), ('bra8',0xD0,'z9'),   # v141: nur volle Wand (Form F), Schraegen sind begehbar
  ('jsr','vers'),
  'z9:', [TXA,CLC,0x69,0x8E,0x00,TAX, 0xE0]+w(0x4E89), ('bra8',0x90,'z2'),
  # Junge (Objekt 4E89) in einer Wand (z. B. vom Raumskript hineingelaufen)? In den letzten 100 Bildern -> naechste freie Zelle
  [0xAF]+L(ENZ)+ci(100), ('bra8',0x90,'zj1'), ('jmp','zb_r'),
  'zj1:', a(LDA,0x4EA3)+[LSR,LSR,LSR,LSR,0x8F]+L(TCX)+[0x8F]+L(JX0)+a(LDA,0x4EA5)+[LSR,LSR,LSR,LSR,0x8F]+L(TCY)+[0x8F]+L(JY0),
  ('jsr','zelle'), ci(0xFFFF), ('bra8',0xD0,'zj2'), ('jmp','zb_r'), 'zj2:', ai(0xF)+ci(0xF), ('bra8',0xF0,'zj3'), ('jmp','zb_r'),
  'zj3:', li(1)+[0x8F]+L(RAD),
  'js1:', [0xA2,0x00,0x00],
  'js2:', [0xAF]+L(RAD)+[TAY,0xAF]+L(JX0), 'js3:', [CLC,0x7F]+L(DXT)+[DEY], ('bra8',0xD0,'js3'), [0x8F]+L(TCX),
  [0xAF]+L(RAD)+[TAY,0xAF]+L(JY0), 'js4:', [CLC,0x7F]+L(DYT)+[DEY], ('bra8',0xD0,'js4'), [0x8F]+L(TCY),
  [0xDA], ('jsr','zelle'), [0xFA]+ci(0xFFFF), ('bra8',0xF0,'jsn'), [0x48]+ai(0x614F), ('bra8',0xD0,'jsp'), [0x68]+ai(0x30)+[0xCF]+L(EBE), ('bra8',0xD0,'jsn'),
  [0xA2]+w(0x4E89), ('jsr','setz'), [0xAF]+L(MOVED)+[CLC,0x69,0x00,0x01,0x8F]+L(MOVED), ('jmp','zb_r'),
  'jsp:', [0x68],
  'jsn:', [INX,INX,0xE0,0x10,0x00], ('bra8',0x90,'js2'), [0xAF]+L(RAD)+[INA,0x8F]+L(RAD)+ci(9), ('bra8',0xB0,'jsa'), ('jmp','js1'),
  # nichts in Reichweite: zurueck auf die Ankunftszelle
  'jsa:', [0xAF]+L(ARX)+[LSR,LSR,LSR,LSR,0x8F]+L(TCX)+[0xAF]+L(ARY)+[LSR,LSR,LSR,LSR,0x8F]+L(TCY), ('jsr','zelle'), ci(0xFFFF), ('bra8',0xF0,'zb_r'),
  [0xA2]+w(0x4E89), ('jsr','setz'), [0xAF]+L(MOVED)+[CLC,0x69,0x00,0x10,0x8F]+L(MOVED),
  'zb_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  # zelle: A = Attribut der Zelle (TCX,TCY) oder FFFF; TT = Tilemap-Offset. X bleibt.
  'zelle:', [0xAF]+L(TCX)+a(CMP,0x08EE), ('bra8',0xB0,'zl_f'), [0xAF]+L(TCY)+[0xCF]+L(HSR), ('bra8',0xB0,'zl_f'),
  [0xE2,0x20, 0xAF]+L(TCY)+[0x8F,0x02,0x42,0x00]+a(LDA,0x08EE)+[0x8F,0x03,0x42,0x00, 0xC2,0x20, 0xEA,0xEA,0xEA,0xEA],
  [0xAF,0x16,0x42,0x00, CLC, 0x6F]+L(TCX)+[ASL, 0x8F]+L(TT)+[0xDA, TAX, 0xBF,0x00,0x00,0x7F, TAX, 0xBF,0x04,0x00,0x7F, 0xFA, 0x60],
  'zl_f:', li(0xFFFF)+[0x60],
  # vers: Objekt X auf freie Zelle setzen (bis 40 Versuche)
  'vers:', li(40)+[0x8F]+L(TRY),
  'v1:', ('jsr','zrnd'), ai(0x7F)+[0x8F]+L(TCX)+a(CMP,0x08EE), ('bra8',0x90,'vf1'), ('jmp','vn'), 'vf1:',
  ('jsr','zrnd'), ai(0x7F)+[0x8F]+L(TCY)+[0xCF]+L(HSR), ('bra8',0x90,'vf2'), ('jmp','vn'), 'vf2:',
  [0xAF]+L(TCX), ('bra8',0xD0,'vf3'), ('jmp','vn'), 'vf3:', [0xAF]+L(TCY), ('bra8',0xD0,'vf4'), ('jmp','vn'), 'vf4:',
  ('jsr','zelle'), ci(0xFFFF), ('bra8',0xD0,'vf5'), ('jmp','vn'), 'vf5:', [0x48]+ai(0x614F), ('bra8',0xF0,'vq'), ('jmp','vp'), 'vq:', [0x68]+ai(0x30)+[0xCF]+L(EBE), ('bra8',0xF0,'vok0'), ('jmp','vn'), 'vok0:',
  # Abstand zum Jungen >= 64 px
  [0xAF]+L(TCX)+[ASL,ASL,ASL,ASL,SEC]+a(0xED,0x4EA3), ('bra8',0x10,'va'), [0x49,0xFF,0xFF,INA], 'va:', [0x48],
  [0xAF]+L(TCY)+[ASL,ASL,ASL,ASL,SEC]+a(0xED,0x4EA5), ('bra8',0x10,'vb'), [0x49,0xFF,0xFF,INA], 'vb:', [CLC,0x63,0x01, 0x83,0x01, 0x68], ci(64), ('bra8',0xB0,'vok'), ('jmp','vn'), 'vok:',
  ('jsr','setz'), [0xAF]+L(MOVED)+[INA,0x8F]+L(MOVED)+[0x60],
  # setz: Objekt X auf Zelle (TCX,TCY) setzen (TT = Tilemap-Offset aus 'zelle'), wie 8F:C2A6ff
  'setz:', [0xAF]+L(TCX)+[ASL,ASL,ASL,ASL,0x09,0x08,0x00]+a(STAX,0x1A)+[0xAF]+L(TCY)+[ASL,ASL,ASL,ASL,0x09,0x08,0x00]+a(STAX,0x1C),
  [0xAF]+L(TCY)+[0xEB, 0x0F]+L(TCX)+a(STAX,0x62)+[0xAF]+L(TT)+a(STAX,0x3A)+[0xDA,TAX,0xBF,0x00,0x00,0x7F,TAX,0xBF,0x04,0x00,0x7F,0xFA]+a(STAX,0x3C)+[0x60],
  'vp:', [0x68],
  'vn:', [0xAF]+L(TRY)+[DEA,0x8F]+L(TRY), ('bra8',0xF0,'vr'), ('jmp','v1'), 'vr:', [0x60],
  'zrnd:', [0xDA, 0x22,0x9B,0x85,0x80, 0xFA, 0x4D,0x00,0x01, 0x60],
]
code, lab = assemble(CODE, t)
assert len(code) <= 0x1000, hex(len(code))
assert CODE+len(code) <= DXT
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), "F2:0000 belegt"
r[o:o+len(code)] = code
RICHT = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
for adr, werte in ((DXT, [x for x,_ in RICHT]), (DYT, [y for _,y in RICHT])):
    b = b''.join((v & 0xFFFF).to_bytes(2,'little') for v in werte); o = at(adr); assert all(x == 0xFF for x in r[o:o+16]); r[o:o+16] = b
kt = b''.join(m.to_bytes(2,'little')+x.to_bytes(2,'little')+y.to_bytes(2,'little') for m,x,y in KT_DATEN) + b'\xFF\xFF'
o = at(ERL); assert all(x == 0xFF for x in r[o:o+len(ERL_DATEN)+1]); r[o:o+len(ERL_DATEN)+1] = bytes(ERL_DATEN+[0xFF])
o = at(KT); assert len(kt) <= 0xE0 and all(x == 0xFF for x in r[o:o+len(kt)]); r[o:o+len(kt)] = kt
def jsl(lbl): x = lab[lbl]; return [0x22, x&0xFF, (x>>8)&0xFF, x>>16]
# Hauptschleifen-Kette F0:4000: bisheriges Ziel in 'bild' einsetzen
o0 = at(0xF04000); assert r[o0] == 0x22; vorher = bytes(r[o0+1:o0+4])
ob = at(lab['bild']); r[ob+1:ob+4] = vorher; r[o0:o0+4] = bytes(jsl('bild'))
# Hook 90:9270
o = at(0x909270); assert bytes(r[o:o+4]) == bytes([0x22,0x25,0xA3,0x90]), bytes(r[o:o+4]).hex(); r[o:o+4] = bytes(jsl('zr'))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Zufallsraum eingebaut (%d Bytes)" % len(code))
