# SRAM-Grundinitialisierung (v146z17, Tester: ohne Spielstand startet "Neues Spiel" sofort; Mesen: frischer SRAM hat
# Zufallswerte -> Cave-Merker AKT gesetzt, "Untergeschoss 124" im Intro).
# Jedes Bild (Kette F0:4000, vorne): fehlt die Kennung 30:7F84 = "SO", werden einmal die Mod-Merker geloescht:
#   30:7000-70FF (Cave), 30:7E70-7E8F (Haendler/Sperren), 30:7EA4-7EFF (Funde, Spruch, Blutfleck, Warp),
#   30:7F80-7FFF (Vulgor gold, Zaehler, Blutfleck-Zustand). Spielstaende (6000-6CFF, 7700-77FF) und Einstellungen
#   (7E90-7EA3) bleiben. Danach Kennung setzen.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
def L(a): return [a&0xFF, (a>>8)&0xFF, a>>16]
CODE, KENN, WERT = 0xF8FB80, 0x307F84, 0x4F53
BEREICHE = [(0x7000, 0x7100), (0x7E70, 0x7E90), (0x7EA4, 0x7F00), (0x7F80, 0x8000)]
o0 = at(0xF04000); assert r[o0] == 0x22; vorbild = list(r[o0+1:o0+4])
teile = ['si:', [0x08, 0xC2,0x30, 0x48, 0xDA],   # erst pruefen, dann die bisherige Kette (sonst ein Bild mit Zufallswerten)
         [0xAF]+L(KENN)+[0xC9]+[WERT&0xFF, WERT>>8], ('bra8',0xD0,'si_pr'), ('jmp','si_r'),
         # v146z20 (Max: alte Cave-Spielstaende wurden 'echt'): nur loeschen, wenn die Cave-Werte Muell sind (AKT nicht 0/1 oder
         # Stockwerk > 99) - sonst nur die Kennung setzen (alte Spielstaende ohne Kennung behalten ihre Cave-Merker)
         'si_pr:', [0xAF,0x02,0x70,0x30, 0x29,0xFF,0x00, 0xC9,0x02,0x00], ('bra8',0xB0,'si_los'),
         [0xAF,0x04,0x70,0x30, 0x29,0xFF,0x00, 0xC9,100,0x00], ('bra8',0xB0,'si_los'), ('jmp','si_k'), 'si_los:']
for i,(a,b) in enumerate(BEREICHE):
    teile += [[0xA2]+[a&0xFF, a>>8], 'l%d:' % i, [0xA9,0x00,0x00, 0x9F,0x00,0x00,0x30, 0xE8,0xE8, 0xE0]+[b&0xFF, b>>8], ('bra8',0xD0,'l%d' % i)]
teile += ['si_k:', [0xA9]+[WERT&0xFF, WERT>>8]+[0x8F]+L(KENN), 'si_r:', [0xFA, 0x68, 0x28, 0x22]+vorbild+[0x6B]]
code, lab = assemble(CODE, teile)
o = at(CODE); assert all(b == 0xFF for b in r[o:o+len(code)]), "Platz belegt"; r[o:o+len(code)] = code
r[o0:o0+4] = bytes([0x22]+L(lab['si']))
h = 0xFFC0
for _ in range(2):
    s = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = s.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (s^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("SRAM-Grundinitialisierung eingebaut, %d Bytes" % len(code))
