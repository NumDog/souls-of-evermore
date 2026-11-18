# Grenzen raus (Max 18.11., v97): Level bis 999, KP bis 9999, Werte-/Erfahrungstabellen bis Level 1000+ (Bank F1),
# Leiste unten zeigt ab Max-KP 1000 nur die aktuellen KP (4 Stellen; Anteil am Balken).
#  Werte-Tabellen (Junge 8C:91BA.., Hund 8C:9376..) gehen nur bis Level 110 -> neu F1:0000 + i*0x800, ab 110 linear weiter.
#  Erfahrung: 3 Byte bis Level 99 (8C:8F62 Junge, 8C:908E Hund) -> neu 4 Byte F1:6000 / F1:7000, ab 99 gleich viel je Level (Level 999 = 99.990.000).
#  Schwelle naechstes Level: 7E:4F1D (Junge) / 4FCB (Hund), 4 Byte, Vergleich im Spiel schon 32 Bit.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF,(a>>8)&0xFF,a>>16]
def w16(a): return r[a] | r[a+1]<<8
def schreib(adr, daten):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(daten)]), hex(adr); r[o:o+len(daten)] = daten
def patch(adr, alt, neu):
    o = at(adr); assert bytes(r[o:o+len(alt)]) == bytes(alt), (hex(adr), bytes(r[o:o+len(alt)]).hex()); r[o:o+len(neu)] = bytes(neu)
MAXL = 1016
# ---- Werte-Tabellen
TAB = [0x91BA,0x9298,0x9376,0x9454,0x9532,0x9610,0x96EE,0x97CC,0x98AA,0x9988,0x9A66,0x9B44]
NEU = {}
for i,t in enumerate(TAB):
    alt = [w16(0x0C0000+t+2*k) for k in range(111)]
    steig = (alt[110]-alt[100]) / 10.0
    werte = alt + [round(alt[110] + (k-110)*steig) for k in range(111, MAXL)]
    werte = [min(v, 0x7FFF) for v in werte]
    neu = 0xF10000 + i*0x800; NEU[t] = neu
    schreib(neu, b''.join(v.to_bytes(2,'little') for v in werte))
# Zugriffe umleiten: LDA/SBC lang auf 8C:Tabelle(+Versatz) in 8F:8300-8700 (Junge/Hund) und F0:9300-9700 (Talismane)
n_um = 0
for start, ende in ((0x0F8300,0x0F8700), (0x309300,0x309700)):
    for o in range(start, ende):
        if r[o] in (0xBF,0xFF) and r[o+3] == 0x8C:
            a = r[o+1] | r[o+2]<<8
            kand = [t for t in TAB if t <= a < t + 0xDE + 16]
            if kand:
                t = max(kand)                    # naechstliegende Tabelle (Bereiche ueberlappen um den Talisman-Versatz)
                z = NEU[t] + (a - t); r[o+1:o+4] = bytes(L(z)); n_um += 1
assert n_um == 36, n_um          # 12 Junge/Hund + 24 Talisman-Stubs
# ---- Erfahrungstabellen (4 Byte, Eintrag L = Gesamt-Erfahrung fuer Level L)
def exptab(basis):
    alt = [r[0x0C0000+basis+3*k] | r[0x0C0000+basis+3*k+1]<<8 | r[0x0C0000+basis+3*k+2]<<16 for k in range(100)]
    # Statusseite zeigt hoechstens 8 Stellen -> Level 999 bei 99.990.000, ab 99 gleich viel je Level (~103.000)
    D = (99_990_000 - alt[99]) // 900
    werte = alt[:]
    for k in range(100, 1000): werte.append(alt[99] + (k-99)*D)
    werte.append(0x7FFFFFFF)                 # Level 1000: unerreichbar
    werte[0] = 0
    return werte
EXPJ, EXPH = 0xF16000, 0xF17000
for basis, ziel in ((0x8F62, EXPJ), (0x908E, EXPH)):
    schreib(ziel, b''.join(v.to_bytes(4,'little') for v in exptab(basis)))
CODE = 0xF18000
def lade(lv, tab, schw):   # Schwelle fuer Level+1 laden (4 Byte)
    return [0x08, 0xC2,0x30, 0xDA, 0xAF]+L(0x7E0000|lv)+[0x1A, 0x0A, 0x0A, 0xAA, 0xBF]+L(tab)+[0x8F]+L(0x7E0000|schw)+[0xBF]+L(tab+2)+[0x8F]+L(0x7E0000|(schw+2))+[0xFA, 0x28, 0x6B]   # 16 Bit erzwingen (Statusseite laeuft mit 8-Bit-X)
teile = ['j:', lade(0x0A50, EXPJ, 0x4F1D), 'h:', lade(0x0A9A, EXPH, 0x4FCB)]
# ---- Leiste unten (8F:917A: LDA $7E002A,X ; JSL 80:870C): Max-KP >= 1000 -> nur aktuelle KP, 4 Stellen rechtsbuendig
teile += ['hud:', [0xDA, 0xBF,0x60,0x00,0x7E, 0xAA, 0xBF,0x0F,0x00,0x8E, 0xFA, 0xC9,0xE8,0x03], ('bra8',0xB0,'gross'),
          [0xBF,0x2A,0x00,0x7E, 0x5C,0x0C,0x87,0x80],                                  # normal: JML 80:870C (RTL zurueck hinter unseren JSL)
          'gross:', [0xBF,0x2A,0x00,0x7E, 0x48, 0xA4,0x26, 0xA9,0xE9,0x2B]]
for k in range(0,14,2): teile += [[0x99,k,0x00]]                                        # 7 Felder leeren
teile += [[0xA2,0x08,0x00],
          'z:', [0x68, 0x8D,0x04,0x42, 0xE2,0x20, 0xA9,10, 0x8D,0x06,0x42, 0xC2,0x20, 0xEA,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA,
                 0xAD,0x14,0x42, 0x48, 0xAD,0x16,0x42, 0x18, 0x69,0xEC,0x2B, 0x48, 0x8A, 0x18, 0x65,0x26, 0xA8, 0x68, 0x99,0x00,0x00,
                 0xA3,0x01], ('bra8',0xF0,'z_e'), [0xCA,0xCA], ('bra8',0x10,'z'),
          'z_e:', [0x68,                                                                 # Quotient weg
                   0x68, 0xE2,0x20, 0x68, 0xC2,0x20,                                     # unsere Ruecksprungadresse (3 Byte) weg
                   0xFA, 0x5C,0xD8,0x91,0x8F]]                                           # PLX (Objekt) ; JML 8F:91D8 (Ende der Leiste)
code, lab = assemble(CODE, teile); schreib(CODE, code)
assert lab['j'] == 0xF18000 and lab['h'] == 0xF1801F, (hex(lab['j']), hex(lab['h']))   # fest in soe_belohnung
def jsl(x): return [0x22]+L(x)
patch(0x8F832D, bytes.fromhex('ad500a0a186d500aaabf668f8c8d1e4fbf658f8c8d1d4f'), jsl(lab['j'])+[0xEA]*19)
patch(0x8F8502, bytes.fromhex('ad9a0a0a186d9a0aaabf92908c8dcc4fbf91908c8dcb4f'), jsl(lab['h'])+[0xEA]*19)
patch(0xCDB422, bytes.fromhex('ad500a1a85120a186512aabf628f8c8f1d4f7ebf638f8c8f1e4f7e'), jsl(lab['j'])+[0xEA]*23)
patch(0xCDB43D, bytes.fromhex('ad9a0a1a85120a186512aabf8e908c8fcb4f7ebf8f908c8fcc4f7e'), jsl(lab['h'])+[0xEA]*23)
patch(0x8F917A, bytes.fromhex('bf2a007e220c8780'), jsl(lab['hud'])+[0xEA]*4)
# ---- Level-Grenze 99 -> 999
for a in (0x8F828D, 0x8F82CF, 0x8F8313, 0x8F84E8, 0xCDA2ED, 0xCDAB44):
    patch(a, [0xC9,0x63,0x00], [0xC9,0xE7,0x03])
# ---- KP-Grenze 999 -> 9999
for a in (0x8F83A6, 0x8F857B):
    patch(a, bytes.fromhex('c9e7033003a9e703'), [0xC9,0x0F,0x27, 0x30,0x03, 0xA9,0x0F,0x27])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Grenzen: Level 999, KP 9999, %d Tabellenzugriffe umgeleitet" % n_um)
