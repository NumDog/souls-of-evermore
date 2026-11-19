# Eigene Karten (v146o, Max: Stadt): Raum-Pakete aus dem Raum-Editor (editor/raeume/*.json, Export editor/rom_export.py)
# ersetzen in der Souls Cave beim Laden das Layout ihrer Vorlage-Karte.
#  - Hook 90:9270 (Kartenaufbau fertig, Bild noch aus; Kette: vorher soe_funde/soe_zufallsraum): erst die alte Kette,
#    dann bei AKT (30:7002) und Karte = Vorlage: Zellen nach 7F:0000 (2*W*H Byte) und eigene Kombis hinter die Original-Kombis
#    (7F:Basis + 8*n). Gleiche Groesse wie die Vorlage -> Kartenmasse/Kameragrenzen bleiben gueltig.
#  - Grafik, Paletten, Raumskript, Tueren kommen weiter von der Vorlage-Karte.
# Daten in Bank F8.
import json, os, sys
sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
def w(v): return [v&0xFF, (v>>8)&0xFF]
HIER = os.path.dirname(os.path.abspath(__file__))
RAEUME = ['stadt1']                     # eigene Raeume (je Vorlage-Karte hoechstens einer, v1)
CODE, DATEN = 0xF8F000, 0xF80000
AKT = 0x307002
NGEGNER = 7                             # Gegner je eigenem Raum (Platzhalter-Larve BA 0E -> soe_vulgor_larven tauscht, gilt als fremd = stumm)
SKR = 0x7EE7C0                          # Gegner-Skript in WRAM (frueher RSKIP, das ist aus)
EKM, EKT, EKD = 0x7EEE7C, 0x7EEE7E, 0x7EEE80   # letzte Karte / Bilder seit Betreten / Gegner gesetzt

eintraege = []; blob = bytearray()
for name in RAEUME:
    raum = json.load(open(os.path.join(HIER, 'editor', 'raeume', name + '.json')))
    satz = json.load(open(os.path.join(HIER, 'editor', 'kachelsaetze', '%02X' % raum['vorlage_karte'], 'kachelsatz.json')))
    W, Hh, n0 = raum['W'], raum['H'], len(satz['kombis'])
    assert (W, Hh) == (satz['W'], satz['H']), "v1: nur gleiche Groesse wie die Vorlage"
    basis = 2 * W * Hh
    tm = open(os.path.join(HIER, 'work', 'eigene', name, 'tilemap_roh.bin'), 'rb').read()
    kr = open(os.path.join(HIER, 'work', 'eigene', name, 'kombis_ram.bin'), 'rb').read()
    assert len(tm) == basis and kr[:8 * n0] == b''.join(bytes(w(k[0]) + w(k[1]) + w(k[2]) + [0, 0]) for k in satz['kombis']), name
    eig = kr[8 * n0:]
    a_tm = DATEN + len(blob); blob += tm
    a_eg = DATEN + len(blob); blob += eig
    # Gegner-Orte: begehbare Zellen (Kategorie boden, keine eigenen Kombis), weit weg vom Start, verteilt
    kat = json.load(open(os.path.join(HIER, 'editor', 'kachelsaetze', '%02X' % raum['vorlage_karte'], 'kategorien.json')))
    KT = dict(kat.get('auto', {})); KT.update(kat.get('hand', {}))
    st = next(m for m in raum['markierungen'] if m['art'] == 'start')
    frei = [(x, y) for y in range(2, Hh - 2) for x in range(2, W - 2)
            if all(raum['zellen'][(y + j) * W + x + i] < n0 and KT.get(str(raum['zellen'][(y + j) * W + x + i])) == 'boden'
                   for i in (-1, 0, 1) for j in (-1, 0, 1)) and abs(x - st['x']) + abs(y - st['y']) >= 10]
    import random as _r; rr = _r.Random(raum['vorlage_karte']); orte = []
    while frei and len(orte) < NGEGNER:
        p = rr.choice(frei); orte.append(p); frei = [q for q in frei if abs(q[0] - p[0]) + abs(q[1] - p[1]) >= 5]
    # v146t: C2 statt BA - C2 setzt $08 = 8000 (feindlich); nur dann erlaubt das Spiel dem Jungen den Schlag (Staedte haben kein C2)
    skript = b''.join(bytes([0xC2, 0x0E, 2 * x + 1, 2 * y + 1]) for x, y in orte) + b'\x00'
    a_sk = DATEN + len(blob); blob += skript
    print('  %s: %d Gegner-Orte %s' % (name, len(orte), orte))
    eintraege.append((raum['vorlage_karte'], a_tm, len(tm), a_eg, len(eig), basis + 8 * n0, a_sk, len(skript)))
    assert basis + 8 * n0 + len(eig) < 0xA000
# v146u: Zusatz-Gegner per C2 fuer Original-Karten in der Cave (ohne Layout-Tausch). Grund: der Junge darf nur schlagen,
# wenn die Erscheinen-Liste (C2 -> 8F:DE42) einen Eintrag hat - verwandelte Menschen sind direkte Objekte (Nobilia 7B).
ZUSATZ = [(0x7B, [(10, 31)])]          # Karte, Zellen (16 px) fuer C2-Platzhalter-Larven (soe_vulgor_larven tauscht sie)
for k, orte in ZUSATZ:
    skript = b''.join(bytes([0xC2, 0x0E, 2 * x + 1, 2 * y + 1]) for x, y in orte) + b'\x00'
    a_sk = DATEN + len(blob); blob += skript
    eintraege.append((k, None, 0, None, 0, 0, a_sk, len(skript)))
assert len(blob) < 0xF000

t = ['ek:', [0x22], 'VORHER', [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B],
     [0xAF]+L(AKT)+[0x29,0xFF,0x00], ('bra8',0xD0,'ek_a'), ('jmp','ek_r'),
     'ek_a:', [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00]]
for i, (k, a_tm, n_tm, a_eg, n_eg, ziel, a_sk, n_sk) in enumerate(eintraege):
    if a_tm is None: continue
    t += [[0xC9, k, 0x00], ('bra8',0xD0,'ek_n%d' % i),
          [0xA2]+w(a_tm & 0xFFFF)+[0xA0,0x00,0x00, 0xA9]+w(n_tm - 1)+[0x54,0x7F,a_tm >> 16]]                 # MVN $7F,$F8: Zellen
    if n_eg:
        t += [[0xA2]+w(a_eg & 0xFFFF)+[0xA0]+w(ziel)+[0xA9]+w(n_eg - 1)+[0x54,0x7F,a_eg >> 16]]               # eigene Kombis
    t += [('jmp','ek_r'), 'ek_n%d:' % i]
t += ['ek_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B]]
# ---- jedes Bild (Kette F0:4000): eigene Karte -> nach 20 Bildern Gegner-Skript als Faden starten (einmal je Besuch)
o0 = at(0xF04000); assert r[o0] == 0x22; vorbild = list(r[o0+1:o0+4])
b = ['eb:', [0x22]+vorbild+[0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A, 0x8B],
     [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00, 0xCF]+L(EKM), ('bra8',0xF0,'eb_g'),
     [0x8F]+L(EKM)+[0xA9,0x00,0x00, 0x8F]+L(EKT)+[0x8F]+L(EKD)+[0x8F,0xB4,0x7F,0x30], ('jmp','eb_r'),   # + v146u Stadt-Verwandlungs-Zaehler
     'eb_g:', [0xAF]+L(AKT)+[0x29,0xFF,0x00], ('bra8',0xD0,'eb_a'), ('jmp','eb_r'),
     'eb_a:', [0xE2,0x20, 0xA9,0x00, 0x8F,0xBF,0x23,0x7E, 0xC2,0x20],
     # v146u: verwandelte Menschen sind nicht mehr ansprechbar (Objekt +68 Bit 0x40 loeschen bei Monster-Vorlagen C536..DF3A),
     # sonst sucht B ein Gespraech (8F:AB9E) statt zu schlagen
     [0xA2,0xE5,0x3D], 'eb_o:', [0xBF,0x60,0x00,0x7E, 0xC9,0x36,0xC5], ('bra8',0x90,'eb_on'), [0xC9,0x3B,0xDF], ('bra8',0xB0,'eb_on'),
     [0xBF,0x68,0x00,0x7E, 0x29,0xBF,0xFF, 0x9F,0x68,0x00,0x7E],
     'eb_on:', [0x8A, 0x18, 0x69,0x8E,0x00, 0xAA, 0xE0,0x89,0x4E], ('bra8',0x90,'eb_o'),   # v146u: Stadt-Waffensperre 7E:23BF in der Cave immer aus (8F:CE31: != 0 -> kein Schlag)
     [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00]]
for i, e in enumerate(eintraege):
    b += [[0xC9, e[0], 0x00], ('bra8',0xD0,'eb_s%d' % i), [0xE2,0x20, 0xA9,0x01, 0x8F,0x21,0x12,0x7E, 0xC2,0x20], 'eb_s%d:' % i]   # v146s: Stadt-Sperre aus (7E:1221 FF = kein Angriff)
b += [[0xAF]+L(EKD), ('bra8',0xF0,'eb_b'), ('jmp','eb_r'),
     'eb_b:', [0xAF]+L(EKT)+[0x1A, 0x8F]+L(EKT)+[0xC9,20,0x00], ('bra8',0xB0,'eb_c'), ('jmp','eb_r'),
     'eb_c:', [0xAF,0xDB,0x0A,0x7E, 0x29,0xFF,0x00]]
for i, (k, a_tm, n_tm, a_eg, n_eg, ziel, a_sk, n_sk) in enumerate(eintraege):
    b += [[0xC9, k, 0x00], ('bra8',0xD0,'eb_n%d' % i),
          [0xA2]+w(a_sk & 0xFFFF)+[0xA0]+w(SKR & 0xFFFF)+[0xA9]+w(n_sk - 1)+[0x54,0x7E,a_sk >> 16], ('jmp','eb_start'), 'eb_n%d:' % i]
b += [('jmp','eb_r'),
     'eb_start:', [0xF4,0x00,0x00, 0xAB, 0xAB],                                                     # DB = 0 fuer den Faden-Start
     [0xA9,0x01,0x00, 0x8F]+L(EKD),
     [0x64,0x26, 0x64,0x28, 0x22,0xFD,0xD2,0x8C],                                                 # Faden anlegen (wie soe_hoehle MSGP)
     [0xA9]+w(SKR & 0xFFFF)+[0x9F,0x00,0x00,0x7E, 0xE2,0x20, 0xA9,0x7E, 0x9F,0x02,0x00,0x7E, 0xC2,0x20],
     [0xA9,0x00,0x00, 0x9F,0x0B,0x00,0x7E, 0x9F,0x0D,0x00,0x7E],
     [0x8A, 0xA6,0x86, 0x9F,0x28,0x2F,0x7E, 0xE8,0xE8, 0xA9,0x00,0x00, 0x9F,0x28,0x2F,0x7E, 0x86,0x86],
     'eb_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B]]
t += b
o9 = at(0x909270); assert r[o9] == 0x22; vorher = list(r[o9+1:o9+4])
t = [x if x != 'VORHER' else vorher for x in t]
t[1] = [0x22] + vorher; del t[2]
code, lab = assemble(CODE, t)
for adr, c in ((DATEN, bytes(blob)), (CODE, code)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
r[o9:o9+4] = bytes([0x22]+L(lab['ek']))
r[o0:o0+4] = bytes([0x22]+L(lab['eb']))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Eigene Karten eingebaut:", ", ".join(RAEUME), "(%d Byte Daten)" % len(blob))
