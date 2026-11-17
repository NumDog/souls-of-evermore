import sys
pfad=sys.argv[1]; d=bytearray(open(pfad,'rb').read()); r=memoryview(d)[512:]
def cks(rom): return (sum(rom[:0x200000])+2*sum(rom[0x200000:0x300000]))&0xFFFF
T={'BoyHP':0xC9532,'BoyDEF':0xC9610,'BoyATK':0xC96EE,'BoyMDEF':0xC97CC,'DogHP':0xC98AA,'DogDEF':0xC9988,'DogATK':0xC9A66,'DogMDEF':0xC9B44}
w=lambda p:int.from_bytes(r[p:p+2],'little')
assert w(0xC9532+2*33)==318 and w(0xC98AA+2*33)==324, "unerwartete Tabelle - schon gepatcht?"
for k,o in T.items():
    v=[w(o+2*j) for j in range(111)]
    neu=[0]+[min(v[1]+2*(v[i]-v[1]),0x7FFF) for i in range(1,111)]
    for i,x in enumerate(neu): r[o+2*i:o+2*i+2]=x.to_bytes(2,'little')
    print(f"{k:8} L1 {v[1]}->{neu[1]}  L35 {v[35]}->{neu[35]}  L99 {v[99]}->{neu[99]}")
h=0xFFC0
for _ in range(2):
    c=cks(r); r[h+0x1E:h+0x20]=c.to_bytes(2,'little'); r[h+0x1C:h+0x1E]=(c^0xFFFF).to_bytes(2,'little')
print("Pruefsumme %04X ok=%s"%(c,cks(r)==c))
open(pfad,'wb').write(d)
