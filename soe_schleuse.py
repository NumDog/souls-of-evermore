# Rote Schleuse als Haendler-Teleporter (v160, Max: "mach so eine Schleuse lieber als Trigger fuer den Shop", Spielstand
# "shop teleport das rote" = Karte 46 bei 417,256). Ohne Animation.
#  - Hook 90:9270 (Kartenaufbau fertig, Bild aus; Kette vorne): in der Cave (AKT) auf dem Schachbrett 5E
#      * die 6 Grafikteile der Schleuse (IDs 1,2,3,9,10,11, gemessen beim Laden von Karte 46) ueber den Kachel-Entpacker
#        8C:CC4F ($2E = VRAM-Wort, DB = 80) in freie Kachelplaetze 3C0..3CB / 3D0..3DB (VRAM-Wort 5C00.., beim Schachbrett leer)
#      * 8 eigene Kombis in 7F:9E00 (BG1 leer, BG2 = Teil | Palette 5, Attribut 1010 = Boden wie 5E) und die Zellen
#        (Spalten 9-12, Zeilen 29-30 = um den Teleporter-Punkt 175,485)
#      * DP $00-$FF vorher nach 30:7A00 sichern und danach zurueck (der Kartenlader arbeitet danach weiter)
#  - Bildkette F0:4000 (vorne): auf 5E in der Cave Farben 1-15 der Schleusen-Palette (ROM 9D:C345, Palette 5 von Karte 46) in
#    den Paletten-Puffer 7E:6229 (Palette 5, im Raster des Schachbretts unbenutzt); 20 und 60 Bilder nach dem Laden zusaetzlich
#    direkt ins CGRAM (80:85FA: $26/$28 Quelle, $2E Farbe, X Bytes).
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
def w(v): return [v&0xFF,(v>>8)&0xFF]
CODE = 0xF92000
AKT, PADZ = 0x307002, 0x3070B8
DPSICH = 0x307A00
PAL = 0x9DC345
assert bytes(r[at(PAL):at(PAL)+4]) == bytes.fromhex('5863d652'), bytes(r[at(PAL):at(PAL)+4]).hex()
BREITE = 22
TEILE = [(1,0x3C0), (2,0x3C2), (3,0x3C4), (9,0x3C6), (10,0x3C8), (11,0x3CA)]   # Grafik-ID -> Kachel
# v161 (Max: Animation der Schleuse): Zwischenbilder oben IDs 4..8, unten 12..16 (8/16 = offen, Karte 46 Kombis 512-515)
AOBEN  = [(4,0x3CC), (5,0x3CE), (6,0x3E0), (7,0x3E2), (8,0x3E4)]
AUNTEN = [(12,0x3E6), (13,0x3E8), (14,0x3EA), (15,0x3EC), (16,0x3EE)]
TEILE += AOBEN + AUNTEN
ANIM = 0x3070BA                 # 0 = zu, 1..N laeuft, FF = offen -> soe_knoten startet den Teleport
AKOMBI = 0x7F9E40               # je Bild 4 Kombis: oben links, oben rechts (gespiegelt), unten links, unten rechts (gespiegelt)
AZELLEN = [(29,10), (29,11), (30,10), (30,11)]
SCHRITT, HALT = 6, 60
TIEF = 45                    # v164: so tief sinken, bis die vordere Ebene (Zeilen 30/31) sie ganz verdeckt
# v163 (Max: im Original wird man gefangen, zentriert und faellt hinein): waehrend des Oeffnens Junge/Hund 1 px je Bild zur
# Lochmitte ziehen; offen -> Sprite-Prioritaet 2 (Objekt +22 = 8, wie Skriptbefehl 75 der Omnitopia-Plattform 9C:C763) und
# 1 px je Bild sinken. Untere Lochhaelfte (BG1 mit Vorrang, wie Karte 46 Kombi 514/515) und Boden Zeile 31 (BG1-Vorrang-Kopie)
# verdecken sie.
MX, MY, HX = 176, 466, 176   # Lochmitte (Junge), Hund etwas rechts
VKOMBI = 0x7F9EE0
# v163: auf dem Schachbrett zeichnet das Spiel Junge/Hund immer mit Sprite-Prioritaet 3 -> nicht verdeckbar. Stattdessen
# blenden sie beim Sinken ins Dunkle: Sprite-Paletten 6/7 (Puffer 7E:6347, 64 Byte) alle 8 Bilder halbieren + ins CGRAM
# (80:85FA, Farbe E0). Sicherung 30:7B00, Merker 30:7B40 -> beim naechsten Kartenaufbau zurueck.
SPAL, SSICH, SMERK = 0x7E6347, 0x307B00, 0x307B40
K = {0x10C:0x3C0, 0x10E:0x3C2, 0x120:0x3C4, 0x12C:0x3C6, 0x12E:0x3C8, 0x140:0x3CA}
OBEN  = [(0x10C,0), (0x10E,0), (0x120,0), (0x10C,0x4000)]
UNTEN = [(0x12C,0), (0x12E,0), (0x140,0), (0x12C,0x4000)]
KOMBI = 0x7F9E00
kombis = [0x1400 | K[t] | fl for t,fl in OBEN + UNTEN]
ZELLEN = [(29, 9+i) for i in range(4)] + [(30, 9+i) for i in range(4)]
setz = []
for j,(bg2,(y,x)) in enumerate(zip(kombis, ZELLEN)):
    a = KOMBI + 8*j
    setz += [0xA9]+w(0xE800)+[0x8F]+L(a) + [0xA9]+w(bg2)+[0x8F]+L(a+2) + [0xA9]+w(0x1010)+[0x8F]+L(a+4) + [0xA9,0,0, 0x8F]+L(a+6)
    setz += [0xA9]+w(a & 0xFFFF)+[0x8F]+L(0x7F0000 + 2*(y*BREITE + x))
for f in range(5):
    for k,(kachel,fl) in enumerate([(AOBEN[f][1],0), (AOBEN[f][1],0x4000), (AUNTEN[f][1],0), (AUNTEN[f][1],0x4000)]):
        a = AKOMBI + 32*f + 8*k
        bg1, bg2 = 0xE800, 0x1400|kachel|fl
        if f == 4 and k >= 2: bg1, bg2 = 0x2000|0x1400|kachel|fl, 0xE800      # offen: untere Haelfte vor den Figuren
        att = 0x0010 if f == 4 else 0x1010   # v164: Boden ohne Bit 0x1000 -> das Spiel zeichnet Figuren dort mit Prioritaet 2 (8F:C73E)
        setz += [0xA9]+w(bg1)+[0x8F]+L(a) + [0xA9]+w(bg2)+[0x8F]+L(a+2) + [0xA9]+w(att)+[0x8F]+L(a+4) + [0xA9,0,0, 0x8F]+L(a+6)
for k in range(4):
    a = VKOMBI + 8*k
    setz += [0xA9]+w(0x2460)+[0x8F]+L(a) + [0xA9]+w(0x0460)+[0x8F]+L(a+2) + [0xA9]+w(0x0010)+[0x8F]+L(a+4) + [0xA9,0,0, 0x8F]+L(a+6)
# Zelle setzen + in die Kachel-Warteschlange des Spiels (wie soe_funde v144: $0F3C sperrt den NMI, $1172 = Index,
# $1176/$11F6 = Wort/VRAM-Adresse, Fenster BG1 $0F8E-$0F94, BG2 $0F96-$0F9C, BG2-Adresse | 0400). DB = 7E, Y = Ring-Index.
def zelle(y, x, kombi, n):
    c = [[0xA9]+w(kombi & 0xFFFF)+[0x8F]+L(0x7F0000 + 2*(y*BREITE + x))]
    for lay,(f0,f1,f2,f3),off,orr in ((1,(0x0F8E,0x0F90,0x0F92,0x0F94),0,0), (2,(0x0F96,0x0F98,0x0F9A,0x0F9C),2,0x0400)):
        s = 'z%d_%d' % (n, lay)
        c += [[0xA9]+w(y)+[0xCD]+w(f0), ('bra8',0x90,s), [0xCD]+w(f1), ('bra8',0xB0,s),
              [0xA9]+w(x)+[0xCD]+w(f2), ('bra8',0x90,s), [0xCD]+w(f3), ('bra8',0xB0,s),
              [0xAF]+L(kombi+off)+[0x99,0x76,0x11, 0xA9]+w((((y&31)<<5)|(x&31))|orr)+[0x99,0xF6,0x11],
              [0xC8,0xC8, 0xC0,0x80,0x00], ('bra8',0xD0,s), [0xA0,0x00,0x00], s+':']
    return c
def bild(f, n0):
    if f == 0: kom = [KOMBI+8*1, KOMBI+8*2, KOMBI+8*5, KOMBI+8*6]
    else: kom = [AKOMBI + 32*(f-1) + 8*k for k in range(4)]
    out = []
    if f == 5:
        for k,(y,x) in enumerate([(31,9), (31,10), (31,11), (31,12)]):
            for e in zelle(y, x, VKOMBI+8*k, 100+n0+k): out.append(e)
    for k,((y,x),kb) in enumerate(zip(AZELLEN, kom)):
        c = zelle(y, x, kb, n0+k)
        for e in c: out.append(e)
    return out
def zieh(adr, ziel, lab):   # Wert 1 px zum Ziel
    return [[0xAF]+L(adr)+[0xC9]+w(ziel), ('bra8',0xF0,lab), ('bra8',0x90,lab+'k'), [0x3A], ('bra8',0x80,lab+'s'), lab+'k:', [0x1A], lab+'s:', [0x8F]+L(adr), lab+':']
fang = zieh(0x7E4EA3, MX, 'zjx') + zieh(0x7E4EA5, MY, 'zjy') + zieh(0x7E4F51, HX, 'zhx') + zieh(0x7E4F53, MY, 'zhy')
laden = []
for gid, kachel in TEILE:
    laden += [0xA9]+w(0x2000 + 16*kachel)+[0x85,0x2E, 0xA9]+w(gid)+[0x22,0x4F,0xCC,0x8C, 0xC2,0x30]
o9 = at(0x909270); assert r[o9] == 0x22; vor9 = list(r[o9+1:o9+4])
o0 = at(0xF04000); assert r[o0] == 0x22; vor0 = list(r[o0+1:o0+4])
code, lab = assemble(CODE, [
  'kh:', [0x22]+vor9, [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A],
  [0xAF]+L(SMERK)+[0x29,0xFF,0x00], ('bra8',0xF0,'kh_0'),
  [0xA9,0x00,0x00, 0x8F]+L(SMERK),   # v164: nur Merker loeschen (kein Abdunkeln mehr, nichts zurueckzuschreiben)
  'kh_0:',
  [0xAF]+L(AKT)+[0x29,0xFF,0x00], ('bra8',0xF0,'kh_n'),
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x5E,0x00], ('bra8',0xF0,'kh_ja'),
  'kh_n:', ('jmp','kh_r'), 'kh_ja:',
  setz,
  [0x8B, 0xA2,0x00,0x00, 0xA0]+w(DPSICH & 0xFFFF)+[0xA9,0xFF,0x00, 0x54,0x30,0x00, 0xAB],   # DP 00:0000-00FF -> 30:7A00
  [0x8B, 0xF4,0x80,0x80, 0xAB,0xAB], laden, [0xAB],
  [0x8B, 0xA2]+w(DPSICH & 0xFFFF)+[0xA0,0x00,0x00, 0xA9,0xFF,0x00, 0x54,0x00,0x30, 0xAB],   # zurueck
  [0xA9,0x01,0x00, 0x8F]+L(PADZ), [0xA9,0x00,0x00, 0x8F]+L(ANIM),
  'kh_r:', [0x7A, 0xFA, 0x68, 0x28, 0x6B],
  # ---- Bildkette
  'kb:', [0x22]+vor0, [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B],
  [0xAF]+L(AKT)+[0x29,0xFF,0x00], ('bra8',0xF0,'kb_r'),
  [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xC9,0x5E,0x00], ('bra8',0xD0,'kb_r'),
  [0xA2]+w(PAL & 0xFFFF)+[0xA0,0x29,0x62, 0xA9,29,0x00, 0x54,0x7E,PAL>>16],          # 30 Byte -> 7E:6229 (MVN 7E,9D)
  ('jsr','anim'),
  [0xAF]+L(PADZ)+[0x29,0xFF,0x00], ('bra8',0xF0,'kb_r'), [0x1A, 0x8F]+L(PADZ),
  [0xC9,21,0x00], ('bra8',0xF0,'kb_cg'), [0xC9,61,0x00], ('bra8',0xD0,'kb_r'), [0xA9,0x00,0x00, 0x8F]+L(PADZ),
  'kb_cg:', [0xA5,0x26, 0x48, 0xA5,0x28, 0x48, 0xA5,0x2E, 0x48],
  [0xA9]+w(PAL & 0xFFFF)+[0x85,0x26, 0xA9,PAL>>16,0x00, 0x85,0x28, 0xA9,0x51,0x00, 0x85,0x2E, 0xA2,30,0x00, 0x22,0xFA,0x85,0x80, 0xC2,0x30],
  [0x68, 0x85,0x2E, 0x68, 0x85,0x28, 0x68, 0x85,0x26],
  'kb_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  # ---- anim: ANIM 1.. -> alle SCHRITT Bilder naechstes Bild (1..5), danach HALT Bilder offen, dann FF (Teleport)
  'anim:', [0xAF]+L(ANIM)+[0x29,0xFF,0x00], ('bra8',0xD0,'an_1'), ('bra8',0x80,'an_0'), 'an_1:', [0xC9,0xFF,0x00], ('bra8',0xD0,'an_2'),
  'an_0:',
  [0xAF]+L(SMERK)+[0x29,0xFF,0x00], ('bra8',0xF0,'an_1r'), [0xA9]+w(TIEF), ('jsr','halt'), 'an_1r:', [0x60],   # v164: bis zum Kartenwechsel unten festhalten
  'an_2:', [0x1A, 0x8F]+L(ANIM), [0xC9]+w(5*SCHRITT+HALT), ('bra8',0x90,'an_3'), [0xA9,0xFF,0x00, 0x8F]+L(ANIM), [0x60],
  'an_3:', [0x48, 0xC9]+w(5*SCHRITT+1), ('bra8',0xB0,'an_s'),
  *fang, ('jmp','an_3e'),                                                           # oeffnen: zur Mitte ziehen
  # v164 (Max: verdeckt nichts, nur schwarz; Hund laeuft weg): Prioritaet 2 ueber den Zeichen-Hook (SMERK = 1), sinken bis
  # ganz hinter der vorderen Ebene (TIEF px), festhalten bis zum Kartenwechsel
  'an_s:', [0xA9,0x01,0x00, 0x8F]+L(SMERK), [0xA3,0x01, 0x38, 0xE9]+w(5*SCHRITT+1), [0xC9]+w(TIEF), ('bra8',0x90,'an_sk'), [0xA9]+w(TIEF), 'an_sk:',
  ('jsr','halt'),
  'an_3e:', [0x68], [0x8F,0x04,0x42,0x00, 0xE2,0x20, 0xA9,SCHRITT, 0x8F,0x06,0x42,0x00, 0xC2,0x20, 0xEA,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA],
  [0xAF,0x16,0x42,0x00], ('bra8',0xF0,'an_4'), [0x60], 'an_4:',                 # nur am Schrittanfang
  [0xAF,0x14,0x42,0x00, 0xC9,0x06,0x00], ('bra8',0x90,'an_5'), [0x60], 'an_5:',  # Bild 1..5
  [0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB, 0xEE,0x3C,0x0F, 0xAC,0x72,0x11],
  [0xC9,0x01,0x00], ('bra8',0xD0,'b2'), ('jmp','f1'), 'b2:', [0xC9,0x02,0x00], ('bra8',0xD0,'b3'), ('jmp','f2'),
  'b3:', [0xC9,0x03,0x00], ('bra8',0xD0,'b4'), ('jmp','f3'), 'b4:', [0xC9,0x04,0x00], ('bra8',0xD0,'b5'), ('jmp','f4'), 'b5:', ('jmp','f5'),
  'f1:', *bild(1,10), ('jmp','an_e'), 'f2:', *bild(2,20), ('jmp','an_e'), 'f3:', *bild(3,30), ('jmp','an_e'),
  'f4:', *bild(4,40), ('jmp','an_e'), 'f5:', *bild(5,50),
  'an_e:', [0x8C,0x72,0x11, 0xCE,0x3C,0x0F, 0xAB, 0x60],
  # ---- halt: A = Tiefe -> Junge/Hund in der Lochmitte, um A nach unten versetzt
  'halt:', [0x18, 0x69]+w(MY)+[0x8F,0xA5,0x4E,0x7E, 0x8F,0x53,0x4F,0x7E, 0xA9]+w(MX)+[0x8F,0xA3,0x4E,0x7E, 0xA9]+w(HX)+[0x8F,0x51,0x4F,0x7E],
  # v164: Zellnummer (+3A) auf die Lochzelle unter den Figuren (8F:AF96 liest daraus jedes Bild +3C = Boden-Attribut;
  # Loch-Kombis ohne Bit 0x1000 -> 8F:C73E waehlt Sprite-Prioritaet 2 -> die vordere Ebene verdeckt sie)
  [0xAF,0xA5,0x4E,0x7E, 0x4A,0x4A,0x4A,0x4A, 0x48, 0x0A, 0x48, 0x0A, 0x48, 0x0A,0x0A, 0x18, 0x63,0x01, 0x18, 0x63,0x03],   # 22*Zeile
  [0x83,0x05, 0x68, 0x68, 0x68, 0x18, 0x69]+w(MX//16)+[0x0A, 0x8F,0xC3,0x4E,0x7E, 0x8F,0x71,0x4F,0x7E, 0x60],
  # ---- dunkel: Paletten 6/7 aus der Sicherung, je Farbe Stufe (SMERK+2) mal halbiert, ins CGRAM
  'dunkel:', [0xA2,0x02,0x00],
  'dk_l:', [0xBF]+L(SSICH)+[0xDA, 0x48, 0xAF]+L(SMERK+2)+[0xAA, 0x68],
  'dk_s:', [0x4A, 0x29,0xEF,0x3D, 0xCA], ('bra8',0xD0,'dk_s'), [0xFA, 0x9F]+L(SPAL)+[0xE8,0xE8, 0xE0,0x40,0x00], ('bra8',0x90,'dk_l'),
  [0xA5,0x26, 0x48, 0xA5,0x28, 0x48, 0xA5,0x2E, 0x48],
  [0xA9]+w(SPAL & 0xFFFF)+[0x85,0x26, 0xA9,0x7E,0x00, 0x85,0x28, 0xA9,0xE0,0x00, 0x85,0x2E, 0xA2,64,0x00, 0x22,0xFA,0x85,0x80, 0xC2,0x30],
  [0x68, 0x85,0x2E, 0x68, 0x85,0x28, 0x68, 0x85,0x26, 0x60],
])
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), 'F9:2000 belegt'; r[o:o+len(code)] = code

r[o9:o9+4] = bytes([0x22]+L(lab['kh'])); r[o0:o0+4] = bytes([0x22]+L(lab['kb']))
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Rote Schleuse auf 5E, %d Bytes" % len(code))
