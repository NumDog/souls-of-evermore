# Monster-Randomizer fuer Secret of Evermore (DE): jedes Monster bekommt zufaellige Staerke 50-170 %,
# HP/Angriff/Verteidigung/Magie-Abwehr einzeln gestreut; EXP und Geld wachsen mit der Staerke.
import sys,random
quelle,ziel,seed=sys.argv[1],sys.argv[2],int(sys.argv[3])
rnd=random.Random(seed); d=bytearray(open(quelle,'rb').read()); r=memoryview(d)[512:]
g=lambda p:int.from_bytes(r[p:p+2],'little')
def s(p,v,n=2): r[p:p+n]=max(0,min(int(round(v)),0x7FFF if n==2 else 0xFFFFFF)).to_bytes(n,'little')
for p in range(0xEC536,0xEDF84,74):
    staerke=rnd.uniform(0.5,1.7)
    f={o:staerke*rnd.uniform(0.8,1.25) for o in (0x0F,0x19,0x1B,0x1D)}
    for o,x in f.items(): s(p+o,g(p+o)*x)
    s(p+0x23,int.from_bytes(r[p+0x23:p+0x27],'little')*staerke,4)
    s(p+0x27,g(p+0x27)*staerke)
h=0xFFC0
def cks(x): return (sum(x[:0x200000])+2*sum(x[0x200000:0x300000]))&0xFFFF
for _ in range(2):
    c=cks(r); r[h+0x1E:h+0x20]=c.to_bytes(2,'little'); r[h+0x1C:h+0x1E]=(c^0xFFFF).to_bytes(2,'little')
open(ziel,'wb').write(d); print("Seed",seed,"->",ziel)
