import sys
pfad=sys.argv[1]; schreiben = len(sys.argv)>2 and sys.argv[2]=="schreiben"
d=bytearray(open(pfad,'rb').read()); H=512; r=memoryview(d)[H:]
def cks(rom):
    a=sum(rom[:0x200000]); b=sum(rom[0x200000:0x300000])
    return (a+2*b)&0xFFFF
hdr=0xFFC0
print("Header-Pruefsumme %04X / Komplement %04X"%(int.from_bytes(r[hdr+0x1E:hdr+0x20],'little'),int.from_bytes(r[hdr+0x1C:hdr+0x1E],'little')))
print("berechnet         %04X"%cks(r))
START,END,SZ=0xEC536,0xEDF84,74
n=0
for p in range(START,END,SZ):
    hp=int.from_bytes(r[p+0x0F:p+0x11],'little'); at=int.from_bytes(r[p+0x19:p+0x1B],'little')
    nhp=min(hp*2,0x7FFF); nat=min(at*2,0x7FFF)
    if not schreiben: print(hex(p),"HP",hp,"->",nhp,"ATK",at,"->",nat)
    r[p+0x0F:p+0x11]=nhp.to_bytes(2,'little'); r[p+0x19:p+0x1B]=nat.to_bytes(2,'little'); n+=1
c=cks(r)  # header bytes are part of sum; set checksum+complement (sum of these 4 bytes is constant)
r[hdr+0x1E:hdr+0x20]=c.to_bytes(2,'little'); r[hdr+0x1C:hdr+0x1E]=(c^0xFFFF).to_bytes(2,'little')
c2=cks(r); r[hdr+0x1E:hdr+0x20]=c2.to_bytes(2,'little'); r[hdr+0x1C:hdr+0x1E]=(c2^0xFFFF).to_bytes(2,'little')
print(n,"Eintraege, neue Pruefsumme %04X, nachgerechnet %04X"%(c2,cks(r)))
if schreiben: open(pfad,'wb').write(d); print("geschrieben")
