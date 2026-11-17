# Fundsachen-Randomizer (DE): Schnueffelstellen (a3 39) und Kuerbisse/Truhen (a3 3a/3b).
# Muster: 18 39 01 84 <Item lo> <Item hi> 17 3d 01 <mapref> 00 a3 <39|3a|3b> 0c <Flag>
import sys, re, random
def zutat(rnd):
    while True:
        z = 0x200 + rnd.randrange(22)
        if z != 0x205: return z          # nie Matschpfeffer (Story)

pfad, seed = sys.argv[1], int(sys.argv[2])
ZUTATEN = ["Wachs","Wasser","Essig","Wurzel","Oel","Matschpfeffer","Pilz","Meteorit","Kalkstein","Eisen","Schiesspulver",
           "Fett","Feder","Ethanol","Trockeneis","Kristall","Lehm","Schwefel","Knochen","Atlas-Amulett","Asche","Eichel"]
VERBRAUCH = {0x800:"Bluetenblatt",0x801:"Nektar",0x802:"Honig",0x803:"Hundekuchen",0x804:"Fluegel",0x805:"Kraeuter",0x806:"Feenstaub",0x807:"Zauberperle"}
def name(v): return ZUTATEN[v-0x200] if 0x200<=v<=0x215 else VERBRAUCH.get(v, "Ruestung %03X"%v if 0x400<=v<0x500 else "%03X"%v)
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
pat = re.compile(rb'(?=\x18\x39\x01\x84(..)\x17\x3d\x01.\x00\xa3([\x39\x3a\x3b])\x0c..)', re.S)
schnueffel, kuerbis, ruestung, geschuetzt = [], [], [], []
for m in pat.finditer(bytes(r)):
    v = int.from_bytes(m.group(1),'little'); s = m.start()+4; art = m.group(2)[0]
    if v == 0x205: geschuetzt.append(s); continue          # Matschpfeffer: Story (Vulkan) -> nie veraendern
    if 0x400 <= v < 0x500: ruestung.append((s,v))
    elif 0x200 <= v <= 0x215 or 0x800 <= v <= 0x807:
        (schnueffel if art == 0x39 else kuerbis).append((s,v))
rnd = random.Random(seed); zaehl = {}
def setze(s, v): r[s:s+2] = v.to_bytes(2,'little'); zaehl[name(v)] = zaehl.get(name(v),0)+1
for s,_ in schnueffel:                                   # Schnueffeln: Zutat, 1 % Zauberperle
    setze(s, 0x807 if rnd.random() < 0.01 else zutat(rnd))
for s,_ in kuerbis:                                      # Kuerbis/Truhe: 5 % Perle, 50 % Verbrauch, sonst Zutat
    x = rnd.random()
    setze(s, 0x807 if x < 0.05 else 0x800 + rnd.randrange(7) if x < 0.55 else zutat(rnd))
werte = [v for _,v in ruestung]; rnd.shuffle(werte)     # Ruestungen untereinander tauschen
for (s,_),v in zip(ruestung, werte): setze(s, v)
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d)
print("Seed %d: %d Schnueffelstellen, %d Kuerbisse/Truhen, %d Ruestungen getauscht, %d Matschpfeffer-Stellen unveraendert" % (seed, len(schnueffel), len(kuerbis), len(ruestung), len(geschuetzt)))
print("Verteilung:", ", ".join("%s %d"%(k,v) for k,v in sorted(zaehl.items(), key=lambda x:-x[1])))
