# Texte der deutschen ROM lesen (Text-ID -> Zeiger in 92:8000+ID, Bit15 des 2. Worts = komprimiert).
# Entpacker nachgebaut von 8C:D147: Nibble-Strom, Woerterbuch 92:A41E[letztes_Zeichen*14 + n].
import sys
def lade(pfad):
    d = open(pfad,'rb').read(); return d[len(d)%1024:]
def zeiger(d, i):
    o = 0x128000 + i
    w1 = int.from_bytes(d[o:o+2],'little'); w2 = int.from_bytes(d[o+1:o+3],'little')
    bank = ((w2>>8)&0x7F) + 0xC0
    return bool(w2 & 0x8000), ((bank&0x3F)<<16) | (w1&0x7FFF)
def entpacke(d, off):
    TAB = 0x12A41E
    p = off; out = []; last = 0; zahl = 0; cur = 0
    def tab(x): return d[TAB + x]
    # Start: wie D174
    zahl = 1; cur = d[p]; nib = cur & 0x0F
    while True:
        if nib == 0:
            if zahl:
                c = ((d[p] >> 4) | (d[p+1] << 4)) & 0xFF
                out.append(c); last = c; p += 1; cur = d[p]
            else:
                p += 1; c = d[p]
                if c == 0: break
                out.append(c); last = c
        elif nib >= 0x0E:
            n = nib - 0x0E; stop = False
            while n >= 0:
                c = tab(last*14)
                if c == 0: stop = True; break
                out.append(c); last = c; n -= 1
            if stop: break
        else:
            c = tab(last*14 + nib)
            if c == 0: break
            out.append(c); last = c
        # D160
        if zahl:
            zahl -= 1; nib = cur >> 4
        else:
            p += 1; zahl = 1; cur = d[p]; nib = cur & 0x0F
    return bytes(out)
def text(d, i):
    komp, off = zeiger(d, i)
    return entpacke(d, off) if komp else d[off:d.index(b'\0', off)]
if __name__ == '__main__':
    d = lade(sys.argv[1])
    for a in sys.argv[2:]:
        t = text(d, int(a,16)); print(a, t.hex(' '), '|', t.decode('latin1','replace'))
