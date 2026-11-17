import sys,re
rom=open(sys.argv[1],'rb').read()[512:]
st=open(sys.argv[2],'rb').read()
i=st.find(b'RAM:'); n=int(st[i+4:i+10]); ram=st[i+11:i+11+n]
w=lambda a,s=2:int.from_bytes(ram[a:a+s],'little')
lv=w(0x0A50); print("Boy Level",lv,"MaxHP",w(0x0A35),"ATK",w(0x0A3F),"DEF",w(0x0A41),"MDEF",w(0x0A43),"Evade",w(0x0A45),"Hit",w(0x0A47),"EXP",w(0x0A49,4))
print("Dog Level",w(0x0A9A),"MaxHP",w(0x0A7F),"ATK",w(0x0A89))
print("Geld T/J/G/C",[w(a,3) for a in (0xAC6,0xAC9,0xACC,0xACF)])
print("Waffen-Bits %02X %02X"%(ram[0x22DA],ram[0x22DB]),"Formel-Bits",ram[0x2258:0x225E].hex())
print("Name",ram[0x2210:0x2220])
T={'BoyHP':0xC919D,'BoyDEF':0xC927B,'BoyATK':0xC9359,'BoyMDEF':0xC9437,'BoyEva':0xC8E25,'BoyHit':0xC8F03,'DogHP':0xC9515,'DogATK':0xC96D1}
for k,o in T.items():
    v=[int.from_bytes(rom[o+2*j:o+2*j+2],'little') for j in range(111)]
    print(k, v[:6],"...",v[lv-1:lv+2],"...",v[97:101])
