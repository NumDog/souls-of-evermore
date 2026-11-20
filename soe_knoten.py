import os
# DarkSoulCave v145 (Max: "erst mit den fertig geprueften Karten"), Bank F3:0000-2FFF (Code) + F7:0000-0FFF (Tabellen).
# Ersetzt v143/v144 (Kisten/Schalter/SCHALTG/STAIROK sind weg, soe_funde ist nicht mehr im Bau).
#  - Schachbrett 5E = Knoten mit vier Zugaengen: links (Tuer nach 5F, x<400), rechts (5F, x>=400), unten (5D), OBEN = Positions-
#    Ausloeser im Bild-Hook (x160-191 / y200-231, nur beim frischen Betreten des Bereichs; die alte Tuer 1032 ist zu Fuss unerreichbar).
#  - Jeder Zugang -> zufaelliger Raum aus dem GEPRUEFTEN POOL (40 Ankuenfte, jedes Betreten neu gewuerfelt, Ankunft exakt mit 238F=0).
#    Jede Tuer im Pool-Raum -> zurueck auf 5E vor den benutzten Zugang.
#  - Saeuberung: alle Monster tot (kein lebender Gegner in den Objekt-Plaetzen ausserhalb der Freiliste UND kein Eintrag der
#    Spawnliste 7E:5DC3.. mit Rest-Anzahl +0C > 0) -> "Der Raum ist gesaeubert!", 150 Bilder spaeter zum Schachbrett vor den Zugang,
#    Zugang versiegelt (Bit in SIEGEL). Respawn: in Hoehlen-Raeumen wird die Anzahl je Spawn-Eintrag auf 1 begrenzt (Hook 8F:DE7C);
#    getoetete Gegner kommen nicht wieder (Eintrag bleibt 0), weggelaufene (despawnte) zaehlen wieder als offen (Mesen: Karte 12).
#    Notfall: Raum ohne jeden Gegner und ohne Spawn-Eintrag gilt nach 300 Bildern als gesaeubert.
#  - Versiegelter Zugang -> "Dieser Zugang ist versiegelt." und man bleibt auf 5E (Landestelle vor dem Zugang).
#  - Boss nur auf Stockwerk 5, 10, 15 ... : OBEN -> Bossraum (zufaellig aus 5 Bossen mit gemessenem Sieg-Flag), Flag-Sicherung BSNAP
#    (7E:2258-2347 -> 30:7400), Sieg-Flag geloescht. Sieg (Flag wieder gesetzt, 240 Bilder) -> Flags zurueck (ohne Formeln/Talismane/
#    Waffen+N/Waffenbesitz), Boss erledigt (SIEGEL Bit 4), Waffen-Orb + Meldung, zurueck vor den oberen Zugang. Tuer = Flucht (Flags
#    zurueck, Boss bleibt offen). Tod: soe_hoehle 'verlassen' ruft kverl (Flags zurueck). Bosswerte: KP x8, Angriff/Abwehr x1,5 ueber
#    den Vorlagen-Zeiger (soe_hoehle stat -> kbkp/kbatk).
#  - Treppe (Mitte, Ziel 0x60) nur offen, wenn SIEGEL Bits 1-4 alle gesetzt (normal: 4 Raeume; Boss-Ebene: 3 Raeume + Boss).
#  - Original-Loot: Fund-Merker (Story-Flags) der Truhen/Kuerbisse/Schnueffelstellen des Pool-Raums werden beim Betreten gesichert und
#    geloescht, beim Verlassen (Tuer, Saeuberung, Tod, Gotteshand) zurueckgeschrieben.
#  - Monster-Beute: jeder Sieg in der Hoehle (soe_hoehle FUND) -> 100 % Beute (Zutat/Verbrauchsgut, Meldung "X gefunden!" ueber das
#    Spiel-Skript a3 3e/3f), davon 1 % selten: Formel / Waffe / Talisman / Ruestung, die man noch nicht hat (sonst Waffen-Orb).
#  - Meldungs-Warteschlange (16 Eintraege): Text-IDs und Beute werden nacheinander gezeigt (Abstand QABST Bilder).
# Vektoren (feste Adressen, soe_hoehle ruft sie): F3:0000 kt (Tuer), 0004 kverl, 0008 kns (neues Stockwerk), 000C qpl (A = Meldung),
# 0010 kdrop (Sieg), 0014 kbkp, 0018 kbatk, 001C kcap.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
def w(v): return [v&0xFF,(v>>8)&0xFF]
def rd(a,n): o=at(a); return bytes(r[o:o+n])
def rw(a): b=rd(a,2); return b[0]|b[1]<<8
CODE, TAB = 0xF30000, 0xF70000
# ---- SRAM (Bank 30, ungespeichert)
AKT, FLOOR, TOD, FEST, MELDZ, MSGP = 0x307002, 0x307004, 0x307008, 0x30700C, 0x307010, 0x307026
TUERM = 0x307038
BOSSAKT, BOSSI, BOSSW = 0x30703A, 0x30703C, 0x30703E
SIEGEL, OBENREQ, INOBEN, RAUMAKT, RZEIT, SEEN, CLRW = 0x3070C0, 0x3070C2, 0x3070C4, 0x3070C6, 0x3070C8, 0x3070CA, 0x3070CC
BOSSV, FLAKT, FLMAP, KTK, KTX, KTY, QCOOL, QH, QT = 0x3070CE, 0x3070D0, 0x3070D2, 0x3070D4, 0x3070D6, 0x3070D8, 0x3070DA, 0x3070DC, 0x3070DE
TMP1, TMP2, TMP3, TMP4, TMP5, TMP6, LIVE, PEND = [0x3070E0+2*i for i in range(8)]
BEAM = 0x3070F0                                  # Rueckweg-Skript laeuft (Bilder bis Zeitablauf)
PK, PX, PY, TPB, RMUS, HFORM = 0x3070A2, 0x3070A4, 0x3070A6, 0x3070AA, 0x3070AC, 0x3070AE   # v146z30: gewaehlter Pool-Raum (Raumsperre) / B-Merker Teleporter
TPZ = (158, 193, 466, 506)   # v146z30: Haendler-Teleporter auf 5E (x von/bis, y von/bis)
BEAMRT = 0x3070F2                                # Rueckweg gewuenscht (bis der Tuer-Hook ihn ausfuehrt; Wiederholung nach Zeitablauf)
SIEGR = 0x3070F6                                 # nach dem Sieg beim Rueckweg BSNAP nochmal zurueck (Boss-Skript gibt Story-Dinge erst nach der Sieg-Erkennung)
BSEEN = 0x3070FA                                 # v146o: Boss (ohne Sieg-Flag) war schon zu sehen
BMUS = 0x3070F8                                  # v146c: Boss-Musik schon gestartet (Vulgor)
BRTW = 0x3070F4                                  # Bilder, die der Rueckweg schon auf den freien Jungen wartet (ab 900 trotzdem)
MTOD = 0x3070B4                                  # v149: Tod im Marathon -> Schachbrett (Geld zurueck an der naechsten Tuer)
MKT = 0xF32FF0                                   # v149: fester Einsprung kmtod (soe_hoehle 'tod')
MARA = 0x3070B0                                  # v148: Boss-Marathon (jedes 5. Untergeschoss): Bit je erledigtem Boss
BOSSFEST, DROPTEST = 0x3070BC, 0x3070BE          # Testhilfen: Boss-Index+1 / seltene Beute erzwingen (1-4 = Art, 5 = normal)
MTXT2 = 0x307540                                 # v147b: Text-Puffer FF6 (Beute-Meldung, erst beim Zeigen gebaut)
BSNAP, MTXT = 0x307400, 0x307500                 # Boss-Flag-Sicherung 7E:2258-2347 / Text-Puffer FFB
QBUF = 0x307580                                  # 16 Woerter
FLSAVE = 0x3075A0                                # je Fund-Merker 1 Byte (max 32)
FREIM = 0x3075C0                                 # 30 Byte: Objekt-Platz frei
RSNAP = 0x307600                                 # Flag-Sicherung 7E:2258-22FF beim Betreten eines Pool-Raums (bis 76A7, soe_speicher ab 7700)
assert FREIM + 32 <= 0x307600
WARPM, WARPX, WARPY, WARPT, WARPB = 0x307EF0, 0x307EF2, 0x307EF4, 0x307EF6, 0x307EED   # soe_aufstehen-Warp
WINC = 0xF1B080
QABST = 80                                       # Bilder zwischen zwei Meldungen
OBEN = (160, 192, 200, 232)                      # Ausloeser oben (x von/bis, y von/bis)
LANDE = [(176,440), (64,448), (288,448), (176,760), (176,296)]   # 0 Mitte, 1 links, 2 rechts, 3 unten, 4 oben (unter dem Ausloeser)

# ---- GEPRUEFTER POOL (Karte, x, y px; Ankunft mit 238F=0 geprueft, Max v145)
# v146g (Max): ohne Vulgors Hoehle (16 Brueckenhoehle, 17 Knochenhoehle) und Wueste (1B)
# v146s (Max, Spielstaende): ohne 59 und 3A (keine Gegner / weg)
# v146n (Max): ohne leere Raeume 0E Speisesaal, 4C Statuen, 70 Dach (54 bleibt: Haendler); neu 65 Wald, 3D Kanal (je 10+ Gegner)
POOL = [[64,88,72],[64,216,608],[65,56,576],[79,56,600],[79,168,264],[79,464,600],[91,72,440],
        [91,144,104],[5,696,616],[5,360,48],[5,32,376],[7,48,488],[7,504,544],[15,888,328],
        [15,96,320],[18,1208,128],[18,272,328],[41,328,984],[40,1064,1240],[101,1168,32],[98,672,560],[55,152,1928],[123,224,720],[37,408,408],[124,536,856],[27,376,224]]   # v146y: Dschungeldorf 25, Nobilia 7C, Ivor Tower 0A/08 (Menschen -> Monster, Haustueren intern)   # v146u: 7B = Nobilia-Markt (Menschen -> Monster); v146t: 62 = eigene Stadt (Gegner per C2 -> Waffe geht); 37 = Feuerdrache-Raum ohne Boss (Max)
if os.environ.get('SOE_NURSTADT'): POOL = [p for p in POOL if p[0] in (0x62, 0x7B, 0x25, 0x7C, 0x1B)]   # Testbau: nur Staedte
# v152 (Max, Spielstand "diese karte raus 3"): Karte 06 raus
NPOOL = len(POOL); assert NPOOL < 256
# ---- Bosse (Bauplan 2.2, Sieg gemessen r_bossraeume): Karte, Ankunft (gemessene Stelle des Jungen), Sieg-Flag, Vorlage
# 18 Vulgor-Herz raus (Mesen v145: nach dem Sieg bleibt der Junge in der Story-Szene gesperrt, kein Rueckweg)
# v146c: + Baumdrache (20, Sieg 42A gemessen) + goldener Vulgor (18: Sieg-Flag 108 aus soe_vulgor_gold, vorher 044 = 1 setzen,
#        damit der Rueckkampf ohne Story-Szene kommt). 6. Feld = Flag, das beim Betreten gesetzt wird (0 = keins).
# v146o (Max: alle Bosse): Sieg-Flag None = Sieg, wenn die Boss-Vorlage (oder die 2. Vorlage) im Raum war und keine mehr lebt.
# Felder: Karte, Ankunft x/y (Junge), Sieg-Flag oder None, Vorlage, Zusatz-Flag beim Betreten (0 = keins), 2. Vorlage (0 = keine),
#   Musik (v146s: Byte-Versatz in 8C:87E0 fuer Skriptbefehl 33 - ueber die Cave startete die Raum-Musik nicht -> Ton weg, Max: Baumdrache)
BOSSE = [(0x2A,504,616,0x407,0xCFE8,0,0,0x24), (0x2C,72,280,0x48E,0xD282,0,0,0x5A), (0x45,464,624,0x477,0xDA50,0,0,0x88), (0x58,264,448,0x406,0xCEC0,0,0,0x24),
         (0x18,184,424,0x108,0xD894,0x044,0,0x04),
         (0x20,216,328,0x42A,0xCC70,0,0,0x24),          # Baumdrache (v146c: Rueckbeamen hing -> jetzt rauslaufen)
         (0x1D,256,56,None,0xCE2C,0,0,0x54),            # Vigor
         (0x4A,144,248,None,0xDBC2,0,0xDC0C,0x24),      # Ventilatoren + Lautsprecher
         (0x6D,208,536,None,0xCBDC,0,0,0x24),           # Monsterqualle
         # Puppentheater (0x77) raus (Max v146r: Kampf startet nicht, nur Dialog)
         (0x7E,120,312,None,0xDDC8,0,0,0x88),           # Raptor (8000 KP)
         (0x37,152,1928,None,0xCCBA,0,0,0x68)]          # Feuerdrache (Ankunft weit weg vom Drachen)
# BSNAP-Rueckschrieb: 2258-22FF ohne Formeln (2258-225C), Talismane/Hund (2261-2263), Waffe+N (22CE-22D0, 22D3-22D6), Waffenbesitz (22DA/DB)
BREST = [(0x225D,4), (0x2264,0x22CE-0x2264), (0x22D1,2), (0x22D7,3), (0x22DC,0x2300-0x22DC)]
# Beute: 21 Zutaten 0x200-0x215 ohne 0x205 + 11 Verbrauchsgueter (ohne 0x804 Fluegel, 0x807 Zauberperle), wie soe_funde v144
BEUTE = [0x200+i for i in range(0x16) if i != 5] + [0x800]*3 + [0x801]*3 + [0x802]*2 + [0x803, 0x805, 0x806]
assert len(BEUTE) == 32
TXT_FA = b"\x97Die Treppe ist versperrt.\x00"
TXT_F9 = b"\x97Der Raum ist ges\xe3ubert!\x00"
TXT_F8 = b"\x97Dieser Zugang ist versiegelt.\x00"
TXT_F5 = b"\x97Marathon geschafft! Alles +1!\x00"
TXT_F4 = b"\x97Fl\xf3gel: 100000 Schaden! BAM!\x00"
TXT_F3 = b"\x97Waffen-Orb: alle Waffen +1!\x00"
TXT_F2 = b"\x97Endbosskristall erhalten!\x00"   # v157   # v151 (Max): Boss-Orb gibt allen Waffen +1   # v150 (Max): Fluegel in der Cave
SUF = {'gelernt': b" gelernt!\x00", 'gefunden': b" gefunden!\x00", 'erhalten': b" erhalten!\x00", 'orb': b"-Orb: +1!\x00", 'plus': b" +1!\x00"}

# ---- Fund-Merker je Pool-Karte aus dem ROM (B-/Lauf-Ausloeser, deren Skript mit "08 85 ff ff LL 00" beginnt und im
#      bedingten Teil 18 39 01 (Item) und a3 39/3a/3b (Fund/Truhe) hat; r_kisten/r_schnueffeln)
def p3(a): b=rd(a,3); return b[0]|b[1]<<8|b[2]<<16
def padr(p): return ((0x93+(p>>15))<<16)|0x8000|(p&0x7FFF)
def trig(i): return padr(p3(0x938000+rw(0x938000)+i))
# nie anfassen: Formeln, Talismane, Waffe+N (soe_waffe99), Waffenbesitz, Rattus-Flag
SPERRB = set(range(0x2258,0x225D)) | {0x2261,0x2262,0x2263,0x22CE,0x22CF,0x22D0,0x22D3,0x22D4,0x22D5,0x22D6,0x22DA,0x22DB,0x22DD}
FLAGS = {}; GESPERRT = []
for m in sorted(set(p[0] for p in POOL)):
    p = p3(0xA0FDE5+4*m); y = 13; fl = []
    for li_ in (1,2):
        n = rw(p+y); y += 2
        for k in range(n//6):
            e = rd(p+y+6*k,6); i = e[4]|e[5]<<8; s = rd(trig(i),64)
            if s[0]==0x08 and s[1]==0x85 and s[5]==0:
                win = s[:6+s[4]]
                if b'\x18\x39\x01' in win and any(bytes([0xA3,c]) in win for c in (0x39,0x3A,0x3B)):
                    f = s[2]|s[3]<<8
                    if (0x2258+(f>>3)) in SPERRB: GESPERRT.append((m,f)); continue
                    if f not in fl and f != 0x490: fl.append(f)
        y += n
    assert len(fl) <= 32, (hex(m), len(fl))
    FLAGS[m] = fl

# ---- Tabellen in Bank F7 (Assert: frei)
T_POOL  = TAB + 0x0000           # je 6 Byte Karte, x, y
T_LAND  = TAB + 0x0100           # je 4 Byte x, y (Index TUERM)
T_BIT   = TAB + 0x0120           # Bit je Zugang (Wort)
T_BOSS  = TAB + 0x0800           # v146o: je 32 Byte: Karte, x, y, Flag-Byte (ab 2258), Maske (0 = Sieg ueber Boss-tot), Vorlage, Zusatzflag Byte/Maske, 2. Vorlage, Vorlage
T_LOOT  = TAB + 0x01A0           # 32 Woerter
T_SKR   = TAB + 0x8000           # Beute-Skript (Skripte ab Adresse 8000: Fadenstart 8C:D257 kodiert Bank 93+p>>15, Adresse 8000|p)
T_RMUS  = TAB + 0x8100           # v146z30: je Karte 4 Byte Musik-Skript 33 <Lied*4> 00 00 (Pool-Raeume starten ihre Original-Musik)
T_MSKR  = TAB + 0x8030           # v146c: Musik-Skript fuer Vulgor (33 04 00)
T_HSKR  = TAB + 0x8028           # v146z30: Teleporter-Skript zum Haendlerraum 0x54
T_TSKR  = TAB + 0x8020           # Tuer-Skript nach 5E (wie die linke Schachbrett-Treppe: a3 19 22 x y kk 00)
T_VNAME = TAB + 0x01E0           # v147b: 8 Zeiger (Bank C5) auf die Namen der Verbrauchsgueter
T_SUF   = TAB + 0x0210           # Endungen der Meldungen
T_TXT   = TAB + 0x0240           # Texte FFA/FF9/FF8
T_FLP   = TAB + 0x0400           # 128 Zeiger (Bank F7) auf Fund-Merker-Listen
T_FLL   = TAB + 0x0500           # Listen: Anzahl, dann je Merker Byte-Versatz ab 2258 (Wort) + Maske (Byte)
tabs = {}
tabs[T_POOL] = b''.join(m.to_bytes(2,'little')+x.to_bytes(2,'little')+y.to_bytes(2,'little') for m,x,y in POOL)
tabs[T_LAND] = b''.join(x.to_bytes(2,'little')+y.to_bytes(2,'little') for x,y in LANDE)
tabs[T_BIT]  = b''.join((0 if i == 0 else 1<<i).to_bytes(2,'little') for i in range(5))
tabs[T_BOSS] = b''.join(bytes(w(m)+w(x)+w(y)+(w(f>>3)+w(1<<(f&7)) if f is not None else [0,0,0,0])+w(v)+w(g>>3)+w((1<<(g&7)) if g else 0)+w(v2)+[0]*14) for m,x,y,f,v,g,v2,mu in BOSSE)
assert len(tabs[T_BOSS]) <= 0x400
tabs[T_LOOT] = b''.join(v.to_bytes(2,'little') for v in BEUTE)
# Beute-Skript: Junge anhalten (bc), buecken, Platz pruefen, geben + "X gefunden!" bzw. "Du hast genug X!", freigeben (bd).
# Mesen v145: ohne bc/Buecken (nur a3 3e/3f) stuerzte das Spiel nach der Meldung ab (STP 00:885F), wenn der Junge gerade angriff.
tabs[T_SKR]  = bytes.fromhex('bc78d01800b0a714a33e098590040500a33f040200a341bd0c9004b000')   # wie soe_funde v144 (GEPRUEFT): anhalten, buecken, geben, freigeben
tabs[T_MSKR] = b''.join(bytes([0x33,mu,0x00,0x00]) for *_,mu in BOSSE)   # je Boss 4 Byte: Musik-Skript 33 <Versatz> 00
# v146z34 (Max: Hund passend zur Epoche, kein Windhund im Sumpf): Hundeform je Karte aus editor/gebiete.json (Aeren)
HUNDFORM = bytes.fromhex('0c02020206060606080808080808080808080202080002020208020808020802020202080802020208080808080802060600000202020206020608020202020c02020c0c0c0c0c0c0c0c0c0008080806060206020c0606060606060202060808080c060000020206060202060800080806080808000808080802020606000c00')   # 02 Wolf, 06 Windhund, 08 Pudel, 0C Toaster, 0 = lassen
HUNDFORM = bytearray(HUNDFORM); HUNDFORM[0x1D] = 6; HUNDFORM = bytes(HUNDFORM)   # Vigor-Arena liegt in Antiqua (gebiete.json grob)
HFT = 0xF8D700
RAUM_MUSIK = {0x40:0x33, 0x41:0x3D, 0x4F:0x1B, 0x57:0x21, 0x5B:0x08, 0x05:0x1E, 0x06:0x1E, 0x07:0x1B, 0x0F:0x38, 0x12:0x12,
              0x29:0x0E, 0x28:0x32, 0x65:0x07, 0x3D:0x43, 0x62:0x3B, 0x37:0x33, 0x7B:0x34, 0x25:0x05, 0x7C:0x34, 0x1B:0x0A}   # Karte -> Lied-Nr. (8C:85E7 A), Mesen-Warp v146z30
_mt = at(0x8C87E0); _arg = {}
for _i in range(0, 0x100, 2): _arg.setdefault(r[_mt+_i] | r[_mt+_i+1]<<8, _i)   # Lied -> Versatz in der Lied-Tabelle 8C:87E0 (Befehl 33 <Versatz>)
assert all(v in _arg for v in RAUM_MUSIK.values()), [hex(v) for v in RAUM_MUSIK.values() if v not in _arg]
tabs[T_RMUS] = b''.join((bytes([0x33,_arg[RAUM_MUSIK[k]],0x00,0x00]) if k in RAUM_MUSIK else bytes(4)) for k in range(128))
tabs[T_TSKR] = bytes([0xA3,0x19, 0x22, 176//8, 440//8, 0x5E,0x00, 0x00])
tabs[T_HSKR] = bytes([0xA3,0x19, 0x22, 320//8, 144//8, 0x54,0x00, 0x00])
sufadr = {}; sb = b''
for k,v in SUF.items(): sufadr[k] = (T_SUF + len(sb)) & 0xFFFF; sb += v
assert len(sb) <= 0x30, len(sb)
tabs[T_SUF] = sb
_vn = []; _o = at(0xC519E8)
for _i in range(8):
    _vn.append(0x19E8 + (_o - at(0xC519E8))); _o = bytes(r).index(b'\x00', _o) + 1
tabs[T_VNAME] = b''.join(v.to_bytes(2,'little') for v in _vn)
T_FA = T_TXT; T_F9 = T_FA + len(TXT_FA); T_F8 = T_F9 + len(TXT_F9); T_F5 = T_F8 + len(TXT_F8); T_F4 = T_F5 + len(TXT_F5); T_F3 = T_F4 + len(TXT_F4); T_F2 = T_F3 + len(TXT_F3)
tabs[T_TXT] = TXT_FA + TXT_F9 + TXT_F8 + TXT_F5 + TXT_F4 + TXT_F3 + TXT_F2
flp = [0]*128; fll = b''
for m, fl in FLAGS.items():
    if not fl: continue
    flp[m] = (T_FLL + len(fll)) & 0xFFFF
    fll += bytes([len(fl)]) + b''.join(bytes(w(f>>3)+[1<<(f&7)]) for f in fl)
tabs[T_FLP] = b''.join(v.to_bytes(2,'little') for v in flp)
tabs[T_FLL] = fll
ordn = sorted(tabs)
for a, b in zip(ordn, ordn[1:]): assert a + len(tabs[a]) <= b, hex(a)
assert all(a + len(tabs[a]) <= TAB + 0x1000 for a in ordn if a < TAB + 0x8000) and T_TSKR + len(tabs[T_TSKR]) <= TAB + 0x8030 and T_MSKR + len(tabs[T_MSKR]) <= TAB + 0x8080
o_ = at(HFT); assert all(b == 0xFF for b in r[o_:o_+128]), 'HFT belegt'; r[o_:o_+128] = HUNDFORM
def skp(a): p = (((a>>16) - 0x93) << 15) | (a & 0x7FFF); assert a & 0x8000; return p

# ---- Assembler-Helfer (16 Bit, lange Adressen)
def lda(a): return [0xAF]+L(a)
def sta(a): return [0x8F]+L(a)
def cmpl(a): return [0xCF]+L(a)
def andl(a): return [0x2F]+L(a)
def oral(a): return [0x0F]+L(a)
def adcl(a): return [0x6F]+L(a)
def ldax(a): return [0xBF]+L(a)
def stax(a): return [0x9F]+L(a)
def li(v): return [0xA9]+w(v)
def ci(v): return [0xC9]+w(v)
def ai(v): return [0x29]+w(v)
def oi(v): return [0x09]+w(v)
def lxi(v): return [0xA2]+w(v)
def lyi(v): return [0xA0]+w(v)
def jsl(a): return [0x22]+L(a)
def z(a): return li(0)+sta(a)
def absw(op, a): return [op, a&0xFF, (a>>8)&0xFF]          # absolut (DB muss passen)
SEP, REP = [0xE2,0x20], [0xC2,0x20]
NOP8 = [0xEA]*8
def mod(n): return [0x8F,0x04,0x42,0x00]+SEP+[0xA9,n, 0x8F,0x06,0x42,0x00]+REP+NOP8+[0xAF,0x16,0x42,0x00]   # A = A mod n (n<256)
def B(op, l): return ('bra8', op, l)
BEQ, BNE, BCC, BCS, BPL, BMI, BRA = 0xF0, 0xD0, 0x90, 0xB0, 0x10, 0x30, 0x80
DB7E = [0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB]          # PHB ; PEA 7E7E ; PLB ; PLB
DB30 = [0x8B, 0xF4,0x30,0x30, 0xAB,0xAB]

o0 = at(0xF04000); assert r[o0] == 0x22; VORHER = list(r[o0+1:o0+4])
o1 = at(0x8CD0F6); assert r[o1] == 0x5C; ALT = list(r[o1+1:o1+4])          # bisher JML F1:8700 (soe_vigor TEXT)
o2 = at(0x8CE0C4); assert bytes(r[o2:o2+4]) == bytes([0xA7,0x82,0xE6,0x82]), bytes(r[o2:o2+4]).hex()
o3 = at(0x8CE0DA); assert bytes(r[o3:o3+4]) == bytes([0xA7,0x82,0xE6,0x82]), bytes(r[o3:o3+4]).hex()   # BA bleibt original
o4 = at(0x8FDE7C); assert bytes(r[o4:o4+4]) == bytes([0xAF,0x33,0x24,0x7E]), bytes(r[o4:o4+4]).hex()   # LDA 2433 -> Spawn-Anzahl

def landx(): return [0x0A,0x0A, 0xAA]+li(0x5E)+sta(KTK)+ldax(T_LAND)+sta(KTX)+ldax(T_LAND+2)+sta(KTY)

t = [
  # ================= Vektoren (werden unten eingesetzt)
  [0x5C,0,0,0]*8,
  # ================= 1. C2-Weiche (keine Monster auf 5E, v143)
  'c2:', [0x08, 0xC2,0x20], lda(AKT)+ai(0xFF), B(BEQ,'c2_o'),
  lda(0x7E0ADB)+ai(0xFF)+ci(0x5E), B(BNE,'c2_o'),
  [0xA5,0x84]+ai(0xFF)+ci(0x7E), B(BEQ,'c2_o'),
  [0x28, 0xE6,0x82, 0xE6,0x82, 0xE6,0x82, 0x5C,0x2C,0xE1,0x8C],
  'c2_o:', [0x28, 0xA7,0x82, 0xE6,0x82, 0x5C,0xC8,0xE0,0x8C],
  # ================= 2. Text-ID -> Zeiger ($22/$24), A = ID, X bleibt
  'text:', ci(0xFF6), B(BEQ,'tx_f6'), ci(0xFF7), B(BEQ,'tx_f7'), ci(0xFFA), B(BEQ,'tx_fa'), ci(0xFF9), B(BEQ,'tx_f9'), ci(0xFFB), B(BEQ,'tx_fb'), ci(0xFF8), B(BEQ,'tx_f8'), ci(0xFF5), B(BEQ,'tx_f5'), ci(0xFF4), B(BEQ,'tx_f4'), ci(0xFF3), B(BEQ,'tx_f3'), ci(0xFF2), B(BEQ,'tx_f2'),
  [0x5C]+ALT,
  'tx_fa:', li(T_FA&0xFFFF), B(BRA,'tx_rom'),
  'tx_f8:', li(T_F8&0xFFFF), B(BRA,'tx_rom'),
  'tx_f5:', li(T_F5&0xFFFF), B(BRA,'tx_rom'),
  'tx_f4:', li(T_F4&0xFFFF), B(BRA,'tx_rom'),
  'tx_f3:', li(T_F3&0xFFFF), B(BRA,'tx_rom'),
  'tx_f2:', li(T_F2&0xFFFF), B(BRA,'tx_rom'),
  'tx_f9:', li(T_F9&0xFFFF),
  'tx_rom:', [0x85,0x22]+li(TAB>>16)+[0x85,0x24, 0x6B],
  'tx_fb:', li(MTXT&0xFFFF)+[0x85,0x22]+li(MTXT>>16)+[0x85,0x24, 0x6B],
  'tx_f6:', li(MTXT2&0xFFFF)+[0x85,0x22]+li(MTXT2>>16)+[0x85,0x24, 0x6B],
  'tx_f7:', li(0xEE00)+[0x85,0x22]+li(0x7E)+[0x85,0x24, 0x6B],      # v146g: Gegner-Info (soe_gegner_info, Puffer 7E:EE00)

  # ================= 3. Tuer (aus soe_hoehle 'tuer', 238F schon 0): KTK/KTX/KTY = Original-Ziel -> neues Ziel
  'kt:', [0x08, 0xC2,0x30]+DB7E,
  li(QABST+40)+sta(QCOOL)+li(1)+sta(INOBEN)+z(BEAM)+z(BEAMRT),
  lda(MTOD), B(BEQ,'kt_mt0'), z(MTOD)+lxi(0), 'kt_mtl:', ldax(0x307EE0)+stax(0x7E0AC6)+[0xE8,0xE8, 0xE0,0x0C,0x00], B(BCC,'kt_mtl'),
  SEP+[0xA9,0x00]+sta(0x307EED)+sta(0x307FEE)+sta(0x307E70)+REP, 'kt_mt0:',
  lda(SIEGR), B(BEQ,'kt_s0'), ('jsr','bsrest'), z(SIEGR), lda(BOSSAKT), B(BNE,'kt_s0'), ('jsr','mara'), B(BCC,'kt_s0'), ('jmp','kt_mb'), 'kt_s0:',
  lda(BOSSAKT), B(BEQ,'kt_nb'),
  # v146t (Max: Verlassen des Bossraums gab einen Waffen-Orb): Bosse ohne Sieg-Flag -> an der Tuer zaehlt nur ein im Kampf
  # schon erkannter Sieg (BOSSW > 0); beim Raumwechsel ist das Boss-Objekt weg und sah wie "besiegt" aus.
  ('jsr','bfl_lade'), lda(TMP3), B(BNE,'kt_mf'), lda(BOSSW), B(BEQ,'kt_flucht'), ('jsr','sieg'), B(BRA,'kt_b4'),
  'kt_mf:', ('jsr','bflag'), B(BEQ,'kt_flucht'), ('jsr','sieg'), B(BRA,'kt_b4'),     # Tuer nach dem Sieg (Flag schon gesetzt) = Sieg
  'kt_flucht:', ('jsr','bsrest'), z(BOSSAKT), li(4)+sta(TUERM), ('jmp','land'),
  'kt_b4:', li(4)+sta(TUERM), ('jsr','mara'), B(BCS,'kt_mb'), ('jmp','land'),
  'kt_mb:', li(4)+sta(TUERM), ('jmp','boss'),
  'kt_nb:', lda(0x7E0ADB)+ai(0xFF)+ci(0x5E), B(BNE,'kt_nb2'), ('jmp','kt_5e'), 'kt_nb2:',
  # v146z34: aus dem Haendlerraum 0x54 zurueck -> Hundeform von vorher (das Schachbrett laedt Hund nach 7E:2363)
  # v146y (Max: Haustueren in der Stadt duerfen nicht rausfuehren): Tuer innerhalb derselben Stadtgruppe (GRP F8:D500,
  # soe_vulgor_larven) bleibt die Original-Tuer; Raumzaehler neu, Flags bleiben gesichert (kein flsave).
  ai(0x7F), [0xAA], ldax(0xF8D500)+ai(0x7F), B(BEQ,'kt_ng'), sta(TMP1),
  lda(KTK)+ai(0x7F), [0xAA], ldax(0xF8D500)+ai(0x7F)+[0xCF]+L(TMP1), B(BNE,'kt_ng'),
  li(1)+sta(0x7EEE92)+ldax(0xF8D500)+ai(0x80), B(BNE,'kt_draus'), li(3), B(BRA,'kt_rs'), 'kt_draus:', li(1),   # v146z6: Haus -> RAUMAKT 3 (keine Saeuberung)
  'kt_rs:', sta(RAUMAKT)+z(RZEIT)+z(SEEN)+z(CLRW)+z(LIVE)+z(PEND), ('jmp','kt_ende'),   # EE92: soe_hoehle stellt 238F wieder her
  'kt_ng:',
  # v146z30 (Max: kein Raum-Wechseln bis einer passt): ungesaeuberter Pool-Raum (RAUMAKT 1, CLRW 0) -> Tuer fuehrt zurueck in denselben Raum
  lda(RAUMAKT)+ci(1), B(BNE,'kt_ng0'), lda(CLRW), B(BNE,'kt_ng0'),
  lda(PK)+sta(KTK)+lda(PX)+sta(KTX)+lda(PY)+sta(KTY), li(0xFF8), ('jsr','qp'),
  li(1)+sta(RAUMAKT)+z(RZEIT)+z(SEEN)+z(CLRW)+z(LIVE)+z(PEND), ('jmp','kt_ende'),
  'kt_ng0:',
  # aus einem Pool-Raum (oder sonst einer Hoehlen-Karte) -> 5E vor den benutzten Zugang
  ('jsr','flrest'), z(RAUMAKT)+z(CLRW),
  lda(TUERM)+ai(7), ('jmp','land'),
  'kt_5e:', lda(KTK)+ai(0xFF)+ci(0x54), B(BNE,'kt_5e0'), li(3)+sta(RAUMAKT), ('jmp','kt_ende'),   # v146z30: Teleporter -> Haendlerraum (keine Saeuberung)
  'kt_5e0:', lda(OBENREQ), B(BEQ,'kt_1'), z(OBENREQ), li(4), ('jmp','zug'),
  'kt_1:', lda(KTK)+ai(0xFF)+ci(0x60), B(BNE,'kt_2'), ('jmp','treppe'),
  'kt_2:', ci(0x5D), B(BNE,'kt_3'), li(3), B(BRA,'zug'),
  'kt_3:', ci(0x5F), B(BEQ,'kt_4'), ('jmp','land0'),
  'kt_4:', lda(KTX)+ci(400)+li(1), B(BCC,'zug'), li(2),
  'zug:', sta(TMP1)+[0x0A, 0xAA]+ldax(T_BIT)+andl(SIEGEL), B(BEQ,'zg_offen'),
  li(0xFF8), ('jsr','qp'), lda(TMP1), ('jmp','land'),                 # versiegelt -> bleibt vor dem Zugang
  'zg_offen:', lda(TMP1)+sta(TUERM),   # v146z30: auch oben ein Pool-Raum (Boss kommt ueber die Treppe)
  'pool:', ([0xA9,int(os.environ.get('SOE_TESTRAUM','0')),0x00]+sta(FEST) if os.environ.get('SOE_TESTRAUM') else []), lda(FEST)+ai(0xFF), B(BEQ,'p_zuf'), ci(0xFF), B(BNE,'p_fest'),
  lda(0x307030)+sta(KTK)+lda(0x307032)+sta(KTX)+lda(0x307034)+sta(KTY), B(BRA,'p_ein'),   # Testmodus FEST=FF
  'p_fest:', [0x3A], B(BRA,'p_idx'),                                                          # Testmodus FEST = Pool-Index+1
  'p_zuf:', ('jsr','rnd'), mod(NPOOL),
  'p_idx:', [0x0A]+sta(TMP2)+[0x0A, 0x18]+adcl(TMP2)+[0xAA]+ldax(T_POOL)+sta(KTK)+ldax(T_POOL+2)+sta(KTX)+ldax(T_POOL+4)+sta(KTY),
  # v146z36 (Max: hier braucht man eine Axt): Karte 0x12 nur mit Axt (Besitz 22DA Bit 5-7 = 0A/0C/0E, 22DB Bit 0 = 10), sonst neu wuerfeln
  lda(KTK)+ai(0xFF)+ci(0x12), B(BEQ,'p_ax0'), ci(0x05), B(BNE,'p_ax'),   # v146z37: auch Karte 0x05 (Max)
  'p_ax0:', lda(0x7E22DA)+ai(0x01C0), B(BNE,'p_ax'), ('jmp','p_zuf'), 'p_ax:',   # v146z39: Bronze-Axt 0C / Ritterzerschmetterer 0E / Atomaxt 10 (ohne Spinnenklaue)
  # v146z38 (Max: hier braucht man den Bronze-Speer): Karte 0x29 nur mit Bronze-Speer 14 / Lanze 16 / Laserlanze 18 (22DB Bit 2-4)
  lda(KTK)+ai(0xFF)+ci(0x29), B(BNE,'p_sp'), lda(0x7E22DA)+ai(0x1C00), B(BNE,'p_sp'), ('jmp','p_zuf'), 'p_sp:',
  'p_ein:', lda(KTK)+sta(PK)+lda(KTX)+sta(PX)+lda(KTY)+sta(PY),   # v146z30: fuer die Raumsperre
  lda(KTK)+ai(0xFF), ('jsr','flsave'),
  lda(KTK)+ai(0x7F)+[0xAA]+ldax(0xF8D500)+ai(0xFF), B(BEQ,'p_r1'), ai(0x80), B(BNE,'p_r1'), li(3), B(BRA,'p_r2'),   # v146z6: Durchgang/Haus -> keine Saeuberung
  'p_r1:', li(1), 'p_r2:', sta(RAUMAKT)+z(RMUS)+z(RZEIT)+z(SEEN)+z(CLRW)+z(LIVE)+z(PEND), ('jmp','kt_ende'),
  'treppe:', lda(SIEGEL)+ai(0x1E)+ci(0x1E), B(BEQ,'tr_frei'), li(0xFFA), ('jsr','qp'), ('jmp','land0'),
  'tr_frei:', lda(SIEGEL)+ai(0x20), B(BNE,'tr_neu'), li(4)+sta(TUERM), ('jmp','boss'),   # v146z30: jedes Untergeschoss erst den Boss
  'tr_neu:', li(220)+sta(MELDZ)+lda(FLOOR)+ai(0xFF)+[0x1A]+ci(100), B(BCC,'tr_f'), li(99), 'tr_f:', sta(FLOOR),
  ('jsr','nstock'),
  'land0:', li(0),
  'land:', landx(),
  'kt_ende:',
  # v146z34: Hundeform zur Zielkarte setzen, bevor sie laedt (die Karte laedt Hund-Palette/-Grafik nach 7E:2363)
  lda(KTK)+ai(0x7F)+[0xAA]+ldax(HFT)+ai(0xFF), B(BEQ,'kt_hx'), SEP, [0x8F,0x63,0x23,0x7E], REP, 'kt_hx:',
  [0xAB, 0x28, 0x6B],
  # ---- Bossraum betreten (TUERM = 4, Stockwerk mod 5 = 0, Boss noch offen)
  'boss:', lda(BOSSFEST)+ai(0xFF), B(BEQ,'bs_z'), [0x3A], B(BRA,'bs_i'),
  'bs_z:', ('jsr','rnd'), mod(len(BOSSE)), sta(TMP4), ('jsr','stock5'), B(BCS,'bs_i0'),
  # v148 (Max: Boss-Marathon, alle Bosse zufaellig): naechster noch offener Boss ab dem Zufallsindex
  li(len(BOSSE))+sta(TMP5),
  'bs_ml:', lda(TMP4), ('jsr','mbit'), andl(MARA), B(BEQ,'bs_i0'),
  lda(TMP4)+[0x1A]+ci(len(BOSSE)), B(BCC,'bs_m2'), li(0), 'bs_m2:', sta(TMP4)+lda(TMP5)+[0x3A]+sta(TMP5), B(BNE,'bs_ml'),
  'bs_i0:', lda(TMP4),
  'bs_i:', [0x0A,0x0A,0x0A,0x0A,0x0A]+sta(BOSSI)+z(BSEEN),
  lxi(0x2258)+lyi(BSNAP&0xFFFF)+li(0xEF)+[0x54,0x30,0x7E],                          # MVN 7E:2258-2347 -> 30:7400 (DB jetzt 30)
  ('jsr','bfl_lade'), [0x49,0xFF,0xFF]+sta(TMP2), SEP, ldax(0x7E2258)+andl(TMP2)+stax(0x7E2258), REP,   # Sieg-Flag loeschen
  lda(BOSSI)+[0xAA]+ldax(T_BOSS+14)+sta(TMP3)+ldax(T_BOSS+12)+[0xAA]+lda(TMP3), B(BEQ,'bs_ns'),   # v146c: Zusatz-Flag setzen (goldener Vulgor: 044)
  SEP, ldax(0x7E2258)+[0x0F]+L(TMP3)+stax(0x7E2258), REP, 'bs_ns:',
  lda(BOSSI)+[0xAA]+ldax(T_BOSS)+sta(KTK)+ldax(T_BOSS+2)+sta(KTX)+ldax(T_BOSS+4)+sta(KTY)+ldax(T_BOSS+10)+sta(BOSSV),
  li(1)+sta(BOSSAKT)+z(BOSSW)+z(RAUMAKT)+z(BMUS), ('jmp','kt_ende'),
  # bfl_lade: X = Flag-Byte (ab 2258), A = Maske
  'bfl_lade:', lda(BOSSI)+[0xAA]+ldax(T_BOSS+8)+sta(TMP3)+ldax(T_BOSS+6)+[0xAA]+lda(TMP3)+[0x60],
  # bflag: Z = 0 wenn das Sieg-Flag gesetzt ist
  'bflag:', ('jsr','bfl_lade'), lda(TMP3), B(BEQ,'bf_tot'), ldax(0x7E2258)+andl(TMP3)+ai(0xFF)+[0x60],
  # v146o: kein Sieg-Flag -> Boss (Vorlage BOSSV oder 2. Vorlage) lebt? ja: BSEEN = 1, A = 0. nein: A = BSEEN (1 = Sieg)
  'bf_tot:', lda(BOSSI)+[0xAA]+ldax(T_BOSS+16)+sta(TMP3)+z(TMP6)+lxi(0x3DE5),   # TMP6 = irgendein Monster lebt
  # v146u (Max: Ventilatoren - Phase 2 kam nicht mehr): JEDES lebende Monster (Vorlage C536..DF3A) zaehlt als "Kampf laeuft"
  'bf_l:', ldax(0x7E0060), ci(0xC536), B(BCC,'bf_n'), ci(0xDF3B), B(BCS,'bf_n'),
  'bf_v:', ldax(0x7E002A), B(BEQ,'bf_n'),
  # v146z2 (Max: Endboss-Raum 4A = mehrere Wellen, nach den Raptoren kam der Sieg): BSEEN nur, wenn der ECHTE Boss
  # (Vorlage BOSSV oder 2. Vorlage TMP3) lebt; andere Monster halten den Kampf nur offen (A = 0).
  # v146z22 (Max: Monsterqualle gab keinen Orb): NICHT beim ersten lebenden Nicht-Boss abbrechen (Tentakel standen vor der Qualle)
  # v146z22: 'irgendein Monster lebt' haelt den Kampf nur im Endboss-Raum 4A offen (Wellen/Phase 2) - sonst blieben z. B. die
  # Tentakel der Monsterqualle ewig 'lebendig' (3920 KP, im Original verschwinden sie) -> nie Sieg
  lda(0x7E0ADB)+ai(0xFF)+ci(0x4A), B(BNE,'bf_k4'), li(1)+sta(TMP6), 'bf_k4:', ldax(0x7E0060)+[0xCF]+L(BOSSV), B(BEQ,'bf_echt'), ldax(0x7E0060)+[0xCF]+L(TMP3), B(BNE,'bf_n'),
  'bf_echt:', li(1)+sta(BSEEN)+sta(TMP6),   # v146z24 (Max: Boss lebt, trotzdem rausgebeamt): lebender Boss haelt den Kampf IMMER offen
  'bf_n:', [0x8A, 0x18, 0x69,0x8E,0x00, 0xAA, 0xE0,0x89,0x4E], B(BCC,'bf_l'),
  lda(TMP6), B(BEQ,'bf_e'), li(0)+[0x60], 'bf_e:', lda(BSEEN)+[0x60],
  # sieg: Flags zurueck, Boss erledigt (SIEGEL Bit 4), Waffen-Orb + Meldung
  'sieg:', ('jsr','bsrest'), li(1)+sta(SIEGR)+z(BOSSAKT)+lda(SIEGEL)+oi(0x10)+sta(SIEGEL)+li(4)+sta(TUERM),
  lda(BOSSI)+[0x4A,0x4A,0x4A,0x4A,0x4A], ('jsr','mbit'), oral(MARA)+sta(MARA),
  ('jsr','mara'), B(BCS,'sg_m'), lda(SIEGEL)+oi(0x20)+sta(SIEGEL),
  ('jsr','stock5'), B(BCS,'sg_m'), ('jsr','malles'), 'sg_m:',   # v146z30: 0x20 = Boss dieses Untergeschosses erledigt
  ('jsr','mwaff'), li(0xFF3), ('jsr','qp'), [0x60],   # v151 (Max): Boss-Orb = alle Waffen +1
  # bsrest: BSNAP -> 7E (ohne Formeln/Talismane/Waffe+N/Waffenbesitz)
  'bsrest:', [0x8B]+sum(([0xA2]+w((BSNAP&0xFFFF)+a-0x2258)+[0xA0]+w(a)+[0xA9]+w(n-1)+[0x54,0x7E,0x30] for a,n in BREST), [])+[0xAB, 0x60],
  # malles (v149, Max: Marathon-Sieg = alle Waffen, Talismane und Formeln +1): nur was man besitzt
  'malles:', ('jsr','mwaff'), ('jmp','ma_fo'),
  'mwaff:', lxi(2),
  'ma_w:', [0xDA]+ldax(0xC5000A)+sta(TMP4)+ldax(0xC50026)+ai(0xFF)+sta(TMP5)+lda(TMP4), B(BEQ,'ma_wn'),
  [0xAA]+ldax(0x7E0000)+andl(TMP5)+ai(0xFF), B(BEQ,'ma_wn'), [0xA3,0x01]+jsl(WINC)+[0xC2,0x30],
  'ma_wn:', [0xFA, 0xE8,0xE8, 0xE0,0x1B,0x00], B(BCC,'ma_w'), [0x60],
  'ma_fo:', lxi(0),
  'ma_f:', [0xDA]+ldax(0xC502E7)+ai(0xFF)+sta(TMP5)+ldax(0xC502A1)+[0xAA]+ldax(0x7E0000)+andl(TMP5)+ai(0xFF), B(BEQ,'ma_fn'),
  [0xA3,0x01, 0xAA, 0x22,0x40,0x90,0xF0, 0xC2,0x30],
  'ma_fn:', [0xFA, 0xE8,0xE8, 0xE0,70,0x00], B(BCC,'ma_f'),
  lxi(0),
  'ma_t:', [0xDA]+ldax(0x8CBFB9)+ai(0xFF)+sta(TMP5)+ldax(0x8CBF91)+[0xAA]+ldax(0x7E0000)+andl(TMP5)+ai(0xFF), B(BEQ,'ma_tn'),
  [0xA3,0x01, 0x18, 0x69,72,0x00, 0xAA, 0x22,0x40,0x90,0xF0, 0xC2,0x30],
  'ma_tn:', [0xFA, 0xE8,0xE8, 0xE0,28,0x00], B(BCC,'ma_t'),
  li(0xFF5), ('jsr','qp'),
  # v157 (Max): dazu ein Endbosskristall (hoechstens 9; 7E:20C9, im Ring nur ausserhalb der Cave)
  SEP+lda(0x7E20C9)+[0xC9,9], B(BCS,'ma_kv'), [0x1A]+sta(0x7E20C9), 'ma_kv:', REP, li(0xFF2), ('jmp','qp'),
  # kmtod (v149, Max: im Marathon nach mindestens einem Boss sterben -> Schachbrett, Marathon vorbei, nur weiter nach unten)
  # C = 1: erledigt (soe_hoehle setzt dann keinen Cave-Tod)
  'kmtod:', [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A]+DB7E,
  lda(BOSSAKT), B(BEQ,'km_n'), ('jsr','stock5'), B(BCS,'km_n'), lda(MARA), B(BEQ,'km_n'),
  ('jsr','bsrest'), z(BOSSAKT)+z(SIEGR)+lda(SIEGEL)+oi(0x30)+sta(SIEGEL)+li(4)+sta(TUERM)+li(1)+sta(MTOD),
  [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x38, 0x6B],
  'km_n:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x18, 0x6B],
  'mbit:', [0xAA]+li(1)+[0xE0,0x00,0x00], 'mb_l:', B(BEQ,'mb_r'), [0x0A, 0xCA], B(BRA,'mb_l'), 'mb_r:', [0x60],
  'mara:', ('jsr','stock5'), B(BCS,'ma_n'), lda(MARA)+ci((1<<len(BOSSE))-1), B(BEQ,'ma_n'), [0x38, 0x60], 'ma_n:', [0x18, 0x60],
  # stock5: C = 0 wenn Stockwerk mod 5 == 0 (Boss-Ebene)
  'stock5:', lda(FLOOR)+ai(0xFF), 's5_m:', ci(5), B(BCC,'s5_r'), [0xE9,0x05,0x00], B(BRA,'s5_m'), 's5_r:', ci(1), [0x60],
  # nstock: neues Stockwerk -> Siegel/Boss zuruecksetzen
  'nstock:', z(MARA)+z(SIEGEL)+z(TUERM)+z(RAUMAKT)+z(CLRW)+z(OBENREQ)+z(BOSSAKT)+[0x60],
  # rnd: A = Zufall 0..7FFF (DB = 7E)
  'rnd:', [0x22,0x9B,0x85,0x80, 0x4F,0x00,0x01,0x7E, 0x4F,0xA3,0x4E,0x7E]+ai(0x7FFF)+[0x60],
  # ---- Fund-Merker des Pool-Raums sichern + loeschen (A = Karte)
  'flsave:', sta(FLMAP)+li(1)+sta(FLAKT)+[0x8B]+lxi(0x2258)+lyi(RSNAP&0xFFFF)+li(0xA7)+[0x54,0x30,0x7E, 0xAB],   # 2258-22FF -> RSNAP
  lda(FLMAP)+[0x0A, 0xAA]+ldax(T_FLP), B(BNE,'fs_1'), [0x60],
  'fs_1:', DB30, [0xAA]+SEP+ldax(TAB)+REP+ai(0xFF)+sta(TMP3)+[0xE8], lyi(0),
  'fs_l:', ldax(TAB)+sta(TMP4)+ldax(TAB+2)+ai(0xFF)+sta(TMP5)+[0xDA]+lda(TMP4)+[0xAA],
  SEP, ldax(0x7E2258)+andl(TMP5)+absw(0x99,FLSAVE), lda(TMP5)+[0x49,0xFF, 0x3F]+L(0x7E2258)+stax(0x7E2258), REP,
  [0xFA, 0xE8,0xE8,0xE8, 0xC8], lda(TMP3)+[0x3A]+sta(TMP3), B(BNE,'fs_l'),
  [0xAB, 0x60],
  # ---- Flags des Pool-Raums zurueck (RSNAP, ohne Formeln/Talismane/Waffe+N/Waffenbesitz) -> auch Fund-Merker und Besuchs-Flags
  'flrest:', lda(FLAKT), B(BNE,'fr_0'), [0x60],
  'fr_0:', z(FLAKT)+[0x8B]+sum(([0xA2]+w((RSNAP&0xFFFF)+a-0x2258)+[0xA0]+w(a)+[0xA9]+w(n-1)+[0x54,0x7E,0x30] for a,n in BREST), [])+[0xAB, 0x60],
  # ---- Warteschlange: qp (JSR, A = Text-ID >= 0F00 oder Beute-Item)
  'qp:', [0xDA, 0x48]+lda(QT)+[0x1A,0x1A]+ai(0x1E)+cmpl(QH), B(BEQ,'qp_voll'),
  lda(QT)+[0xAA, 0x68]+stax(QBUF)+[0x8A, 0x1A,0x1A]+ai(0x1E)+sta(QT)+[0xFA, 0x60],
  'qp_voll:', [0x68, 0xFA, 0x60],
  'qpl:', [0x08, 0xC2,0x30], ('jsr','qp'), [0x28, 0x6B],
  # ---- qtick (jedes Bild in der Hoehle): naechste Meldung zeigen
  'qtick:', lda(QCOOL), B(BEQ,'qt_1'), [0x3A]+sta(QCOOL)+[0x60],
  'qt_1:', lda(QH)+cmpl(QT), B(BNE,'qt_2'), [0x60],
  'qt_2:', lda(MSGP), B(BEQ,'qt_3'), [0x60],
  'qt_3:', lda(WARPT)+oral(BEAM)+oral(BEAMRT), B(BEQ,'qt_4'), [0x60],
  'qt_4:', lda(QH)+[0xAA]+ldax(QBUF)+ci(0x0F00), B(BCS,'qt_5'),
  # Beute erst, wenn der Junge frei ist (keine Sperre 4E99 & 0020 wie nach bc, kein laufendes Skript 4E89+3E)
  # v146s (Max: Aufheben unterbrach Aufladen/Spezialschlag): auch warten, solange er schlaegt (4E99 & 0040)
  # oder eine Aktionstaste gehalten wird (Aufladen: B/Y/A/X in $00:4218)
  # v147b (Max: Aufheben bricht Aufladen/Angriff ab): Beute ohne Skript -> kein Warten auf den freien Jungen mehr
  'qt_5:', ldax(QBUF)+[0x48, 0x8A, 0x1A,0x1A]+ai(0x1E)+sta(QH)+li(QABST)+sta(QCOOL)+[0x68]+ci(0x0F00), B(BCC,'qt_item'),
  sta(MSGP)+[0x60],
  # v147b: Beute direkt ins Inventar (Zutat 0x200+i -> 22FF+i bis 99, Verbrauchsgut 0x800+i -> 2315+i bis 6), Meldung FF6
  #        ohne Skript (kein Anhalten/Buecken). Voll -> nichts.
  'qt_item:', ci(0x800), B(BCS,'qi_v'),
  [0x38,0xE9,0x00,0x02, 0xAA]+ldax(0x7E22FF)+ai(0xFF)+ci(99), B(BCS,'qi_r'),
  SEP+ldax(0x7E22FF)+[0x1A]+stax(0x7E22FF)+REP+[0x8A,0x0A,0xAA]+ldax(0xC50659), B(BRA,'qi_t'),
  'qi_v:', [0x38,0xE9,0x00,0x08, 0xAA]+ldax(0x7E2315)+ai(0xFF)+ci(6), B(BCS,'qi_r'),
  SEP+ldax(0x7E2315)+[0x1A]+stax(0x7E2315)+REP+[0x8A,0x0A,0xAA]+ldax(T_VNAME),
  'qi_t:', [0xAA]+lyi(sufadr['gefunden']), ('jsr','txb2'), li(0xFF6)+sta(MSGP),
  'qi_r:', [0x60],
  'qt_alt:', li(skp(T_SKR)&0xFFFF),
  # faden: Skript (kodierter Zeiger A, Bank F7) als Faden mit dem Jungen als Besitzer wie ein Ausloeser (8C:D257: PHY, 8C:D2FD,
  #        +0D = Besitzer, Besitzer +3E hochzaehlen, in 7E:2F28 eintragen). Mesen v145: ohne Besitzer (+0D = 0) Absturz nach a3 3f.
  'faden:', [0x85,0x26]+li(skp(T_SKR)>>16)+[0x85,0x28]+lyi(0x4E89)+[0x22,0x57,0xD2,0x8C, 0xC2,0x30, 0x60],
  # ---- zurueck nach 5E bzw. Ausloeser oben: Tuer-Skript als Faden (geht durch den Tuer-Hook; ein Warp ohne a3-Vorskript
  #      landet falsch: Mesen v145 Karte 05 328,760 statt 696,616)
  #      warp5e merkt den Wunsch nur vor (BEAMRT); gestartet wird in kbild, sobald der Junge frei ist (Mesen v145: gleichzeitig mit
  #      einem Beute-Faden lief das Tuer-Skript nicht) - und nach Zeitablauf (300 Bilder ohne Tuer) erneut.
  'warp5e:', li(1)+sta(BEAMRT)+[0x60],
  'beamst:', li(300)+sta(BEAM)+li(skp(T_TSKR)&0xFFFF), ('jmp','faden'),

  # ================= 4. Bildkette
  'kbild:', [0x22]+VORHER+[0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A]+DB7E,
  lda(AKT)+ai(0xFF), B(BNE,'kb_a'), z(QH)+z(QT), ('jmp','kb_r'),
  'kb_a:', ('jsr','qtick'),
  lda(BEAM), B(BEQ,'kb_a1'), [0x3A]+sta(BEAM), ('jmp','kb_r'),                          # Rueckweg laeuft
  'kb_a1:', lda(BEAMRT), B(BEQ,'kb_a2'), lda(WARPT), B(BNE,'kb_a3'), lda(0x7E4E99)+ai(0x0020), B(BEQ,'kb_a4'),
  lda(BRTW)+[0x1A]+sta(BRTW)+ci(900), B(BCC,'kb_a3'),
  'kb_a4:', z(BRTW), ('jsr','beamst'), 'kb_a3:', ('jmp','kb_r'),
  'kb_a2:',
  lda(TOD), B(BEQ,'kb_b'), ('jmp','kb_r'),
  'kb_b:', lda(0x7E0ADB)+ai(0xFF)+ci(0x5E), B(BEQ,'kb_5e'), ('jmp','kb_n5e'),
  # ---- 5E: Ausloeser oben
  'kb_5e:', lda(0x7E4EA3)+ci(TPZ[0]), B(BCC,'tp_n'), ci(TPZ[1]), B(BCS,'tp_n'), lda(0x7E4EA5)+ci(TPZ[2]), B(BCC,'tp_n'), ci(TPZ[3]), B(BCS,'tp_n'),
  lda(0x004218)+ai(0x8000), B(BEQ,'tp_up'), lda(TPB), B(BNE,'tp_n'), li(1)+sta(TPB), lda(WARPT), B(BNE,'tp_n'),
  lda(0x7E2363)+ai(0xFF)+sta(HFORM),   # v146z34 (Max: Toaster-Hund nach dem Haendler): Hundeform merken
  li(300)+sta(BEAM)+li(skp(T_HSKR)&0xFFFF), ('jsr','faden'), ('jmp','kb_r'),   # v146z30: B im Teleporter -> Haendlerraum
  'tp_up:', z(TPB), 'tp_n:',
  lda(WARPT), B(BEQ,'o_1'), ('jmp','kb_r'),
  'o_1:', lda(0x7E4EA3)+ci(OBEN[0]), B(BCC,'o_aus'), ci(OBEN[1]), B(BCS,'o_aus'),
  lda(0x7E4EA5)+ci(OBEN[2]), B(BCC,'o_aus'), ci(OBEN[3]), B(BCS,'o_aus'),
  lda(INOBEN), B(BEQ,'o_2'), ('jmp','kb_r'),
  'o_2:', li(1)+sta(INOBEN)+lda(SIEGEL)+ai(0x10), B(BEQ,'o_3'), li(0xFF8), ('jsr','qp'), ('jmp','kb_r'),
  'o_3:', li(1)+sta(OBENREQ), ('jsr','warp5e'), ('jmp','kb_r'),
  'o_aus:', z(INOBEN), ('jmp','kb_r'),
  # ---- Bossraum: Sieg erkennen
  'kb_n5e:', lda(BOSSAKT), B(BNE,'kb_bo'), ('jmp','kb_pool'), 'kb_bo:',
  lda(0x7E0ADB)+ai(0xFF)+ci(0x18), B(BNE,'kb_b0'), li(1)+sta(0x307FD4), 'kb_b0:',          # Vulgors Rache (Raptoren) im Bossraum aus
  # v146c: ueber die Cave startet in 18 keine Musik -> Schachbrett-Geraeuschsatz bleibt, Vulgors Geraeusche toeten den Soundchip
  # (Max: Ton weg). Einmal Song 0x01 wie beim normalen Betreten: Skript-Faden 33 04 (Befehl 33 = Musik, Wort bei 8C:87E0+4 = Song 1).
  # (Direkter JSL 8C:85E7 aus dem Bild-Hook stoerte das Sample-Hochladen -> Soundchip sofort tot, Mesen v146d.)
  lda(BMUS), B(BNE,'kb_m1'), li(1)+sta(BMUS)+lda(BOSSI)+[0x4A,0x4A,0x4A, 0x18, 0x69]+w(skp(T_MSKR)&0xFFFF), ('jsr','faden'), 'kb_m1:',   # v146s: Musik JEDES Bosses (Index*4)
  'kb_b1:', lda(WARPT), B(BEQ,'kb_b2'), ('jmp','kb_r'),
  'kb_b2:', ('jsr','bflag'), B(BNE,'kb_b3'), z(BOSSW), ('jmp','kb_r'),          # v146u: Sieg muss am Stueck halten
  'kb_b3:', lda(BOSSW)+[0x1A]+sta(BOSSW)+ci(240), B(BCC,'kb_b3r'), ('jsr','bfl_lade'), lda(TMP3), B(BNE,'kb_b4j'),
  lda(0x7E0ADB)+ai(0xFF)+ci(0x4A), B(BNE,'kb_k6'), lda(BOSSW)+ci(1800), B(BCS,'kb_b4j'), B(BRA,'kb_b3r'),   # v146z2: Endboss-Raum 4A (Wellen) 30 s
  'kb_k6:', lda(BOSSW)+ci(600), B(BCS,'kb_b4j'),                                          # v146u: ohne Sieg-Flag 600 Bilder (Phase 2 abwarten)
  'kb_b3r:', ('jmp','kb_r'),
  'kb_b4j:',
  'kb_b4:', ('jsr','sieg'), ('jsr','warp5e'),
  # v146c goldener Vulgor (18): Rache/Ausgangssperre aus und den Jungen auf den Ausgang stellen -> das Spiel nimmt die Tuer
  # selbst (der Tuer-Faden kam dort erst nach ~2700 Bildern durch, Mesen v146c). Jede Tuer nach dem Sieg fuehrt nach 5E.
  lda(0x7E0ADB)+ai(0xFF)+ci(0x18), B(BNE,'kb_b5'), li(1)+sta(0x307FD4)+li(184)+sta(0x7E4EA3)+li(510)+sta(0x7E4EA5),
  'kb_b5:', ('jmp','kb_r'),
  # ---- Pool-Raum: Saeuberung
  'kb_pool:', lda(RAUMAKT)+ci(1), B(BEQ,'kp_1'), ('jmp','kb_r'),
  'kp_1:', lda(RMUS), B(BNE,'kp_m1'), li(1)+sta(RMUS)+lda(0x7E0ADB)+ai(0x7F)+[0x0A,0x0A, 0x18, 0x69]+w(skp(T_RMUS)&0xFFFF), ('jsr','faden'), 'kp_m1:',   # v146z30: Original-Raummusik
  lda(WARPT), B(BEQ,'kp_2'), ('jmp','kb_r'),
  'kp_2:', lda(CLRW), B(BEQ,'kp_z'), [0x1A]+sta(CLRW)+ci(150), B(BCS,'kp_beam'), ('jmp','kb_r'),
  'kp_beam:', li(2)+sta(RAUMAKT), ('jsr','warp5e'), ('jmp','kb_r'),
  'kp_z:', lda(RZEIT)+ci(0x7000), B(BCS,'kp_z1'), [0x1A]+sta(RZEIT), 'kp_z1:', ai(7), B(BEQ,'kp_z2'), ('jmp','kb_r'),
  'kp_z2:', ('jsr','cnt'),
  lda(LIVE), B(BEQ,'kp_3'), li(1)+sta(SEEN), ('jmp','kb_r'),
  'kp_3:', lda(RZEIT)+ci(120), B(BCS,'kp_4'), ('jmp','kb_r'),
  'kp_4:', lda(PEND), B(BEQ,'kp_5'), ('jmp','kb_r'),
  'kp_5:', lda(SEEN), B(BNE,'kp_clr'), lda(RZEIT)+ci(300), B(BCS,'kp_clr'), ('jmp','kb_r'),
  'kp_clr:', lda(TUERM)+ai(7)+[0x0A, 0xAA]+ldax(T_BIT)+oral(SIEGEL)+sta(SIEGEL), li(0xFF9), ('jsr','qp'), li(1)+sta(CLRW),
  'kb_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  # ---- cnt: LIVE = lebende Gegner (Platz nicht in der Freiliste $3DE3/+5E, Vorlage C536-DF3A (n>=51), KP > 0),
  #           PEND = Spawn-Eintraege (7E:5DC3 bis $0EC2, je 16 Byte) mit Rest-Anzahl +0C > 0
  'cnt:', DB30, lyi(0)+li(0),
  'cn_c:', absw(0x99,FREIM)+[0xC8,0xC8, 0xC0,32,0x00], B(BCC,'cn_c'),
  lyi(40)+lda(0x7E3DE3),
  'cn_w:', ci(0), B(BEQ,'cn_wd'), [0xAA, 0x38, 0xE9,0xE5,0x3D], B(BCC,'cn_wn'),
  [0x8F,0x04,0x42,0x00]+SEP+[0xA9,0x8E, 0x8F,0x06,0x42,0x00]+REP+NOP8+[0xAF,0x14,0x42,0x00]+ci(30), B(BCS,'cn_wn'),
  [0xDA, 0xAA]+SEP+[0xA9,0x01]+absw(0x9D,FREIM)+REP+[0xFA],
  'cn_wn:', ldax(0x7E005E)+[0x88], B(BNE,'cn_w'),
  'cn_wd:', z(LIVE)+z(PEND)+lyi(0)+lxi(0x3DE5),
  'cn_l:', absw(0xB9,FREIM)+ai(0xFF), B(BNE,'cn_s'),
  ldax(0x7E0060)+ci(0xC536), B(BCC,'cn_s'), ci(0xDF3B), B(BCS,'cn_s'), ldax(0x7E002A), B(BEQ,'cn_s'),
  absw(0xEE,LIVE),
  'cn_s:', [0x8A, 0x18, 0x69,0x8E,0x00, 0xAA, 0xC8, 0xC0,30,0x00], B(BCC,'cn_l'),
  lxi(0x5DC3),
  'cn_p:', [0x8A]+cmpl(0x7E0EC2), B(BCS,'cn_pd'), ldax(0x7E000C), B(BEQ,'cn_ps'), absw(0xEE,PEND),
  'cn_ps:', [0x8A, 0x18, 0x69,0x10,0x00, 0xAA], B(BRA,'cn_p'),
  'cn_pd:', [0xAB, 0x60],

  # ================= 5. kverl (soe_hoehle 'verlassen', vor dem Stash-Rueckschrieb): Boss-Flags + Fund-Merker zurueck
  'kverl:', [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A]+DB7E,
  lda(BOSSAKT)+oral(SIEGR), B(BEQ,'kv_1'), ('jsr','bsrest'), z(BOSSAKT)+z(SIEGR),
  'kv_1:', ('jsr','flrest'), z(RAUMAKT)+z(CLRW)+z(OBENREQ)+z(QH)+z(QT)+z(BEAM)+z(BEAMRT),
  [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  'kns:', [0x08, 0xC2,0x30, 0x48], ('jsr','nstock'), z(QH)+z(QT)+z(FLAKT)+z(BEAM)+z(BEAMRT), [0x68, 0x28, 0x6B],

  # ================= 6. kdrop (soe_hoehle FUND, jeder Sieg in der Hoehle)
  'kdrop:', [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A]+DB7E,
  lda(BOSSAKT), B(BEQ,'kd_nb'), ('jmp','kd_r'), 'kd_nb:',   # v146z2 (Max: Orb nach jedem Gegner im Endboss-Raum): keine Funde im Bossraum
  lda(DROPTEST)+ai(0xFF), B(BEQ,'kd_z'), ci(5), B(BCC,'kd_d1'), ('jmp','kd_n'), 'kd_d1:', [0x3A]+sta(TMP1), B(BRA,'kd_s'),
  'kd_z:', ('jsr','rnd'), mod(4), B(BEQ,'kd_ja'),        # v147b (Max: Droprate kleiner): jeder 4.
  ('jmp','kd_r'),        # v146s (Max): nur noch jeder 2. Gegner laesst etwas fallen
  'kd_ja:', ('jsr','rnd'), mod(50), B(BEQ,'kd_sel'), ('jmp','kd_n'), 'kd_sel:',
  ('jsr','rnd'), mod(4), sta(TMP1),
  'kd_s:', lda(TMP1)+[0x0A, 0xAA, 0xFC,0x00,0x00],      # JSR (seltab,X) - Adresse wird unten eingesetzt
  B(BCC,'kd_r'),
  # v146z17 (Max: Orb von normalen Gegnern 1/1000): Seltenes nicht mehr vorraetig -> nur 1:5 Orb (1/2*1/100*1/5), sonst normale Beute
  ('jsr','rnd'), mod(5), B(BEQ,'kd_orb'), ('jmp','kd_n'), 'kd_orb:',
  lda(0x7E0ABA)+ai(0xFF)+jsl(WINC)+[0xC2,0x30]+li(0xFFE), ('jsr','qp'), B(BRA,'kd_r'),
  'kd_n:', ('jsr','rnd'), mod(32), [0x0A, 0xAA]+ldax(T_LOOT), ('jsr','qp'),
  'kd_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  'seltab:', [0]*8,
  # --- Formel (nicht gelernt, ohne Telekinese 21 / Zauberbruecke 28): Bit + Alchemie-Ring (91:CB6F), "<Name> gelernt!"
  'gformel:', ('jsr','rnd'), mod(35), sta(TMP2)+li(35)+sta(TMP3),
  'gf_l:', lda(TMP2)+ci(21), B(BEQ,'gf_n'), ci(28), B(BEQ,'gf_n'),
  [0x0A, 0xAA]+ldax(0xC502E7)+ai(0xFF)+sta(TMP5)+ldax(0xC502A1)+sta(TMP4)+[0xAA]+ldax(0x7E0000)+andl(TMP5)+ai(0xFF), B(BEQ,'gf_ja'),
  # v147b (Max: Formeln auch finden): schon gelernt -> Formel +1
  lda(TMP2)+[0x0A, 0xAA, 0x22,0x40,0x90,0xF0, 0xC2,0x30]+lda(TMP2)+[0x0A, 0xAA]+ldax(0xC5036F)+[0xAA]+lyi(sufadr['plus']), ('jsr','txt'), [0x18, 0x60],
  'gf_n:', lda(TMP2)+[0x1A]+ci(35), B(BCC,'gf_s'), li(0), 'gf_s:', sta(TMP2)+lda(TMP3)+[0x3A]+sta(TMP3), B(BNE,'gf_l'), [0x38, 0x60],
  'gf_ja:', lda(TMP4)+[0xAA]+SEP+ldax(0x7E0000)+oral(TMP5)+stax(0x7E0000)+REP,
  [0xA5,0x12, 0x48]+lda(TMP2)+[0x0A, 0xAA, 0x22,0x6F,0xCB,0x91, 0xC2,0x30, 0x68, 0x85,0x12],
  lda(TMP2)+[0x0A, 0xAA]+ldax(0xC5036F)+[0xAA]+lyi(sufadr['gelernt']), ('jsr','txt'), [0x18, 0x60],
  # --- Waffe (nicht im Besitz, ohne Bazooka/Klasse 6): Besitz-Bit, "<Name> gefunden!"
  'gwaffe:', ('jsr','rnd'), mod(13), sta(TMP2)+li(13)+sta(TMP3),
  'gw_l:', lda(TMP2)+[0x0A, 0x1A,0x1A]+sta(TMP6)+[0xAA]+ldax(0xC50042)+ai(0xFF)+ci(6), B(BEQ,'gw_n'),
  ldax(0xC50026)+ai(0xFF)+sta(TMP5)+ldax(0xC5000A)+sta(TMP4), B(BEQ,'gw_n'), [0xAA]+ldax(0x7E0000)+andl(TMP5)+ai(0xFF), B(BEQ,'gw_ja'),
  # v151 (Max: Waffen auch einzeln aufmotzen): schon im Besitz -> "<Waffe> +1!"
  lda(TMP6)+jsl(WINC)+[0xC2,0x30]+lda(TMP6)+[0xAA]+ldax(0xC43EB4)+[0xAA]+ldax(0xC40002)+[0xAA]+lyi(sufadr['plus']), ('jsr','txt'), [0x18, 0x60],
  'gw_n:', lda(TMP2)+[0x1A]+ci(13), B(BCC,'gw_s'), li(0), 'gw_s:', sta(TMP2)+lda(TMP3)+[0x3A]+sta(TMP3), B(BNE,'gw_l'), [0x38, 0x60],
  'gw_ja:', lda(TMP4)+[0xAA]+SEP+ldax(0x7E0000)+oral(TMP5)+stax(0x7E0000)+REP,
  lda(TMP6)+[0xAA]+ldax(0xC43EB4)+[0xAA]+ldax(0xC40002)+[0xAA]+lyi(sufadr['gefunden']), ('jsr','txt'), [0x18, 0x60],
  # --- Talisman (nicht im Besitz): 7E:243D = 2k (Spiel setzt Bit + Werte), "<Name> erhalten!"
  'gtalis:', ('jsr','rnd'), mod(14), sta(TMP2)+li(14)+sta(TMP3),
  'gt_l:', lda(TMP2)+[0x0A, 0xAA]+ldax(0x8CBFB9)+ai(0xFF)+sta(TMP5)+ldax(0x8CBF91)+[0xAA]+ldax(0x7E0000)+andl(TMP5)+ai(0xFF), B(BEQ,'gt_ja'),
  # v147b (Max: fuer jeden Talisman ein eigener Orb): schon im Besitz -> "<Talisman>-Orb: +1!" (Zaehler 36+k)
  lda(TMP2)+[0x18, 0x69,36,0x00, 0x0A, 0xAA, 0x22,0x40,0x90,0xF0, 0xC2,0x30],
  lda(TMP2)+[0x0A, 0xAA]+ldax(0x8CBFFB)+[0xAA]+lyi(sufadr['orb']), ('jsr','txt'), [0x18, 0x60],
  'gt_ja:', lda(TMP2)+[0x0A]+sta(0x7E243D)+[0xAA]+ldax(0x8CBFFB)+[0xAA]+lyi(sufadr['erhalten']), ('jsr','txt'), [0x18, 0x60],
  # --- Ruestung (Anzahl 7E:231D+Nr = 0): Anzahl 1, "<Name> gefunden!"
  'gruest:', ('jsr','rnd'), mod(40), sta(TMP2)+li(40)+sta(TMP3),
  'gr_l:', lda(TMP2)+[0xAA]+ldax(0x7E231D)+ai(0xFF), B(BEQ,'gr_ja'),
  # v158 (Max: Ruestung nochmal bekommen = +1 %): schon da -> Anzahl +1 (bis 99, soe_ruestung_plus rechnet +1 % je Exemplar)
  ci(99), B(BCS,'gr_n'), SEP+ldax(0x7E231D)+[0x1A]+stax(0x7E231D)+REP,
  lda(TMP2)+[0x0A]+sta(TMP4)+[0x0A,0x0A, 0x18]+adcl(TMP4)+[0xAA]+ldax(0xC44146)+[0xAA]+lyi(sufadr['plus']), ('jsr','txt'), [0x18, 0x60],
  'gr_n:',
  lda(TMP2)+[0x1A]+ci(40), B(BCC,'gr_s'), li(0), 'gr_s:', sta(TMP2)+lda(TMP3)+[0x3A]+sta(TMP3), B(BNE,'gr_l'), [0x38, 0x60],
  'gr_ja:', lda(TMP2)+[0xAA]+SEP+[0xA9,0x01]+stax(0x7E231D)+REP,
  lda(TMP2)+[0x0A]+sta(TMP4)+[0x0A,0x0A, 0x18]+adcl(TMP4)+[0xAA]+ldax(0xC44146)+[0xAA]+lyi(sufadr['gefunden']), ('jsr','txt'), [0x18, 0x60],
  # --- txt: X = Name (Bank C5), Y = Endung (Bank F7) -> MTXT (0x97, Name, Endung, 00), Meldung FFB in die Warteschlange
  'txt:', DB30, [0x5A], SEP+[0xA9,0x97]+absw(0x8D,MTXT), lyi(1),
  'tx_n:', ldax(0xC50000), B(BEQ,'tx_nd'), absw(0x99,MTXT)+[0xE8, 0xC8, 0xC0,26,0x00], B(BCC,'tx_n'),
  'tx_nd:', [0xFA],
  'tx_s:', ldax(TAB), absw(0x99,MTXT), B(BEQ,'tx_sd'), [0xE8, 0xC8], B(BRA,'tx_s'),
  'tx_sd:', REP+[0xAB]+li(0xFFB), ('jmp','qp'),
  'txb2:', DB30, [0x5A], SEP+[0xA9,0x97]+absw(0x8D,MTXT2), lyi(1),
  't2_n:', ldax(0xC50000), B(BEQ,'t2_nd'), absw(0x99,MTXT2)+[0xE8, 0xC8, 0xC0,26,0x00], B(BCC,'t2_n'),
  't2_nd:', [0xFA],
  't2_s:', ldax(TAB), absw(0x99,MTXT2), B(BEQ,'t2_sd'), [0xE8, 0xC8], B(BRA,'t2_s'),
  't2_sd:', REP+[0xAB, 0x60],

  # ================= 7. Boss-Werte (soe_hoehle stat, nach SKAL): A = Wert, X = Vorlage
  'kbkp:', [0x08, 0xC2,0x30, 0x48]+lda(BOSSAKT), B(BEQ,'bk_o'), [0x8A]+cmpl(BOSSV), B(BNE,'bk_o'),
  [0x68]+ci(3750), B(BCC,'bk_m'), li(30000)+[0x28, 0x6B], 'bk_m:', [0x0A,0x0A,0x0A, 0x28, 0x6B],
  'bk_o:', [0x68, 0x28, 0x6B],
  'kbatk:', [0x08, 0xC2,0x30, 0x48]+lda(BOSSAKT), B(BEQ,'bk_o'), [0x8A]+cmpl(BOSSV), B(BNE,'bk_o'),
  [0x68]+ci(20000), B(BCC,'ba_m'), li(30000)+[0x28, 0x6B], 'ba_m:', sta(TMP6)+[0x4A, 0x18]+adcl(TMP6)+[0x28, 0x6B],
  # ================= 8. Spawn-Anzahl (8F:DE7C, ersetzt LDA 7E:2433): in Hoehlen-Raeumen hoechstens 1 -> kein Respawn
  'kcap:', [0xAF,0x33,0x24,0x7E, 0x48]+lda(AKT)+ai(0xFF), B(BEQ,'kc_o'), lda(0x7E0ADB)+ai(0xFF)+ci(0x5E), B(BEQ,'kc_o'),
  lda(BOSSAKT), B(BNE,'kc_o'), [0x68]+ci(2), B(BCC,'kc_r'), li(1), 'kc_r:', [0x6B],
  'kc_o:', [0x68, 0x6B],
]
code, lab = assemble(CODE, t)
code = bytearray(code)
for i, l in enumerate(['kt','kverl','kns','qpl','kdrop','kbkp','kbatk','kcap']):
    a = lab[l]; code[4*i:4*i+4] = bytes([0x5C, a&0xFF, (a>>8)&0xFF, a>>16])
o = lab['seltab'] - CODE
for i, l in enumerate(['gformel','gwaffe','gtalis','gruest']): code[o+2*i:o+2*i+2] = bytes(w(lab[l] & 0xFFFF))
o = lab['kd_s'] - CODE + 6; assert code[o] == 0xFC; code[o+1:o+3] = bytes(w(lab['seltab'] & 0xFFFF))
assert len(code) <= 0x2F00, hex(len(code))
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), 'F3 belegt'; r[o:o+len(code)] = code
o = at(MKT); assert all(b == 0xFF for b in r[o:o+4]), 'MKT belegt'; a = lab['kmtod']; r[o:o+4] = bytes([0x5C, a&0xFF, (a>>8)&0xFF, a>>16])
for a, b in tabs.items():
    o = at(a); assert all(x == 0xFF for x in r[o:o+len(b)]), hex(a); r[o:o+len(b)] = b
def jml(l): a = lab[l]; return bytes([0x5C, a&0xFF, (a>>8)&0xFF, a>>16])
r[o2:o2+4] = jml('c2')
r[o1:o1+4] = jml('text')
a = lab['kcap']; r[o4:o4+4] = bytes([0x22, a&0xFF, (a>>8)&0xFF, a>>16])
a = lab['kbild']; r[o0:o0+4] = bytes([0x22, a&0xFF, (a>>8)&0xFF, a>>16])
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d)
print("Knoten v145 eingebaut (%d Bytes Code, Pool %d, Fund-Merker %d auf %d Karten, gesperrt %s)" % (len(code), NPOOL,
      sum(len(v) for v in FLAGS.values()), sum(1 for v in FLAGS.values() if v), ' '.join('%02X:%03X' % x for x in GESPERRT)))
