# Titelbild: „SECRET“ im Logo wird zu „SOULS“ (Souls of Evermore). Die Logo-Grafik liegt komprimiert im ROM und wird im
# Vorspann (Bild ~437) vom Grafik-Lader 90:9350 Kachel fuer Kachel in den VRAM entpackt (JSL 8C:CC4F je Stueck, $2E = VRAM-Ziel).
# Hook auf diesen JSL (90:9360): nach jedem Stueck pruefen, ob unsere letzte Kachel schon geschrieben ist ($2E hinter ihr)
# UND im VRAM das Original-Logo steht (2 Woerter von Kachel 0x188 per $2139 lesen). Dann die 60 neuen 8x8-Kacheln
# (tools/titel_souls.bin: je 2 Byte Kachel-Nr + 32 Byte 4bpp) direkt in den VRAM schreiben. Danach passt die Signatur
# nicht mehr -> kein zweites Mal; beim naechsten Titel (Neustart) wieder.
import sys, json, os; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
hier = os.path.dirname(os.path.abspath(__file__))
DATA = open(os.path.join(hier,'tools','titel_souls.bin'),'rb').read()
J = json.load(open(os.path.join(hier,'tools','titel_souls.json')))
CODE, DAT = 0xF07000, 0xF07200
# ---- Zusatzzeile „REMAKE 2026“ (v85): eigene 8x16-Schrift in freie 16x16-Plaetze (BG2-Kacheln 0x3A0..), Karte Zeile 8.
import importlib.util
_sp = importlib.util.spec_from_file_location('schrift', os.path.join(hier,'tools','schrift_titel.py')); _sm = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_sm)
ZEILE, ZSPALTE, PLAETZE = "REMAKE 2026", 5, [0x3A0,0x3A2,0x3A4,0x3A6,0x3A8,0x3AA]
GOLD, SCHATTEN = 13, 3
breite = len(PLAETZE)*16
bild = [[0]*breite for _ in range(16)]
x0 = (breite - len(ZEILE)*8)//2
for i,ch in enumerate(ZEILE):
    g = _sm.GLYPHEN[ch]
    for y,row in enumerate(g):
        for x,c in enumerate(row):
            if c != ' ':
                X, Y = x0+i*8+x, 3+y
                bild[Y][X] = GOLD
                for dx,dy in ((1,1),(1,0),(0,1)):
                    if X+dx < breite and Y+dy < 16 and bild[Y+dy][X+dx] == 0: bild[Y+dy][X+dx] = SCHATTEN
def kachel(px, ox, oy):
    t = bytearray(32)
    for y in range(8):
        for x in range(8):
            v = px[oy+y][ox+x]; sh = 7-x
            for p in range(4):
                if v>>p & 1: t[(16 if p>=2 else 0)+2*y+(p&1)] |= 1<<sh
    return bytes(t)
ZUSATZ = b''; KARTE = []
for k,n in enumerate(PLAETZE):
    for sub,(dx,dy) in enumerate(((0,0),(8,0),(0,8),(8,8))):
        ZUSATZ += (n+[0,1,16,17][sub]).to_bytes(2,'little') + kachel(bild, k*16+dx, dy)
    KARTE.append((0x0400 + 8*32 + ZSPALTE + k, 0x0400 | n))      # BG2-Karte (Wortadresse), Palette 1
# (Portraet: nicht im Titel, Max moechte es am ENDE-Bildschirm)
DATA = DATA + ZUSATZ
KDAT = b''.join(a.to_bytes(2,'little') + v.to_bytes(2,'little') for a,v in KARTE)
KDAT = b''.join(a.to_bytes(2,'little') + v.to_bytes(2,'little') for a,v in KARTE)
TRIG = 0x2000 + (J['max']+1)*16                     # $2E ab hier: alle unsere Kacheln geschrieben
SIGA = 0x2000 + J['sigtile']*16
FLAG, TIM = 0x7EE320, 0x7EE322                                           # Titel aktiv (Merker), Bilder seit Logo-Upload
code, lab = assemble(CODE, [
  [0x08, 0xC2,0x20, 0x48, 0xAF,FLAG&0xFF,(FLAG>>8)&0xFF,FLAG>>16], ('bra8',0xF0,'t_weiter'),    # (A = Parameter des Entpackers -> sichern!)
  [0xAF,TIM&0xFF,(TIM>>8)&0xFF,TIM>>16, 0xC9,60,0x00], ('bra8',0x90,'t_weiter'),
  [0xA9,0x00,0x00, 0x8F,FLAG&0xFF,(FLAG>>8)&0xFF,FLAG>>16],
  't_weiter:', [0x68, 0x28],
  [0x22,0x4F,0xCC,0x8C],                                                 # Original: Stueck entpacken
  [0x08, 0xC2,0x30, 0x48, 0xDA, 0x5A],
  [0xA5,0x2E, 0xC9,TRIG&0xFF,TRIG>>8], ('bra8',0xB0,'t_trig'), ('jmp','aus'),
  't_trig:',
  [0xE2,0x20, 0xA9,0x80, 0x8F,0x15,0x21,0x00, 0xC2,0x20],
  [0xA9,SIGA&0xFF,SIGA>>8, 0x8F,0x16,0x21,0x00],
  [0xAF,0x39,0x21,0x00, 0xC9,J['sig1']&0xFF,J['sig1']>>8], ('bra8',0xD0,'aus_j1'),
  [0xA9,(SIGA+1)&0xFF,(SIGA+1)>>8, 0x8F,0x16,0x21,0x00],                  # Adresse neu setzen (Lesezaehler laeuft nicht zuverlaessig weiter)
  [0xAF,0x39,0x21,0x00, 0xC9,J['sig2']&0xFF,J['sig2']>>8], ('bra8',0xF0,'t_sig_ok'),
  'aus_j1:', ('jmp','aus'),
  't_sig_ok:',
  [0xA2,0x00,0x00],
  'k:', [0xBF,DAT&0xFF,(DAT>>8)&0xFF,DAT>>16, 0x0A,0x0A,0x0A,0x0A, 0x18, 0x69,0x00,0x20, 0x8F,0x16,0x21,0x00, 0xE8,0xE8, 0xA0,0x10,0x00],
  'w:', [0xBF,DAT&0xFF,(DAT>>8)&0xFF,DAT>>16, 0x8F,0x18,0x21,0x00, 0xE8,0xE8, 0x88], ('bra8',0xD0,'w'),
  [0xE0,len(DATA)&0xFF,len(DATA)>>8], ('bra8',0x90,'k'),
  [0xA2,0x00,0x00],                                                      # Karten-Eintraege (Adresse, Wert)
  'm:', [0xBF]+list(((DAT+len(DATA))&0xFFFF).to_bytes(2,'little'))+[DAT>>16, 0x8F,0x16,0x21,0x00, 0xE8,0xE8],
  [0xBF]+list(((DAT+len(DATA))&0xFFFF).to_bytes(2,'little'))+[DAT>>16, 0x8F,0x18,0x21,0x00, 0xE8,0xE8],
  [0xE0,len(KDAT)&0xFF,len(KDAT)>>8], ('bra8',0x90,'m'),
  [0xA9,0x01,0x00, 0x8F,FLAG&0xFF,(FLAG>>8)&0xFF,FLAG>>16, 0xA9,0x00,0x00, 0x8F,TIM&0xFF,(TIM>>8)&0xFF,TIM>>16],
  [0xA5,0x2E, 0x8F,0x16,0x21,0x00],                                     # VRAM-Adresse wie vorher
  'aus:', [0x7A, 0xFA, 0x68, 0x28, 0x6B],
])
# ---- Jedes Bild (NMI, nach der Sprite-DMA 80:830E): solange das SOULS-Logo im VRAM steht (Kachel 0x188 = neue Daten),
# die Karten-Eintraege fuer „REMAKE 2026“ + Portraet neu schreiben (das Spiel laedt die Kartenzeilen per DMA nach).
i188 = [i for i in range(0, len(DATA), 34) if int.from_bytes(DATA[i:i+2],'little') == J['sigtile']][0]
NEUSIG = int.from_bytes(DATA[i188+2:i188+4], 'little')
assert NEUSIG != J['sig1']
NMI = 0xF07100
KADR = DAT + len(DATA)
nmi, nlab = assemble(NMI, [
  [0x22,0x00,0x80,0xF0],                                                 # ENDE-Bildschirm (soe_ende_bild.py)
  [0xDA, 0x5A],
  [0xAF,FLAG&0xFF,(FLAG>>8)&0xFF,FLAG>>16], ('bra8',0xF0,'n_aus'),
  [0xAF,TIM&0xFF,(TIM>>8)&0xFF,TIM>>16, 0xC9,0x78,0x05], ('bra8',0xB0,'n_los'),     # erst nach ~1400 Bildern (Logo fertig, Copyright da)
  [0x1A, 0x8F,TIM&0xFF,(TIM>>8)&0xFF,TIM>>16], ('bra8',0x80,'n_aus'),
  'n_los:', [0xE2,0x20, 0xA9,0x80, 0x8F,0x15,0x21,0x00, 0xC2,0x20],
  [0xA2,0x00,0x00],
  'n_m:', [0xBF]+list((KADR&0xFFFF).to_bytes(2,'little'))+[KADR>>16, 0x8F,0x16,0x21,0x00, 0xE8,0xE8],
  [0xBF]+list((KADR&0xFFFF).to_bytes(2,'little'))+[KADR>>16, 0x8F,0x18,0x21,0x00, 0xE8,0xE8],
  [0xE0,len(KDAT)&0xFF,len(KDAT)>>8], ('bra8',0x90,'n_m'),
  'n_aus:', [0x7A, 0xFA, 0xAD,0x0A,0x01, 0x8D,0x09,0x42, 0x6B],          # Original: LDA $010A ; STA $4209
])
assert CODE + len(code) <= NMI and NMI + len(nmi) <= DAT, (hex(CODE+len(code)), hex(NMI+len(nmi)))
o = at(NMI); assert all(b == 0xFF for b in r[o:o+len(nmi)]); r[o:o+len(nmi)] = nmi
o = at(0x80830E); assert bytes(r[o:o+6]) == bytes([0xAD,0x0A,0x01,0x8D,0x09,0x42]), bytes(r[o:o+6]).hex()
r[o:o+6] = bytes([0x22, NMI&0xFF, (NMI>>8)&0xFF, NMI>>16, 0xEA, 0xEA])
assert CODE + len(code) <= DAT and DAT + len(DATA) + len(KDAT) <= 0xF08000
for adr, c in ((CODE, code), (DAT, DATA + KDAT)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
o = at(0x909360); assert bytes(r[o:o+4]) == bytes([0x22,0x4F,0xCC,0x8C]), bytes(r[o:o+4]).hex()
r[o:o+4] = bytes([0x22, CODE&0xFF, (CODE>>8)&0xFF, CODE>>16])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Titel-Logo SOULS eingebaut, %d Kacheln" % (len(DATA)//34))
