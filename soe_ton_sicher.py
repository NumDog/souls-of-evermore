# Ton-Sicherheitsnetz: Das Spiel wartet an 10 Stellen endlos auf eine Antwort des Soundchips (CMP $2140/$2142 ; BNE *).
# Ist der Soundchip abgestuerzt (z. B. durch einen fremden Gegner), haengt das Spiel. Jetzt: Warten mit Zeitlimit.
# Laeuft das Limit ab, wird der Merker $7F:FFF0 gesetzt ("Ton tot") -> danach nur noch ganz kurz warten (Spiel laeuft stumm weiter).
# Antwortet der Soundchip wieder (z. B. nach Reset), wird der Merker geloescht.
# Die beiden Start-Warteschleifen des Hochladens (Wert $BBAA) warten immer lang, damit ein alter Merker sicher geloescht wird.
import sys; sys.path.insert(0, __file__.rsplit('/',1)[0]); from asm import assemble
pfad = sys.argv[1]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
def at(x): return x & 0x3FFFFF if (x>>16) >= 0xC0 else (((x>>16)&0x3F)<<16)|(x&0xFFFF)
MERKER = (0xF0,0xFF,0x7F)          # $7F:FFF0 (in allen 40 Spielstaenden unbenutzt)
LANG, KURZ = 0x8000, 0x0020        # ~0,1 s / ~0,1 ms
BASIS = 0xF03600
def routine(adr, port, immer_lang, nachziehen=False):
    # Stand v88 (0,1 s), v91: die Befehls-Quittung (8C:8532, nachziehen) setzt bei Zeitablauf NICHT „Ton tot“, sondern
    # uebernimmt wie das Original (8C:84E9) die Nummer des Soundchips ($2142 -> A -> $9F). v89/v90 (1 s + PHY) liess
    # in Mesen 4 von 10 Starts den Soundchip haengen -> zurueck auf v88-Schleife.
    teile = [[0x08, 0xC2,0x10, 0xDA]]                              # PHP ; REP #$10 ; PHX
    if immer_lang:
        teile += [[0xA2, LANG&0xFF, LANG>>8]]
    else:
        teile += [[0x48, 0xAF,*MERKER], ('bra8',0xF0,'normal'), [0x68, 0xA2,KURZ&0xFF,KURZ>>8], ('bra8',0x80,'schleife'),
                  'normal:', [0x68, 0xA2, LANG&0xFF, LANG>>8]]
    teile += ['schleife:', [0xCF,port&0xFF,port>>8,0x00], ('bra8',0xF0,'ok'), [0xCA], ('bra8',0xD0,'schleife')]
    if nachziehen:
        teile += [[0xE2,0x20, 0xAF,0x42,0x21,0x00], ('bra8',0x80,'fertig')]
    else:
        teile += [[0xE2,0x20, 0x48, 0xA9,0x01, 0x8F,*MERKER, 0x68], ('bra8',0x80,'fertig')]
    teile += ['ok:', [0xE2,0x20, 0x48, 0xA9,0x00, 0x8F,*MERKER, 0x68],
              'fertig:', [0xFA, 0x28, 0x6B]]                                               # PLX ; PLP ; RTL
    return assemble(adr, teile)[0]
W40  = BASIS
c40  = routine(W40, 0x2140, False)
W40L = W40 + len(c40);  c40l = routine(W40L, 0x2140, True)
W42  = W40L + len(c40l); c42 = routine(W42, 0x2142, False, nachziehen=True)
ende = W42 + len(c42); assert ende <= 0xF03700
for adr,c in ((W40,c40),(W40L,c40l),(W42,c42)):
    o = at(adr); assert all(b == 0xFF for b in r[o:o+len(c)]), hex(adr); r[o:o+len(c)] = c
STELLEN = {0x8C837F:W40L, 0x8C83EC:W40, 0x8C840C:W40, 0x8C8428:W40L, 0x8C8440:W40,
           0x8C8451:W40, 0x8C847F:W40, 0x8C84B8:W40, 0x8C84C5:W40, 0x8C8532:W42}
for site, ziel in STELLEN.items():
    o = at(site); port = 0x42 if ziel == W42 else 0x40
    assert bytes(r[o:o+5]) == bytes([0xCD,port,0x21,0xD0,0xFB]), (hex(site), bytes(r[o:o+5]).hex())
    r[o:o+5] = bytes([0x22, ziel&0xFF, (ziel>>8)&0xFF, ziel>>16, 0xEA])
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d); print("Ton-Sicherheitsnetz eingebaut: %d Stellen, %d Bytes"%(len(STELLEN), ende-BASIS))
