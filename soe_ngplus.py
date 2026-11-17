# New Game+: uebertraegt Werte, Waffen, Formeln und Items aus einem spaeten Spielstand (quelle)
# in einen Spielstand vom Neustart (basis). Story-Flags bleiben vom Neustart.
import sys
basis,quelle,rom_alt,rom_neu,ziel=sys.argv[1:6]
def ram_of(b):
    i=b.find(b'RAM:131072:'); assert i>0; return i+11
B=bytearray(open(basis,'rb').read()); Q=open(quelle,'rb').read()
bo,qo=ram_of(B),ram_of(Q)
rb=memoryview(B)[bo:bo+131072]; rq=Q[qo:qo+131072]
def kopie(a,e): rb[a:e+1]=rq[a:e+1]
w=lambda m,a,s=2:int.from_bytes(m[a:a+s],'little')
def setw(a,v,s=2): rb[a:a+s]=int(v).to_bytes(s,'little')
vor=(w(rb,0x0A50),w(rb,0x0A35))
kopie(0x0A35,0x0A51)   # Junge: Werte, EXP, Level
kopie(0x0A7F,0x0A9B)   # Hund: Werte, EXP, Level
talons=bytes(rb[0x0AC6:0x0AC9]); kopie(0x0AC6,0x0AD1)   # Geld (alle 4 Waehrungen)
if w(rb,0x0AC6,3)==0: rb[0x0AC6:0x0AC9]=talons
kopie(0x0ADD,0x0AF7)   # Waffen-Level
kopie(0x0B07,0x0B07)   # Hund-Angriffslevel
rb[0x22DA]=rq[0x22DA]&~0x40&0xFF; rb[0x22DB]=rq[0x22DB]&0x3F&~0x04   # Waffen (ohne Horace; ohne Bronze-Axt + Bronze-Speer = Story)
kopie(0x2258,0x225B); rb[0x225C]=rq[0x225C]&0x7F     # Alchemie-Formeln (ohne Horace/Begleiter-Bits)
rb[0x225A]&=~0x20&0xFF; rb[0x225B]&=~0x10&0xFF       # ohne Telekinese (Levitate) + Enthueller (Revealer) = Story
kopie(0x2250,0x2256); rb[0x2256]&=0x7F               # Waffen-+1-Zaehler
rb[0x2257]=min(rq[0x2257]+1,255)                    # Zyklus +1
kopie(0x2F52,0x2FDD)   # Alchemie-Level
kopie(0x22FF,0x2347)   # Zutaten, Items, Ruestungen, Bazooka-Munition
rb[0x2304]=0           # kein Matschpfeffer (Story)
rb[0x2262]=rq[0x2262]; rb[0x2263]=(rb[0x2263]&0xF8)|(rq[0x2263]&0x07)  # Talismane
kopie(0x4F1D,0x4F20)   # EXP bis naechstes Level
# Werte auf die neuen (verdoppelten) Level-Tabellen umrechnen, Ausruestungs-Bonus bleibt
A=open(rom_alt,'rb').read()[512:]; N=open(rom_neu,'rb').read()[512:]
tab=lambda r,o,L:int.from_bytes(r[o+2*L:o+2*L+2],'little')
lb,lh=w(rb,0x0A50),w(rb,0x0A9A)
for ram,o,L in [(0x0A35,0xC9532,lb),(0x0A41,0xC9610,lb),(0x0A3F,0xC96EE,lb),(0x0A43,0xC97CC,lb),
                (0x0A7F,0xC98AA,lh),(0x0A8B,0xC9988,lh),(0x0A89,0xC9A66,lh),(0x0A8D,0xC9B44,lh)]:
    setw(ram, w(rb,ram)-tab(A,o,L)+tab(N,o,L))
setw(0x4EB3,w(rb,0x0A35)); setw(0x4F61,w(rb,0x0A7F))  # volle HP
open(ziel,'wb').write(B)
print("Basis Level/HP",vor,"-> Junge L",lb,"HP",w(rb,0x0A35),"ATK",w(rb,0x0A3F),"DEF",w(rb,0x0A41),"| Hund L",lh,"HP",w(rb,0x0A7F),"ATK",w(rb,0x0A89))
print("Waffen %02X %02X Formeln %s Geld %s"%(rb[0x22DA],rb[0x22DB],bytes(rb[0x2258:0x225E]).hex(),[w(rb,a,3) for a in (0xAC6,0xAC9,0xACC,0xACF)]))
