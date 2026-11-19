# DarkSoulCave PROTOTYP Raumfilter (Max: alle Karten als "Kopien nur fuer die Hoehle"): gleiche Grafik/Kollision/Tueren,
# OHNE NPCs, Dialoge, Zwischenszenen, Story-Skripte, MIT Monstern. Die Originale bleiben unveraendert.
# NICHT in work/bau.sh eingetragen. Aufruf: python3 soe_raumfilter.py ROM [--info] [--nur KK,KK,...]
#
# Ablauf (offline, beim ROM-Bau):
#  1. Wurzeln: Raumskript jeder Karte (93:801B + K*5) und die Skripte aller Lauf-/B-Ausloeser (Kartenkopf A0:FDE5,
#     Listen ab Kopf+13, Eintrag y1 x1 y2 x2 id, Skript = 93:8000 + [93:8000] + id).
#  2. Alle erreichbaren Befehle werden zerlegt (Sprungziele, lokale Unterskripte, 29/07/AF/B4-Zeiger). Zeigerziele, die von
#     >= GEMEINSAM Karten erreicht werden (z. B. 93:E200 = gemeinsamer Raum-Schluss), bleiben Original (nicht kopiert).
#  3. Die erreichbaren Bereiche werden als Bloecke (Layout 1:1) in die freien Baenke ab SKRIPT_BANK kopiert; relative
#     Spruenge bleiben gueltig, 3-Byte-Skriptzeiger in kopierte Bereiche werden umgerechnet.
#  4. In der Kopie: entfernte Befehle werden zu 4D (= nichts) bzw. ab 4 Byte zu "04 Sprung ueber den Rest".
#     Bedingungen 08/09 (vorwaerts) werden fest aufgeloest, wenn ein Zweig Szene/Dialog/NPC enthaelt und der andere nicht
#     (dann wird der szenenfreie Zweig genommen), sonst bei unterschiedlicher Gegnerzahl der Zweig mit mehr Gegnern;
#     sonst bleibt die Bedingung zur Laufzeit.
#  5. Tabellen: Raumskript-Ersatz (127 x 5 Byte, wie 93:801B) und Ausloeser-Ersatz (gleiches Layout wie die id-Tabelle,
#     FF = Original). Hooks: 8C:D2B1 (Raumskript-Zeiger) und 8C:D241 (id -> Skript), beide nur wenn AKT 30:7002 != 0
#     und Karte != 5E (Schachbrett behaelt alles).
import sys, os, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm import assemble

# ------------------------------------------------------------------ Einstellungen
CODE_BANK = 0xF5          # F5:0000 Hook-Code, F5:1000 Raumtabelle, F5:2000.. id-Tabelle (unteres Halb: nur Daten/Code)
SKRIPT_BANKEN = list(range(0xF5, 0x100))   # gefilterte Skripte nur in x:8000-FFFF (Skriptzeiger-Format), ~226 KB
AKT = 0x307002
AUSNAHME_KARTEN = {0x5E, 0x04}  # 5E Schachbrett (soe_knoten/funde brauchen das Original), 04 Hoehlendorf (AKT=0 dort)
GEMEINSAM = 3              # Zeigerziel ab so vielen Karten = gemeinsamer Code -> Original
STANDARD_SCHREIBER = 15    # Flag/Variable, die von so vielen Karten geschrieben wird = Spiel-Standard (49D/497/4B0...) -> behalten

# ------------------------------------------------------------------ ROM
def lade(pfad):
    d = bytearray(open(pfad, 'rb').read()); H = len(d) % 1024
    return d, H

def off(a):
    b = a >> 16
    return (a & 0x3FFFFF) if b >= 0xC0 or b & 0x40 else ((b & 0x3F) << 16) | (a & 0xFFFF)

def zeiger(p):           # 3-Byte-Skriptzeiger -> SNES-Adresse
    return ((0x93 + (p >> 15)) << 16) | 0x8000 | (p & 0x7FFF)

def zeiger_von(a):       # SNES-Adresse (Bank >= 93, Adresse >= 8000) -> 3-Byte-Skriptzeiger
    b = a >> 16; assert b >= 0x93 and a & 0x8000, hex(a)
    return ((b - 0x93) << 15) | (a & 0x7FFF)

# ------------------------------------------------------------------ Befehlsformate (aus work/dsc/filter/befehle.py, Laengen dort per Emulator geprueft)
# b Byte, w/2 Wort, t 3 Byte, p Skriptzeiger, r rel16, s rel8 rueckwaerts, E/O Ausdruck, L Liste, Z Ausdrucksliste bis 0
FMT = {
 0x00:'',0x04:'r',0x05:'s',0x07:'p',0x08:'Er',0x09:'Er',0x0A:'Etr',0x0B:'Etr',0x0C:'wE',0x0D:'wE',0x0E:'bE',
 0x10:'wE',0x11:'wE',0x12:'bE',0x14:'wE',0x15:'wE',0x16:'bE',0x17:'ww',0x18:'wE',0x19:'wE',0x1A:'bE',0x1B:'wwbb',
 0x1C:'wE',0x1D:'wE',0x1E:'bE',0x20:'bb',0x21:'bb',0x22:'bbw',0x23:'w',0x26:'',0x27:'',0x29:'p',0x2A:'O',0x2B:'O',
 0x2C:'b',0x2D:'b',0x2E:'E',0x30:'b',0x31:'b',0x32:'b',0x33:'b',0x38:'',0x39:'E',0x3A:'',0x3B:'E',0x3C:'wwbb',
 0x3D:'Ow',0x3F:'Eww',0x42:'O2',0x43:'OEE',0x44:'bbbbb',0x45:'bbbbb',0x46:'bbbbb',0x47:'bbbbb',0x48:'',0x49:'',
 0x4A:'',0x4B:'',0x4C:'b',0x4D:'',0x4E:'O',0x50:'bw',0x51:'w',0x52:'w',0x54:'b',0x55:'',0x58:'',0x59:'',0x5A:'',
 0x5B:'',0x5C:'EE',0x5D:'Ew',0x5E:'Ew',0x5F:'Ew',0x60:'E',0x61:'E',0x62:'bww',0x63:'',0x64:'E',0x65:'',0x66:'',
 0x68:'E',0x69:'',0x6A:'',0x6C:'Obb',0x6D:'OEE',0x6E:'Obb',0x6F:'OEE',0x70:'OO',0x71:'OO',0x73:'OEE',0x74:'O',
 0x75:'O',0x76:'O',0x77:'O',0x78:'OwE',0x79:'OwE',0x7A:'EE',0x7B:'EE',0x7C:'Et',0x7D:'Et',0x7E:'EEEE',0x7F:'w',
 0x80:'',0x81:'',0x82:'',0x83:'',0x84:'EE',0x85:'EE',0x86:'E',0x87:'E',0x88:'',0x89:'EE',0x8A:'E',0x8C:'w',
 0x8D:'b',0x8E:'EEr',0x8F:'EEr',0x90:'E',0x91:'E',0x92:'OE',0x93:'OE',0x94:'OE',0x95:'OE',0x96:'EE',
 0x97:'EEEEEEE',0x98:'E',0x99:'EEEEEE',0x9A:'E',0x9B:'O',0x9C:'O',0x9D:'OEE',0x9E:'OEEZ',0x9F:'',0xA0:'',0xA1:'',
 0xA2:'wwEE',0xA3:'b',0xA4:'w',0xA5:'s',0xA6:'r',0xA7:'b',0xA8:'w',0xA9:'OE',0xAA:'',0xAB:'',0xAC:'EEZ',
 0xAD:'wwbb',0xAE:'bbbb',0xAF:'Lp',0xB0:'Lb',0xB1:'Lw',0xB2:'Ls',0xB3:'Lr',0xB4:'Lp',0xB5:'EEEEEEEE',0xB6:'EEEE',
 0xB7:'E',0xB9:'OEE',0xBA:'bbb',0xBB:'OE',0xBC:'',0xBD:'',0xBE:'',0xBF:'',0xC0:'',0xC1:'',0xC2:'bbb',
}
ENDE = {0x00, 0x04, 0x05, 0x21, 0x22, 0xAB}
EX1 = {0x01, 0x02, 0x0F, 0x10, 0x11, 0x12, 0x13}
EX2 = set(range(0x03, 0x0F))

class Befehl:
    __slots__ = ('a', 'op', 'n', 'args', 'spr', 'ruf', 'zeig', 'konst', 'rel')
    def __repr__(s): return '%06X %02X n%d' % (s.a, s.op, s.n)

def ausdruck(rom, a):
    s = a; wert = None; n = 0
    while True:
        c = rom[off(a)]; a += 1; n += 1; k = c & 0x7F
        if k in EX1:
            v = rom[off(a)]; a += 1; wert = v if k == 0x02 and n == 1 else None
        elif k in EX2:
            v = rom[off(a)] | rom[off(a + 1)] << 8; a += 2; wert = v if k == 0x04 and n == 1 else None
        elif 0x30 <= k <= 0x3F: wert = (k & 0x0F) if n == 1 else None
        elif 0x60 <= k <= 0x6F: wert = (k & 0x0F) + 16 if n == 1 else None
        else: wert = None
        if c & 0x80 or k == 0x00: return a - s, wert
        if a - s > 250: return a - s, None

def befehl(rom, a):
    op = rom[off(a)]
    if op not in FMT: return None
    c = Befehl(); c.a = a; c.op = op; c.args = []; c.spr = []; c.ruf = []; c.zeig = []; c.konst = []; c.rel = None
    p = a + 1
    for f in FMT[op]:
        if f == 'b': c.args.append(rom[off(p)]); p += 1
        elif f in 'w2': c.args.append(rom[off(p)] | rom[off(p + 1)] << 8); p += 2
        elif f == 't': c.args.append(rom[off(p)] | rom[off(p + 1)] << 8 | rom[off(p + 2)] << 16); p += 3
        elif f == 'p':
            v = rom[off(p)] | rom[off(p + 1)] << 8 | rom[off(p + 2)] << 16
            c.zeig.append((p - a, zeiger(v))); c.args.append(zeiger(v)); p += 3
        elif f == 'r':
            v = rom[off(p)] | rom[off(p + 1)] << 8; p += 2
            if v >= 0x8000: v -= 0x10000
            if op in (0xA6, 0xB3): t = zeiger(zeiger_von(a) + v); c.ruf.append(t); c.rel = (p - 2 - a, 2)   # lokaler Aufruf: relativ im Zeigerraum (bankuebergreifend)
            else: t = ((p + v) & 0xFFFF) | (p & 0xFF0000); c.spr.append(t)
            c.args.append(t)
        elif f == 's':
            v = rom[off(p)]; p += 1
            if op in (0xA5, 0xB2): t = zeiger(zeiger_von(a) + v - 256); c.ruf.append(t); c.rel = (p - 1 - a, 1)
            else: t = ((p + (v - 256) - 2) & 0xFFFF) | (p & 0xFF0000); c.spr.append(t)
            c.args.append(t)
        elif f in 'EO':
            n, w = ausdruck(rom, p); c.args.append(bytes(rom[off(p):off(p) + n])); c.konst.append(w); p += n
        elif f == 'L':
            n = rom[off(p)]; p += 1
            for _ in range(n): m, w = ausdruck(rom, p); p += m
        elif f == 'Z':
            k = 0
            while True:
                m, w = ausdruck(rom, p); p += m; k += 1
                if w == 0 or k > 12: break
    c.n = p - a
    return c

# ------------------------------------------------------------------ Karten, Ausloeser
def w16(rom, a): return rom[off(a)] | rom[off(a + 1)] << 8
def w24(rom, a): return rom[off(a)] | rom[off(a + 1)] << 8 | rom[off(a + 2)] << 16

def raumskript(rom, k): return zeiger(w24(rom, 0x93801B + k * 5))
def id_skript(rom, i): return zeiger(w24(rom, 0x938000 + w16(rom, 0x938000) + i))

def ausloeser(rom, k):
    """[(art, id, (y1,x1,y2,x2))] aus Liste 1 (lauf) und Liste 2 (b)."""
    p = w24(rom, 0xA0FDE5 + 4 * k); y = 13; aus = []
    for art in ('lauf', 'b'):
        s = w16(rom, p + y); y += 2
        for i in range(s // 6):
            e = p + y + 6 * i
            aus.append((art, w16(rom, e + 4), tuple(rom[off(e + j)] for j in range(4))))
        y += s
    return aus

def global_adressen(rom):
    t = w16(rom, 0x938000); t2 = w16(rom, 0x938008); ad = set()
    for n in range(256):
        try: ad.add(zeiger(w24(rom, 0x938000 + t + t2 + n * 3)))
        except Exception: pass
    return ad

# ------------------------------------------------------------------ Einstufung
def vorlage_nr(rom, byteoff):
    v = w16(rom, 0x8EB55A + byteoff); d = v - 0xB678
    if v < 0xB678 or d % 74: return None
    return d // 74
OBJEKT_VORLAGEN = {23, 24, 25, 26, 27, 28, 54, 55, 60, 124, 135}   # Felsbrocken, Statue, Bruecke, Zepter ... (Kartenobjekte)
def spawn_art(rom, c):
    if c.op in (0xBA, 0xC2): nr = vorlage_nr(rom, c.args[0] * 2)
    else: nr = vorlage_nr(rom, c.args[0])
    if nr is None: return 'sonder', nr
    if nr in OBJEKT_VORLAGEN: return 'objekt', nr
    return ('gegner' if nr >= 51 else 'npc'), nr

# globale Skripte (a3 nn): weglassen = Textfenster/Dialog/Szene/Speichern; Rest (Blenden, Tuer-Vorskripte, Truhen, Raum-Schluss 36) bleibt
GLOBAL_WEG = set(range(0x02, 0x19)) | {0x32, 0x34, 0x3E, 0x40, 0x42, 0x47, 0x48, 0x49, 0x4D, 0x4E, 0x4F, 0x53, 0x54, 0x55,
                                        0x59, 0x5A, 0x5B, 0xD4, 0xFF}
DIALOG = {0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x50, 0x51, 0x52, 0x54, 0x55, 0x80, 0x81, 0x9F, 0xA0, 0xA1}
SPERRE = {0x2A, 0x2C, 0xBC, 0xBE, 0xC0, 0xAA, 0x98}
OBJEKT = {0x3D, 0x3F, 0x4E, 0x78, 0x79, 0x92, 0x93, 0x94, 0x95, 0x9B, 0x9C, 0x9E, 0xA9, 0xAC, 0xBB,
          0x42, 0x43, 0x6C, 0x6D, 0x6E, 0x6F, 0x73, 0x9D, 0xB9, 0x70, 0x71, 0x74, 0x75, 0x76, 0x77}
SZENE = {0x96, 0x5A, 0x64, 0x65, 0x68, 0x69, 0x63, 0x7F, 0x99, 0x9A, 0xAB, 0xB5}
SONDER_WEG = {0x88, 0x89, 0x8A, 0x8C, 0x7C, 0x7D, 0x7E, 0x84, 0x85, 0x7A, 0x7B}
SCHREIB_2258 = {0x0C: 'f', 0x10: 'b', 0x14: 'b', 0x17: 'w', 0x18: 'w', 0x1C: 'w', 0x1B: 'w'}

def schreibziel(c):
    """(art, offset) fuer Schreibbefehle in 7E:2258, sonst None"""
    if c.op not in SCHREIB_2258: return None
    w = c.args[0]
    return ('flag' if c.op == 0x0C else 'var', w)

def story_schreib(c, standard):
    z = schreibziel(c)
    if z is None: return False
    art, w = z
    if z in standard: return False
    if art == 'flag': return (w >> 3) < 0xA1
    if c.op == 0x1B: return w < 0xA1 or c.args[1] < 0xA1
    return w < 0xA1

def entscheide(rom, c, ctx, standard):
    """'k' behalten, 'w' weglassen (Szene), 'x' weglassen (still, kein Szenen-Zeichen)"""
    op = c.op
    if op in DIALOG or op in SPERRE or op in OBJEKT or op in SZENE: return 'w'
    if op == 0x8D: return 'w' if c.args[0] else 'k'
    if op in SONDER_WEG: return 'w' if op in (0x88, 0x89, 0x8A, 0x8C) else 'x'
    if op == 0x2E: return 'k' if c.konst[0] is not None else 'x'          # warten auf Objekt -> weg; Kartenteil/Kamera/Ausloeser bleibt
    if op in (0xA3, 0xB0): return 'w' if c.args[0] in GLOBAL_WEG else 'k'
    if op in (0xBA, 0xC2, 0x3C, 0xA2): return 'w' if spawn_art(rom, c)[0] == 'npc' else 'k'
    if op == 0x20: return 'x' if ctx == 'raum' else 'k'                   # Raumskript versetzt den Jungen nicht (Ankunft = Tuer-Hook)
    if story_schreib(c, standard): return 'x'
    return 'k'

def ist_gegner(rom, c):
    return c.op in (0xBA, 0xC2, 0x3C, 0xA2) and spawn_art(rom, c)[0] == 'gegner'

# ------------------------------------------------------------------ Analyse
class Analyse:
    def __init__(s, rom, karten=range(127)):
        s.rom = rom; s.karten = list(karten); s.cmd = {}
        s.globale = global_adressen(rom)
        s.wurzeln = []                   # (art, schluessel, adresse, karte)
        for k in s.karten:
            s.wurzeln.append(('raum', k, raumskript(rom, k), k))
            for art, i, rect in ausloeser(rom, k):
                if i >= 0xF000: continue
                s.wurzeln.append(('ausl', i, id_skript(rom, i), k))
        # Durchlauf 1: alle Zeigerziele mit Karten zaehlen
        s.ziel_karten = {}
        for art, key, a, k in s.wurzeln: s._lauf(a, k, None, folge_zeiger=True)
        s.gemeinsam = {z for z, ks in s.ziel_karten.items() if len(ks) >= GEMEINSAM} | s.globale
        # Durchlauf 2: erreichbare Befehle je Kontext (ohne gemeinsame Ziele)
        s.ctx = {}; s.kart = {}
        for art, key, a, k in s.wurzeln: s._lauf(a, k, 'raum' if art == 'raum' else 'ausl', folge_zeiger=False)
        # Standard-Schreiber (Flags/Variablen, die viele Karten schreiben)
        z = {}
        for a in s.ctx:
            c = s.cmd[a]; t = schreibziel(c)
            if t: z.setdefault(t, set()).update(s.kart[a])
        s.standard = {t for t, ks in z.items() if len(ks) >= STANDARD_SCHREIBER}

    def get(s, a):
        if a not in s.cmd:
            s.cmd[a] = befehl(s.rom, a)
        return s.cmd[a]

    def _lauf(s, start, karte, ctx, folge_zeiger):
        offen = [start]; gesehen = set()
        while offen:
            a = offen.pop()
            while a not in gesehen:
                gesehen.add(a)
                c = s.get(a)
                if c is None: break
                if ctx is not None:
                    s.ctx.setdefault(a, set()).add(ctx); s.kart.setdefault(a, set()).add(karte)
                offen.extend(c.spr); offen.extend(c.ruf)
                for _, z in c.zeig:
                    if z >> 16 >= 0xC0: continue                  # Skripte anderer Module (z. B. E5:xxxx) nicht anfassen
                    if folge_zeiger: s.ziel_karten.setdefault(z, set()).add(karte); offen.append(z)
                    elif z not in s.gemeinsam: offen.append(z)
                if c.op in ENDE: break
                a += c.n

# ------------------------------------------------------------------ Bloecke + Filter
def baue(rom, an, log=None):
    cmds = sorted(an.ctx)
    # Bereiche zusammenfassen (Luecke <= 32 Byte, gleiche Bank)
    ber = []
    for a in cmds:
        e = a + an.cmd[a].n
        if ber and a >> 16 == ber[-1][0] >> 16 and a <= ber[-1][1] + 32: ber[-1][1] = max(ber[-1][1], e)
        else: ber.append([a, e])
    # relative Spruenge zwischen Bloecken -> zusammenlegen
    def blk(a):
        i = bisect.bisect_right(starts, a) - 1
        return i if i >= 0 and ber[i][0] <= a < ber[i][1] else None
    geaendert = True
    while geaendert:
        geaendert = False; starts = [b[0] for b in ber]
        for a in cmds:
            c = an.cmd[a]
            for t in c.spr:
                i, j = blk(a), blk(t)
                if j is None: raise SystemExit('Sprungziel ausserhalb %06X -> %06X' % (a, t))
                if i != j:
                    lo, hi = min(i, j), max(i, j)
                    ber[lo] = [min(ber[lo][0], ber[hi][0]), max(ber[lo][1], ber[hi][1])]
                    del ber[lo + 1:hi + 1]; geaendert = True; break
            if geaendert: break
    # Entscheidungen je Befehl
    ent = {}
    for a in cmds:
        c = an.cmd[a]; ctx = 'raum' if 'raum' in an.ctx[a] and 'ausl' not in an.ctx[a] else 'ausl' if 'raum' not in an.ctx[a] else 'beide'
        ent[a] = entscheide(rom, c, 'raum' if ctx == 'raum' else 'ausl', an.standard)
    # Bewertung von Bereichen (Szene, Gegner), rekursiv ueber lokale/eigene Unterskripte
    memo = {}
    HELD = {b'\xd0', b'\xd1', b'\xd2', b'\xd3'}
    def szene(x):
        c = an.cmd[x]
        if ent[x] != 'w': return 0
        if c.op in OBJEKT and c.args and isinstance(c.args[0], bytes) and c.args[0] in HELD: return 0   # Held laeuft/dreht sich (Tuer-Nachlaufen)
        return 1
    def bewerte_ab(a, tiefe=0):
        """Faden ab a linear bis Ende: (szene, gegner)"""
        if a in memo: return memo[a]
        memo[a] = (0, 0)
        sz = gg = 0; gesehen = set(); x = a
        while x in an.cmd and x not in gesehen and x in ent:
            gesehen.add(x); c = an.cmd[x]
            sz += szene(x)
            if ist_gegner(rom, c): gg += 1
            for t in c.ruf + [z for _, z in c.zeig if z not in an.gemeinsam]:
                if tiefe < 4: s2, g2 = bewerte_ab(t, tiefe + 1); sz += s2; gg += g2
            if c.op in ENDE: break
            x += c.n
        memo[a] = (sz, gg); return memo[a]
    def bewerte(lo, hi):
        sz = gg = 0
        for a in cmds[bisect.bisect_left(cmds, lo):bisect.bisect_left(cmds, hi)]:
            if True:
                c = an.cmd[a]
                sz += szene(a)
                if ist_gegner(rom, c): gg += 1
                for t in c.ruf + [z for _, z in c.zeig if z not in an.gemeinsam]:
                    if not (lo <= t < hi): s2, g2 = bewerte_ab(t, 1); sz += s2; gg += g2
        return sz, gg
    # Bester Weg ab x bis Fadenende: (Szene-Befehle, Freigabe erreicht, Gegner); an Bedingungen der bessere Zweig
    sys.setrecursionlimit(100000)
    def frei(x):
        c = an.cmd[x]
        if ent[x] != 'k': return 0
        if c.op in (0xA3, 0xB0) and c.args[0] == 0x36: return 1                 # gemeinsamer Raum-Schluss (Bild + Steuerung frei)
        if c.op == 0x29 and c.args[0] in an.gemeinsam: return 1                  # 29 -> 93:E200 (ruft a3 36)
        if c.op in (0xBD, 0xC1): return 1
        return 0
    bmemo = {}
    def besser(p, q): return (p[0], -p[1], -p[2]) <= (q[0], -q[1], -q[2])
    def best(x):
        if x in bmemo: return bmemo[x]
        bmemo[x] = (0, 0, 0)
        sz = fr = gg = 0; start = x; gesehen = set(); erg = None
        while x in an.cmd and x in ent and x not in gesehen:
            gesehen.add(x); c = an.cmd[x]
            sz += szene(x); fr = max(fr, frei(x)); gg += 1 if ist_gegner(rom, c) else 0
            for t in c.ruf + [z for _, z in c.zeig if z not in an.gemeinsam]:
                s2, f2, g2 = best(t); sz += s2; fr = max(fr, f2); gg += g2
            if c.op in (0x08, 0x09) and c.spr[0] > x:
                p1 = best(x + c.n); p2 = best(c.spr[0]); q = p1 if besser(p1, p2) else p2
                erg = (sz + q[0], max(fr, q[1]), gg + q[2]); break
            if c.op == 0x04 and c.spr[0] > x: x = c.spr[0]; continue
            if c.op in ENDE: break
            x += c.n
        if erg is None: erg = (sz, fr, gg)
        bmemo[start] = erg; return erg
    bed = {}
    for a in cmds:
        c = an.cmd[a]
        if c.op not in (0x08, 0x09): continue
        T = c.spr[0]
        if T <= a: bed[a] = ('lauf', 'rueckwaerts'); continue
        p1 = best(a + c.n); p2 = best(T)
        if p1 == p2 or (p1[0] == p2[0] and p1[1] == p2[1] and p1[0] == 0): w = 'lauf'    # gleichwertig -> Laufzeit entscheidet
        elif besser(p1, p2): w = 'durch'
        else: w = 'springen'
        bed[a] = (w, (p1, p2))
    # Bloecke mit Aenderungen ("schmutzig") bestimmen; saubere Bloecke bleiben Original (spart Platz)
    starts = [b[0] for b in ber]
    veraendert = {a for a in cmds if ent[a] in 'wx'} | {a for a, (w, _) in bed.items() if w != 'lauf'}
    schmutz = {blk(a) for a in veraendert}
    while True:
        n0 = len(schmutz)
        for a in cmds:
            i = blk(a)
            if i in schmutz: continue
            c = an.cmd[a]
            if any(blk(z) in schmutz for _, z in c.zeig if z not in an.gemeinsam) or any(blk(t) in schmutz for t in c.ruf):
                schmutz.add(i)
        if len(schmutz) == n0: break
    while True:
        # Platz vergeben
        neu = {}; bi = 0; pc = (SKRIPT_BANKEN[0] << 16) | 0x8000
        for i in sorted(schmutz):
            s0, e0 = ber[i]; n = e0 - s0
            if (pc & 0xFFFF) + n > 0x10000 or pc & 0x8000 == 0:
                bi += 1; assert bi < len(SKRIPT_BANKEN), 'zu wenig Platz'; pc = (SKRIPT_BANKEN[bi] << 16) | 0x8000
            neu[i] = pc; pc += n
        def neu_adr(a):
            i = blk(a)
            return neu[i] + (a - ber[i][0]) if i in neu else None
        def adr(a): x = neu_adr(a); return a if x is None else x
        # lokale Aufrufe aus schmutzigen Bloecken muessen erreichbar bleiben
        mehr = set()
        for a in cmds:
            c = an.cmd[a]
            if c.rel is None or blk(a) not in schmutz: continue
            v = zeiger_von(adr(c.ruf[0])) - zeiger_von(adr(a))
            ok = (-0x8000 <= v < 0x8000) if c.rel[1] == 2 else (-256 <= v < 0)
            if not ok: mehr.add(blk(c.ruf[0]))
        if not mehr - schmutz: break
        schmutz |= mehr
    # Kopie
    kopie = {}
    for i in schmutz:
        s0, e0 = ber[i]; kopie[neu[i]] = bytearray(rom[off(s0):off(s0) + (e0 - s0)])
    def schreib(a, bs):
        i = blk(a); s0, e0 = ber[i]; assert i in schmutz and s0 <= a and a + len(bs) <= e0, hex(a)
        kopie[neu[i]][a - s0:a - s0 + len(bs)] = bytes(bs)
    # Zeiger umrechnen
    for a in cmds:
        if blk(a) not in schmutz: continue
        c = an.cmd[a]
        for po, z in c.zeig:
            nz = neu_adr(z)
            if nz is not None and z not in an.gemeinsam:
                p = zeiger_von(nz); schreib(a + po, [p & 0xFF, (p >> 8) & 0xFF, p >> 16])
    # lokale Aufrufe (A5/A6/B2/B3) neu berechnen (Ziel kann in einem anderen Block liegen)
    for a in cmds:
        c = an.cmd[a]
        if c.rel is None or blk(a) not in schmutz: continue
        ro, gr = c.rel; v = zeiger_von(adr(c.ruf[0])) - zeiger_von(adr(a))
        if gr == 2: schreib(a + ro, [v & 0xFF, (v >> 8) & 0xFF])
        else: schreib(a + ro, [v + 256])
    # Sprungziele (keine 04-Abkuerzung ueber Ziele hinweg)
    ziele = set()
    for a in cmds: ziele.update(an.cmd[a].spr); ziele.update(an.cmd[a].ruf)
    for a in an.gemeinsam: pass
    # Schreiben
    statistik = {'weg': 0, 'still': 0, 'springen': 0, 'durch': 0, 'lauf': 0}
    weg = [a for a in cmds if ent[a] in 'wx']
    for a in weg: statistik['weg' if ent[a] == 'w' else 'still'] += 1
    i = 0
    while i < len(weg):
        a = weg[i]; e = a + an.cmd[a].n; j = i + 1
        while j < len(weg) and weg[j] == e and weg[j] not in ziele: e += an.cmd[weg[j]].n; j += 1
        n = e - a
        if n >= 4:
            v = n - 3; schreib(a, [0x04, v & 0xFF, v >> 8] + [0x4D] * (n - 3))
        else:
            schreib(a, [0x4D] * n)
        i = j
    for a, (w, info) in bed.items():
        c = an.cmd[a]
        if w == 'springen':
            v = c.spr[0] - (a + 3); assert -0x8000 <= v < 0x8000
            schreib(a, [0x04, v & 0xFF, (v >> 8) & 0xFF] + [0x4D] * (c.n - 3)); statistik['springen'] += 1
        elif w == 'durch':
            if c.n >= 4: schreib(a, [0x04, (c.n - 3) & 0xFF, 0] + [0x4D] * (c.n - 3))
            else: schreib(a, [0x4D] * c.n)
            statistik['durch'] += 1
        else: statistik['lauf'] += 1
    return ber, neu, kopie, neu_adr, ent, bed, statistik, schmutz, blk

def gegner_im_fluss(rom, an, ent, bed, start):
    """Gegner-Spawns, die im gefilterten Skript (feste Zweige beachtet) erreichbar sind"""
    seen = set(); st_ = [start]; g = 0
    while st_:
        x = st_.pop()
        while x in an.cmd and x not in seen and x in ent:
            seen.add(x); c = an.cmd[x]
            if ent[x] == 'k' and ist_gegner(rom, c): g += 1
            b = bed.get(x)
            if b and b[0] == 'springen': x = c.spr[0]; continue
            if not (b and b[0] == 'durch'): st_ += c.spr
            st_ += c.ruf + [z for _, z in c.zeig if z not in an.gemeinsam]
            if c.op in ENDE: break
            x += c.n
    return g

# ------------------------------------------------------------------ Zusatzgegner (Karten ohne Gegner nach dem Filtern)
# Nach dem Anhaengen des Raumfadens (8C:D2C8 JSL 8C:D26B) wird bei AKT != 0 und Merker ZKT[Karte] ein zweiter Faden gestartet:
# Mini-Skript in 7E:E7C0 (wie v136 RSKIP, dort ungenutzt) mit "BA typ x y" an freien Zellen (Kollision 7F, Form 0, gleiche Ebene
# wie der Junge, >= 80 px weg), Anzahl 2 + Stockwerk/8 (max 6), zwei Arten aus ZTAB F1:8B00 (soe_vigor).
ZUSATZ = True
RSKR, ZTAB, FLOOR = 0x7EE7C0, 0xF18B00, 0x307004
TMP = 0x307660   # 7660 Typ1, 7662 Typ2, 7664 Zaehler, 7666 Versuche, 7668 cx, 766A cy, 766C H, 766E Ebene
def zusatz_code(ZKT):
    N8 = [0xEA] * 8
    return [
      'zg:', [0x22, 0x6B, 0xD2, 0x8C],                                             # Original: JSL 8C:D26B
      [0x08, 0xC2, 0x30, 0x48, 0xDA, 0x5A, 0x8B, 0xF4, 0x7E, 0x7E, 0xAB, 0xAB],
      [0xAF] + L(AKT) + [0x29, 0xFF, 0x00], ('bra8', 0xD0, 'zg_a'), ('jmp', 'zg_r'),
      'zg_a:', [0xAD, 0xDB, 0x0A, 0x29, 0x7F, 0x00, 0xAA, 0xBF] + L(ZKT) + [0x29, 0xFF, 0x00], ('bra8', 0xD0, 'zg_b'), ('jmp', 'zg_r'),
      'zg_b:', [0xAD, 0xEE, 0x08, 0x0A, 0x48, 0xAD, 0xAA, 0x0F, 0x8F, 0x04, 0x42, 0x00, 0x68, 0xE2, 0x20, 0x8F, 0x06, 0x42, 0x00, 0xC2, 0x20] + N8 +
               [0xAF, 0x14, 0x42, 0x00, 0x8F] + L(TMP + 12),
      ('jsr', 'zuf'), [0x29, 0x07, 0x00, 0x8F] + L(TMP), ('jsr', 'zuf'), [0x29, 0x07, 0x00, 0x8F] + L(TMP + 2),
      [0xAF] + L(FLOOR) + [0x29, 0xFF, 0x00, 0x4A, 0x4A, 0x4A, 0x1A, 0x1A, 0xC9, 0x07, 0x00], ('bra8', 0x90, 'zg_n'), [0xA9, 0x06, 0x00], 'zg_n:', [0x8F] + L(TMP + 4),
      [0xAD, 0xA3, 0x4E, 0x4A, 0x4A, 0x4A, 0x4A, 0x8F] + L(TMP + 8) + [0xAD, 0xA5, 0x4E, 0x4A, 0x4A, 0x4A, 0x4A, 0x8F] + L(TMP + 10), ('jsr', 'attr'), [0x29, 0x30, 0x00, 0x8F] + L(TMP + 14),
      [0xA0, 0x00, 0x00],
      'zg_g:', [0xA9, 40, 0x00, 0x8F] + L(TMP + 6),
      'zg_v:', [0xAF] + L(TMP + 6) + [0x3A, 0x8F] + L(TMP + 6), ('bra8', 0xD0, 'zg_v1'), ('jmp', 'zg_naechst'),
      'zg_v1:', ('jsr', 'zuf'), [0x8F, 0x04, 0x42, 0x00, 0xE2, 0x20, 0xAD, 0xEE, 0x08, 0x8F, 0x06, 0x42, 0x00, 0xC2, 0x20] + N8 + [0xAF, 0x16, 0x42, 0x00, 0x8F] + L(TMP + 8),
      ('jsr', 'zuf'), [0x8F, 0x04, 0x42, 0x00, 0xAF] + L(TMP + 12) + [0xE2, 0x20, 0x8F, 0x06, 0x42, 0x00, 0xC2, 0x20] + N8 + [0xAF, 0x16, 0x42, 0x00, 0x8F] + L(TMP + 10),
      [0xAF] + L(TMP + 8) + [0x0A, 0x0A, 0x0A, 0x0A, 0x38, 0xED, 0xA3, 0x4E], ('bra8', 0x10, 'zg_d1'), [0x49, 0xFF, 0xFF, 0x1A], 'zg_d1:', [0x48],
      [0xAF] + L(TMP + 10) + [0x0A, 0x0A, 0x0A, 0x0A, 0x38, 0xED, 0xA5, 0x4E], ('bra8', 0x10, 'zg_d2'), [0x49, 0xFF, 0xFF, 0x1A], 'zg_d2:', [0x18, 0x63, 0x01, 0xAA, 0x68, 0x8A],
      [0xC9, 80, 0x00], ('bra8', 0xB0, 'zg_weit'), ('jmp', 'zg_v'), 'zg_weit:',
      ('jsr', 'attr'), [0x48, 0x29, 0x0F, 0x00], ('bra8', 0xF0, 'zg_f1'), [0x68], ('jmp', 'zg_v'),
      'zg_f1:', [0xA3, 0x01, 0x29, 0x00, 0x01], ('bra8', 0xF0, 'zg_f2'), [0x68], ('jmp', 'zg_v'),
      'zg_f2:', [0x68, 0x29, 0x30, 0x00, 0xCF] + L(TMP + 14), ('bra8', 0xF0, 'zg_ok'), ('jmp', 'zg_v'),
      'zg_ok:', [0x98, 0x29, 0x04, 0x00], ('bra8', 0xF0, 'zg_t1'), [0xAF] + L(TMP + 2), ('bra8', 0x80, 'zg_t'), 'zg_t1:', [0xAF] + L(TMP), 'zg_t:',
      [0xAA, 0xE2, 0x20, 0xA9, 0xBA, 0x99] + w(RSKR & 0xFFFF) + [0xBF] + L(ZTAB) + [0x99] + w((RSKR + 1) & 0xFFFF),
      [0xAF] + L(TMP + 8) + [0x0A, 0x1A, 0x99] + w((RSKR + 2) & 0xFFFF) + [0xAF] + L(TMP + 10) + [0x0A, 0x1A, 0x99] + w((RSKR + 3) & 0xFFFF) + [0xC2, 0x20, 0xC8, 0xC8, 0xC8, 0xC8],
      'zg_naechst:', [0xAF] + L(TMP + 4) + [0x3A, 0x8F] + L(TMP + 4), ('bra8', 0xF0, 'zg_ende'), ('jmp', 'zg_g'),
      'zg_ende:', [0xE2, 0x20, 0xA9, 0x00, 0x99] + w(RSKR & 0xFFFF) + [0xC2, 0x20, 0xC0, 0x00, 0x00], ('bra8', 0xF0, 'zg_r'),
      # zweiten Faden starten (wie soe_hoehle 'bild' MSKR2): Zeiger 0 -> D2FD, dann PC = 7E:E7C0, +0B/+0D = 0, anhaengen
      [0x64, 0x26, 0x64, 0x28, 0x22, 0xFD, 0xD2, 0x8C],
      [0xA9] + w(RSKR & 0xFFFF) + [0x9F, 0x00, 0x00, 0x7E, 0xE2, 0x20, 0xA9, 0x7E, 0x9F, 0x02, 0x00, 0x7E, 0xC2, 0x20],
      [0xA9, 0x00, 0x00, 0x9F, 0x0B, 0x00, 0x7E, 0x9F, 0x0D, 0x00, 0x7E, 0x22, 0x6B, 0xD2, 0x8C],
      'zg_r:', [0xAB, 0x7A, 0xFA, 0x68, 0x28, 0x6B],
      'attr:', [0xDA, 0xAF] + L(TMP + 10) + [0x8F, 0x02, 0x42, 0x00, 0xAD, 0xEE, 0x08, 0xE2, 0x20, 0x8F, 0x03, 0x42, 0x00, 0xC2, 0x20, 0xEA, 0xEA, 0xEA, 0xEA,
                0xAF, 0x16, 0x42, 0x00, 0x18, 0x6F] + L(TMP + 8) + [0x0A, 0xAA, 0xBF, 0x00, 0x00, 0x7F, 0xAA, 0xBF, 0x04, 0x00, 0x7F, 0xFA, 0x60],
      'zuf:', [0x22, 0x9B, 0x85, 0x80, 0x4D, 0xA3, 0x4E, 0x4D, 0x00, 0x01, 0x29, 0xFF, 0x7F, 0x60],
    ]

# ------------------------------------------------------------------ Einbau
def L(a): return [a & 0xFF, (a >> 8) & 0xFF, a >> 16]
def w(v): return [v & 0xFF, (v >> 8) & 0xFF]

def einbau(pfad, info=False, nur=None):
    d, H = lade(pfad); r = memoryview(d)[H:]
    rom = bytes(r)
    karten = range(127)
    an = Analyse(rom, karten)
    ber, neu, kopie, neu_adr, ent, bed, st, schmutz, blk = baue(rom, an)
    groesse = sum(len(b) for b in kopie.values())
    # Tabellen
    RTAB = (CODE_BANK << 16) | 0x1000
    ITAB = (CODE_BANK << 16) | 0x2000
    rtab = bytearray(b'\xFF' * (127 * 5))
    nur_k = set(nur) if nur else None
    for art, key, a, k in an.wurzeln:
        if art != 'raum' or k in AUSNAHME_KARTEN or (nur_k is not None and k not in nur_k): continue
        na = neu_adr(a)
        if na is None: continue
        p = zeiger_von(na); rtab[k * 5:k * 5 + 3] = bytes(L(p)); rtab[k * 5 + 3:k * 5 + 5] = rom[off(0x93801B + k * 5 + 3):off(0x93801B + k * 5 + 5)]
    basis = w16(rom, 0x938000)
    ids = {}
    for art, key, a, k in an.wurzeln:
        if art != 'ausl': continue
        if nur_k is not None and k not in nur_k: continue
        if k in AUSNAHME_KARTEN: continue
        na = neu_adr(a)
        if na is not None: ids[key] = zeiger_von(na)
    imax = max(ids) + 3 if ids else 3
    itab = bytearray(b'\xFF' * (basis + imax))
    for i, p in ids.items(): itab[basis + i:basis + i + 3] = bytes(L(p))
    assert len(itab) <= 0xE000, len(itab)
    TMAX = len(itab)
    # Hook-Code
    CODE = CODE_BANK << 16
    t = [
      # 8C:D2B1-D2BC ersetzt (LDA $93801B,X ; STA $26 ; LDA $93801C,X ; STA $27), X = Karte*5
      'rs:', [0xBF, 0x1B, 0x80, 0x93, 0x85, 0x26, 0xBF, 0x1C, 0x80, 0x93, 0x85, 0x27],
      [0xAF] + L(AKT) + [0x29, 0xFF, 0x00], ('bra8', 0xF0, 'rs_r'),
      [0xBF] + L(RTAB + 2) + [0x29, 0xFF, 0x00, 0xC9, 0xFF, 0x00], ('bra8', 0xF0, 'rs_r'),
      [0xBF] + L(RTAB) + [0x85, 0x26, 0xBF] + L(RTAB + 1) + [0x85, 0x27],
      'rs_r:', [0x6B],
      # 8C:D241 (TXA ; CLC ; ADC $938000 ; TAX ; LDA $938000,X ; STA $26 ; LDA $938002,X ; AND #$FF ; STA $28) -> JML 8C:D257
      'id:', [0x8A, 0x18, 0x6F, 0x00, 0x80, 0x93, 0xAA, 0xBF, 0x00, 0x80, 0x93, 0x85, 0x26, 0xBF, 0x02, 0x80, 0x93, 0x29, 0xFF, 0x00, 0x85, 0x28],
      [0xAF] + L(AKT) + [0x29, 0xFF, 0x00], ('bra8', 0xF0, 'id_r'),
      [0xAF, 0xDB, 0x0A, 0x7E, 0x29, 0xFF, 0x00, 0xC9, 0x5E, 0x00], ('bra8', 0xF0, 'id_r'),
      [0xE0] + w(TMAX - 3), ('bra8', 0xB0, 'id_r'),
      [0xBF] + L(ITAB + 2) + [0x29, 0xFF, 0x00, 0xC9, 0xFF, 0x00], ('bra8', 0xF0, 'id_r'),
      [0x85, 0x28, 0xBF] + L(ITAB) + [0x85, 0x26],
      'id_r:', [0x5C, 0x57, 0xD2, 0x8C],
    ]
    ZKT = (CODE_BANK << 16) | 0x0F00
    zkt = bytearray(128); ohne = []
    for art, key, a, k in an.wurzeln:
        if art == 'raum' and k not in AUSNAHME_KARTEN and rtab[k * 5 + 2] != 0xFF and gegner_im_fluss(rom, an, ent, bed, a) == 0:
            zkt[k] = 1; ohne.append(k)
    if ZUSATZ: t += zusatz_code(ZKT)
    code, lab = assemble(CODE, t)
    assert len(code) <= 0x0F00
    if info:
        return an, ber, neu, kopie, ent, bed, st, groesse
    # schreiben (FF-Pruefung)
    def put(adr, bs):
        o = off(adr); assert all(b == 0xFF for b in r[o:o + len(bs)]), 'nicht frei: %06X' % adr; r[o:o + len(bs)] = bs
    put(CODE, code); put(RTAB, bytes(rtab)); put(ITAB, bytes(itab)); put(ZKT, bytes(zkt))
    if ZUSATZ:
        o = off(0x8CD2C8); assert bytes(r[o:o + 4]) == bytes([0x22, 0x6B, 0xD2, 0x8C]), bytes(r[o:o + 4]).hex()
        a = lab['zg']; r[o:o + 4] = bytes([0x22, a & 0xFF, (a >> 8) & 0xFF, a >> 16])
    for n0, bs in kopie.items(): put(n0, bytes(bs))
    o = off(0x8CD2B1); assert bytes(r[o:o + 12]) == bytes([0xBF, 0x1B, 0x80, 0x93, 0x85, 0x26, 0xBF, 0x1C, 0x80, 0x93, 0x85, 0x27]), bytes(r[o:o + 12]).hex()
    a = lab['rs']; r[o:o + 12] = bytes([0x22, a & 0xFF, (a >> 8) & 0xFF, a >> 16, 0x80, 0x06] + [0xEA] * 6)
    o = off(0x8CD241); assert bytes(r[o:o + 4]) == bytes([0x8A, 0x18, 0x6F, 0x00]), bytes(r[o:o + 4]).hex()
    a = lab['id']; r[o:o + 4] = bytes([0x5C, a & 0xFF, (a >> 8) & 0xFF, a >> 16])
    h = 0xFFC0
    for _ in range(2):
        s = sum(r) & 0xFFFF; r[h + 0x1E:h + 0x20] = s.to_bytes(2, 'little'); r[h + 0x1C:h + 0x1E] = (s ^ 0xFFFF).to_bytes(2, 'little')
    open(pfad, 'wb').write(d)
    print('Raumfilter eingebaut: %d Bloecke, %d Bytes Skripte, %d Ausloeser-ids, Code %d Bytes; %s' % (len(kopie), groesse, len(ids), len(code), st))
    print('Zusatzgegner (%d Karten): %s' % (len(ohne), ' '.join('%02X' % k for k in sorted(ohne))))

if __name__ == '__main__':
    nur = None
    for x in sys.argv[2:]:
        if x.startswith('--nur='): nur = [int(k, 16) for k in x[6:].split(',')]
    if '--info' in sys.argv:
        r = einbau(sys.argv[1], info=True, nur=nur)
        an, ber, neu, kopie, ent, bed, st, gr = r
        print('Bloecke', len(ber), 'Bytes', gr, st, 'gemeinsam', len(an.gemeinsam), 'standard', sorted(an.standard))
    else:
        einbau(sys.argv[1], nur=nur)
