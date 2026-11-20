# Gegner-Info (v146g, Max): trifft man einen Gegner, erscheint oben eine Meldung mit Name, KP, Erfahrung und Geld dieses Gegners.
# Trifft man einen anderen, wechselt sie (nach kurzer Pause, damit nicht jedes Bild eine neue Meldung startet).
#  - Treffer: Schadens-Kette 8F:C1CC (vorne einhaengen, Rest wie bisher). Y = getroffenes Objekt; Junge (4E89) / Hund (4F37) zaehlen nicht.
#  - Anzeige: Bild-Kette F0:4000 (vorne einhaengen). Text in 7E:EE00, Text-Nr 0xFF7 (soe_knoten 'text'), gezeigt ueber MSGP
#    (30:7026, soe_hoehle startet damit den Meldungs-Faden `52 <Nr>`), nur wenn keine andere Meldung ansteht.
#  - Erfahrung/Geld wie beim Besiegen (Schwierigkeit, Cave-Formel): soe_belohnung INFO F0:3FB8 / INFO_G F0:3FD3, Ergebnis 30:7EF8/7EFA.
import os, sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
def w(v): return [v&0xFF, (v>>8)&0xFF]
CODE = 0xF1F000
GTXT, GOBJ, GNEU, GCOOL, Q0, Q1, REM, DCNT, TPL = 0xEE00, 0xEE60, 0xEE62, 0xEE64, 0xEE66, 0xEE68, 0xEE6A, 0xEE6C, 0xEE6E   # (7E:EF00 = Talisman-Puffer)
MSGP, V0, V1 = 0x307026, 0x307EF8, 0x307EFA
INFO, INFO_G = 0xF03FB8, 0xF03FD3
GHIT = 0xEE72                              # v146o: Bilder seit dem letzten Treffer (180 -> 0)
MTAB, MKART, MMAX = 0xED00, 0xED80, 0xED86   # v155: volle KP je Objekt-Platz (FBUF wird nur mit SOE_POS_OBEN gebraucht)
FRM, FBUF, FLEN = 0xEE70, 0xED00, 0x100           # Rahmen gezeichnet? / Sicherung der oberen 4 Zeilen (32*2*4 Byte)
RSP, RZE, RBR, RHO, TZE = 1, 0, 30, 4, 1      # Rahmen Spalte/Zeile/Breite/Hoehe, Textzeile
ZEILE = 1                                   # v146k (Max): Info oben statt mitten im Bild
# Souls-Namen der Cave-Bosse (Karte -> Name), Tabellen ab NKART in Bank F1
# (Max: vorhandene Bosse behalten ihre Namen - nur NEUE Bosse bekommen hier einen Eintrag; Karte 0xFF = Platzhalter)
SOULS = [(0xFF, b'-')]
NKART = 0xF1FA00; NZEIG = NKART + 2*len(SOULS)
OBEN = bool(os.environ.get('SOE_POS_OBEN'))   # Test: Statuszeile oben (Balken durch geteilte Text-Ebene, s. KANBAN)
OURM = 0xEE70                               # v146z14: eigene Statuszeile offen (frueher FRM, unbenutzt)
COOL = 90                                   # Bilder bis zur naechsten Meldung
SEP, REP = [0xE2,0x20], [0xC2,0x20]
def put(t):                                 # Zeichen an GTXT,Y anhaengen (M 16 -> 8 -> 16)
    out = list(SEP)                         # Kopie! (sonst haengt der Text-Code an der gemeinsamen SEP-Liste)
    for ch in t.encode('latin1'): out += [0xA9, ch, 0x99]+w(GTXT)+[0xC8]
    return out + REP

o = at(0x8FC1CC); assert r[o] == 0x22; PREVDMG = list(r[o+1:o+4])
o0 = at(0xF04000); assert r[o0] == 0x22; PREVBILD = list(r[o0+1:o0+4])

code, lab = assemble(CODE, [
  # ---- Treffer (aus 8F:C1CC): erst die bisherige Kette, dann Objekt merken. A/Flags bleiben (Aufrufer: BPL auf A)
  'dmg:', [0x22]+PREVDMG+[0x08, 0x48],
  [0xC0,0x89,0x4E], ('bra8',0xF0,'dm_r'), [0xC0,0x37,0x4F], ('bra8',0xF0,'dm_r'),
  [0xC2,0x30, 0xDA, 0xBB], ('jsr','mrec'), [0xFA],                   # v155: volle KP vor dem ersten Treffer merken
  [0x98, 0x8F]+L(0x7E0000|GOBJ)+[0xA9,0x01,0x00, 0x8F]+L(0x7E0000|GNEU),
  [0xA9,180,0x00, 0x8F]+L(0x7E0000|GHIT),                          # v146o: Treffer-Zeitfenster (soe_vulgor_extra: Verwirrung nach dem Wegschubsen)
  'dm_r:', [0x68, 0x28, 0x6B],
  # ---- jedes Bild
  'bild:', [0x22]+PREVBILD+[0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB],
  # v155: volle KP jedes Monsters gleich beim Erscheinen merken (Platz-Tabelle MTAB, Kartenwechsel leert)
  [0xAD,0xDB,0x0A, 0x29,0xFF,0x00, 0xCD]+w(MKART), ('bra8',0xF0,'ms_0'), [0x8D]+w(MKART)+[0xA2,0x00,0x00, 0xA9,0x00,0x00],
  'ms_c:', [0x9D]+w(MTAB)+[0xE8,0xE8, 0xE0,0x80,0x00], ('bra8',0x90,'ms_c'),
  'ms_0:', [0xA2,0x00,0x00, 0xA0,0xE5,0x3D],
  'ms_l:', [0xB9,0x60,0x00, 0xC9,0x36,0xC5], ('bra8',0x90,'ms_n'), [0xC9,0x3B,0xDF], ('bra8',0xB0,'ms_n'),
  [0xDD]+w(MTAB), ('bra8',0xF0,'ms_g'), [0x9D]+w(MTAB)+[0xB9,0x2A,0x00, 0x9D]+w(MTAB+2), ('bra8',0x80,'ms_n'),
  'ms_g:', [0xB9,0x2A,0x00, 0xDD]+w(MTAB+2), ('bra8',0x90,'ms_n'), [0x9D]+w(MTAB+2),
  'ms_n:', [0xE8,0xE8,0xE8,0xE8, 0x98, 0x18, 0x69,0x8E,0x00, 0xA8, 0xC9,0x89,0x4E], ('bra8',0x90,'ms_l'),
  # WRAM ist beim Einschalten nicht 0 -> Pause ausserhalb 0..COOL = 0 (Mesen: 27749)
  [0xAD]+w(GHIT)+[0xC9,181,0x00], ('bra8',0x90,'b_hk'), [0x9C]+w(GHIT), 'b_hk:', [0xAD]+w(GHIT), ('bra8',0xF0,'b_h0'), [0x3A, 0x8D]+w(GHIT), 'b_h0:',
  [0xAD]+w(GCOOL)+[0xC9,COOL+1,0x00], ('bra8',0x90,'b_ck'), [0x9C]+w(GCOOL), 'b_ck:',
  [0xAD]+w(GCOOL), ('bra8',0xF0,'b_c0'), [0x3A, 0x8D]+w(GCOOL), 'b_c0:',
  # v146z14 (Max: Info oben, ohne Balken): nach dem Schliessen unserer Statuszeile oben bleiben die Zeilen 0-3 der
  # Text-Ebene (7F:C800) mit Kachel 03FF gefuellt (unten raeumt die Lebensleiste auf, oben niemand) -> selbst auf 0FFF
  # zuruecksetzen und per DMA-Auftrag (80:8650: $26/$28 Quelle, $2E VRAM, X Bytes) hochladen. Nur einmal je eigener Meldung.
] + ([
  [0xAD,0x2B,0x0B, 0x29,0xFF,0x7F], ('bra8',0xF0,'b_ci'), [0xA9,0x01,0x00, 0x8D]+w(OURM), ('bra8',0x80,'b_cz'),   # irgendeine Statuszeile offen -> merken
  'b_ci:', [0xAD]+w(OURM), ('bra8',0xF0,'b_cz'),
  [0xAD,0x2F,0x0B, 0xCD,0x31,0x0B], ('bra8',0xD0,'b_cz'), [0x9C]+w(OURM), [0xA2,0x00,0x00],
  'b_cl:', [0xBF,0x00,0xC8,0x7F, 0xC9,0xFF,0x03], ('bra8',0xD0,'b_cn'), [0xA9,0xFF,0x0F, 0x9F,0x00,0xC8,0x7F],
  'b_cn:', [0xE8, 0xE8, 0xE0,0x00,0x01], ('bra8',0xD0,'b_cl'),
  [0xA5,0x26, 0x48, 0xA5,0x28, 0x48, 0xA5,0x2E, 0x48, 0xA9,0x00,0xC8, 0x85,0x26, 0xA9,0x7F,0x00, 0x85,0x28, 0xA9,0x00,0x08, 0x85,0x2E,
   0xA2,0x00,0x01, 0x22,0x50,0x86,0x80, 0x68, 0x85,0x2E, 0x68, 0x85,0x28, 0x68, 0x85,0x26],
  'b_cz:',
] if OBEN else []) + [
  [0xAD]+w(GNEU), ('bra8',0xD0,'b_1'), ('jmp','raus'),
  'b_1:', [0xAD]+w(GCOOL), ('bra8',0xF0,'b_2'), ('jmp','raus'),
  'b_2:', [0xAF,0x90,0x7E,0x30, 0x29,0x00,0x08], ('bra8',0xF0,'b_2a'), ('jmp','raus'), 'b_2a:',   # v146z15: Treffer-Info im Menue aus
  [0xAF]+L(MSGP)+([0xA9,0x01,0x00] if os.environ.get('SOE_OHNE_OBEN') else []), ('bra8',0xF0,'b_3'), ('jmp','raus'),   # Test SOE_OHNE_OBEN: A=1 -> nie Meldung oben
  'b_3:', [0x9C]+w(GNEU),
  [0xAE]+w(GOBJ)+[0xBD,0x60,0x00, 0xC9,0x78,0xB6], ('bra8',0xB0,'b_4'), ('jmp','raus'),
  'b_4:', [0xC9,0x3B,0xDF], ('bra8',0x90,'b_5'), ('jmp','raus'),
  'b_5:', [0x8D]+w(TPL), ('jsr','mk'),
  SEP, [0xA9,0x00, 0x99]+w(GTXT), REP,
  # v146z12 (Max: schwarzer Streifen): nicht mehr als Dialog-Skript (MSGP/FF7), sondern ueber die Statuszeilen-Warteschlange
  # des Spiels (8C:C8E4 = Text [$22] einreihen; Oeffnen/Schliessen 8C:C920/C906 macht das Spiel selbst mit Zeitgeber)
  ([0xA9,0x30,0xA9, 0xA2,0x06,0x00, 0x22,0xDB,0xCF,0x90] if OBEN else []),   # Test OBEN: Fensterfarben wie beim Anvisieren (Palette 6 = 90:A930)
  [0xA5,0x22, 0x48, 0xA5,0x24, 0x48, 0xA9]+w(GTXT)+[0x85,0x22, 0xA9,0x7E,0x00, 0x85,0x24, 0x22,0xE4,0xC8,0x8C, 0x68, 0x85,0x24, 0x68, 0x85,0x22],
  [0xA9,COOL,0x00, 0x8D]+w(GCOOL),
  'raus:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
  # ---- Zielbestimmung (8C:8D9B, statt Namenszeiger laden): X = Vorlage, Y = Zeiger in die Zielliste ($0000,Y = Objekt)
  #      -> $22/$24 auf unseren Text "Name nKP eEP gG [Anzahl lebender Gegner]"; X bleibt
  'ziel:', [0x8B, 0xDA, 0x5A, 0xF4,0x7E,0x7E, 0xAB,0xAB],
  # v154 (Max: Zauber auf sich selbst zeigte "taten" / "stische Form"): Junge (4E89) / Hund (4F37) -> Original-Namen
  [0xB9,0x00,0x00, 0xC9,0x89,0x4E], ('bra8',0x90,'z_mon'),
  [0x7A, 0xFA, 0xAB, 0xBF,0x00,0x00,0x8E, 0x85,0x22, 0xBF,0x01,0x00,0x8E, 0x85,0x23, 0x6B],
  'z_mon:', [0xB9,0x00,0x00, 0x8D]+w(GOBJ)+[0x8A, 0x8D]+w(TPL), ('jsr','mk'),
  put(' ['), ('jsr','cnt'), [0x9C]+w(Q1), ('jsr','dec'), put(']'),
  SEP, [0xA9,0x00, 0x99]+w(GTXT), REP,
  [0xA9]+w(GTXT)+[0x85,0x22, 0xA9,0x7E,0x00, 0x85,0x24],
  [0x7A, 0xFA, 0xAB, 0x6B],
  # ---- mrec (v155): X = Objekt -> volle KP je Objekt-Platz merken (7E:ED00 + 4*Platz: Vorlage, KP; Kartenwechsel leert),
  #      Ergebnis 7E:ED86 = volle KP. X/Y bleiben.
  'mrec:', [0x08, 0xC2,0x30, 0x8B, 0xF4,0x7E,0x7E, 0xAB,0xAB, 0xDA, 0x5A],
  [0xAD,0xDB,0x0A, 0x29,0xFF,0x00, 0xCD]+w(MKART), ('bra8',0xF0,'mr_1'), [0x8D]+w(MKART)+[0xA2,0x00,0x00, 0xA9,0x00,0x00],
  'mr_c:', [0x9D]+w(MTAB)+[0xE8,0xE8, 0xE0,0x80,0x00], ('bra8',0x90,'mr_c'),
  'mr_1:', [0xA3,0x03, 0xA8, 0x38, 0xE9,0xE5,0x3D], ('bra8',0x90,'mr_x'), [0xA2,0x00,0x00],
  'mr_s:', [0xC9,0x8E,0x00], ('bra8',0x90,'mr_d'), [0xE9,0x8E,0x00, 0xE8], ('bra8',0x80,'mr_s'),
  'mr_d:', [0xE0,0x20,0x00], ('bra8',0xB0,'mr_x'), [0x8A, 0x0A,0x0A, 0xAA],
  [0xB9,0x60,0x00, 0xDD]+w(MTAB), ('bra8',0xD0,'mr_n'), [0xB9,0x2A,0x00, 0xDD]+w(MTAB+2), ('bra8',0x90,'mr_a'), ('bra8',0xF0,'mr_a'),
  'mr_n:', [0xB9,0x60,0x00, 0x9D]+w(MTAB)+[0xB9,0x2A,0x00, 0x9D]+w(MTAB+2),
  'mr_a:', [0xBD]+w(MTAB+2)+[0x8D]+w(MMAX), ('bra8',0x80,'mr_r'),
  'mr_x:', [0xB9,0x2A,0x00, 0x8D]+w(MMAX),
  'mr_r:', [0x7A, 0xFA, 0xAB, 0x28, 0x60],
  # ---- cnt: Q0 = lebende Gegner (Vorlage ab Nr 44, KP > 0) in den Objekten 3DE5..4E89 (Junge/Hund danach)
  'cnt:', [0x9C]+w(Q0)+[0xA2,0xE5,0x3D],
  'c_l:', [0xBD,0x60,0x00, 0xC9,0xA0,0xC2], ('bra8',0x90,'c_n'), [0xC9,0x3B,0xDF], ('bra8',0xB0,'c_n'),
  [0xBD,0x2A,0x00], ('bra8',0xF0,'c_n'), [0xEE]+w(Q0),
  'c_n:', [0x8A, 0x18, 0x69,0x8E,0x00, 0xAA, 0xE0,0x89,0x4E], ('bra8',0x90,'c_l'),
  # v146m (Max: "insgesamt im Raum"): + noch nicht erschienene aus der Erscheinen-Liste 7E:5DC3 (je 0x10 B, Rest +0C, Ende 7E:0EC2)
  [0xA2,0xC3,0x5D],
  'c_p:', [0xEC,0xC2,0x0E], ('bra8',0xB0,'c_pd'), [0xBD,0x0C,0x00, 0x29,0xFF,0x00, 0x18, 0x6D]+w(Q0)+[0x8D]+w(Q0),
  [0x8A, 0x18, 0x69,0x10,0x00, 0xAA], ('bra8',0x80,'c_p'),
  'c_pd:', [0x60],
  # ---- mk: Text "Name nKP eEP gG" (ohne Ende) nach GTXT, Y = Laenge. Braucht GOBJ, TPL, DB = 7E
  # Name (Vorlage +0 = Zeiger in Bank C5), hoechstens 12 Zeichen (die Meldung zeigt nur EINE Zeile)
  # v146n (Max): Souls-Namen fuer die Cave-Bosse (BOSSAKT 30:703A, Vorlage = BOSSV 30:70CE) je Bossraum-Karte
  'mk:', [0xAF,0x3A,0x70,0x30], ('bra8',0xF0,'mk_n'), [0xAD]+w(TPL)+[0xCF,0xCE,0x70,0x30], ('bra8',0xD0,'mk_n'),
  [0xAD,0xDB,0x0A, 0x29,0xFF,0x00, 0xA2,0x00,0x00],
  'mk_s:', [0xDF]+L(NKART), ('bra8',0xF0,'mk_f'), [0xE8,0xE8, 0xE0]+w(2*len(SOULS)), ('bra8',0x90,'mk_s'), ('bra8',0x80,'mk_n'),
  'mk_f:', [0xBF]+L(NZEIG)+[0xAA, 0xA0,0x00,0x00],
  'mk_c:', SEP, [0xBF,0x00,0x00,NKART>>16], ('bra8',0xF0,'mk_ce'), [0x99]+w(GTXT), REP, [0xE8, 0xC8], ('bra8',0x80,'mk_c'),
  'mk_ce:', REP, ('jmp','nm_f'),
  'mk_n:', [0xAE]+w(TPL)+[0xBF,0x00,0x00,0x8E, 0xAA, 0xA0,0x00,0x00],
  'nm:', SEP, [0xBF,0x00,0x00,0xC5], ('bra8',0xF0,'nm_e'), [0x99]+w(GTXT), REP, [0xE8, 0xC8, 0xC0,12,0x00], ('bra8',0x90,'nm'), ('bra8',0x80,'nm_f'),
  'nm_e:', REP, 'nm_f:',
  # KP (aktuell)
  # v155 (Max: "427/427" statt "427KP"): aktuell / hoechster gemerkter Wert (mrec)
  put(' '), [0xAE]+w(GOBJ), ('jsr','mrec'), [0xBD,0x2A,0x00, 0x8D]+w(Q0)+[0x9C]+w(Q1), ('jsr','dec'), put('/'),
  [0xAF]+L(0x7E0000|MMAX)+[0x8D]+w(Q0)+[0x9C]+w(Q1), ('jsr','dec'), put(' '),
  # Erfahrung / Geld wie beim Besiegen
  [0x5A, 0xAE]+w(TPL)+[0x22]+L(INFO)+[0x7A, 0xAF]+L(V0)+[0x8D]+w(Q0)+[0xAF]+L(V1)+[0x8D]+w(Q1), ('jsr','dec'), put('EP '),
  [0x5A, 0xAE]+w(TPL)+[0x22]+L(INFO_G)+[0x7A, 0xAF]+L(V0)+[0x8D]+w(Q0)+[0xAF]+L(V1)+[0x8D]+w(Q1), ('jsr','dec'), put('G'), [0x60],
  # ---- Meldungs-Zeile (8C:C962 statt LDA #$0014 ; STA $0361): unsere Info (Text 7E:EE00) oben in Zeile ZEILE, sonst Zeile 20
  # v146z9 (Max: schwarzer Streifen ueber der Lebensleiste): ALLE einzeiligen Meldungen oben - sonst zeichnete das Spiel
  # beim Neuzeichnen/Schliessen die leere Box in Zeile 20 (schwarzer Balken), wenn \$22 gerade nicht auf unseren Text zeigte.
  'pos:',
  # (v146m-Versuch Goldrahmen ueber 8C:BA0E/B397 verworfen: 7F:C800 ist im Spiel nicht die Anzeigeebene, die Lebensleiste verschwand)
  [0xA9,ZEILE,0x00, 0x8D,0x61,0x03, 0x6B],
  'p_n:', [0xA9,0x14,0x00, 0x8D,0x61,0x03, 0x6B],
  # ---- dec: Q1:Q0 (32 Bit) dezimal an GTXT,Y anhaengen (Y weiter)
  'dec:', [0x9C]+w(DCNT),
  'd_l:', [0x9C]+w(REM)+[0xA2,32,0x00],
  'd_b:', [0x0E]+w(Q0)+[0x2E]+w(Q1)+[0x2E]+w(REM)+[0xAD]+w(REM)+[0xC9,10,0x00], ('bra8',0x90,'d_nb'),
  [0xE9,10,0x00, 0x8D]+w(REM)+[0xEE]+w(Q0),
  'd_nb:', [0xCA], ('bra8',0xD0,'d_b'),
  [0xAD]+w(REM)+[0x18, 0x69,0x30,0x00, 0x48, 0xEE]+w(DCNT),
  [0xAD]+w(Q0)+[0x0D]+w(Q1), ('bra8',0xD0,'d_l'),
  'd_o:', [0x68], SEP, [0x99]+w(GTXT), REP, [0xC8, 0xCE]+w(DCNT), ('bra8',0xD0,'d_o'), [0x60],
])
assert len(code) < 0x400
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), "Platz belegt"; r[o:o+len(code)] = code
nt = b''.join(m.to_bytes(2,'little') for m,_ in SOULS); nz = b''; nb = b''; p0 = NZEIG + 2*len(SOULS)
for _, n in SOULS: nz += ((p0 + len(nb)) & 0xFFFF).to_bytes(2,'little'); nb += n + b'\x00'
blob = nt + nz + nb; assert CODE + len(code) <= NKART and NKART + len(blob) < 0xF1FFF0
o = at(NKART); assert all(b == 0xFF for b in r[o:o+len(blob)]); r[o:o+len(blob)] = blob
def jsl(a): return bytes([0x22]+L(a))
o = at(0x8FC1CC); r[o:o+4] = jsl(lab['dmg'])
r[o0:o0+4] = jsl(lab['bild'])
# Zielbestimmung: 8C:8D9B  LDA $8E0000,X ; STA $22 ; LDA $8E0001,X ; STA $23  (12 Byte) -> JSL ziel + 8x NOP
o = at(0x8C8D9B); assert bytes(r[o:o+12]) == bytes.fromhex('bf00008e8522bf01008e8523'), bytes(r[o:o+12]).hex()
r[o:o+12] = jsl(lab['ziel']) + b'\xEA'*8
# v146z13 (Max: schwarzer Balken = Ueberbleibsel der Meldung an der alten Stelle): Text NICHT mehr nach oben verschieben -
# der Box-Hintergrund blieb in Zeile 20 und war ohne Inhalt schwarz. Nur zum Testen: SOE_POS_OBEN=1.
for adr in ((0x8CC962, 0x8CC876) if OBEN else ()):   # Max (v146z14): unten lassen - oben erzeugt die geteilte Text-Ebene einen Balken   # zwei gleich gebaute Zeichenroutinen der Meldung
    o = at(adr); assert bytes(r[o:o+6]) == bytes.fromhex('a914008d6103'), (hex(adr), bytes(r[o:o+6]).hex())
    r[o:o+6] = jsl(lab['pos']) + b'\xEA\xEA'
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,"wb").write(d); print("Gegner-Info eingebaut, %d Bytes, dec %X bild %X ziel %X" % (len(code), lab["dec"], lab["bild"], lab["ziel"]))
