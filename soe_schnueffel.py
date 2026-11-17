# Schnueffel-/Topf-Randomizer (DE): jede Stelle "18 39 01 84 <Zutat> 02 17 3d 01 <Menge> 00 a3 xx 0c <Flag>" bekommt eine zufaellige Zutat.
import sys, re, random
pfad, seed = sys.argv[1], int(sys.argv[2])
NAMEN = ["Wachs","Wasser","Essig","Wurzel","Oel","Matschpfeffer","Pilz","Meteorit","Kalkstein","Eisen","Schiesspulver",
         "Fett","Feder","Ethanol","Trockeneis","Kristall","Lehm","Schwefel","Knochen","Atlas-Amulett","Asche","Eichel"]
d = bytearray(open(pfad,'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
pat = re.compile(rb'(?=\x18\x39\x01\x84([\x00-\x15])\x02\x17\x3d\x01.\x00\xa3[\x39\x3a\x3b]\x0c..)', re.S)
stellen = [m.start() for m in pat.finditer(bytes(r))]
rnd = random.Random(seed); vorher = {}; nachher = {}; perlen = []
for s in stellen:
    alt = r[s+4]; neu = rnd.randrange(22)
    if rnd.random() < 0.01:          # 1 % Zauberperle (Item 0x807)
        r[s+4] = 0x07; r[s+5] = 0x08; perlen.append(s); continue
    vorher[alt] = vorher.get(alt,0)+1; nachher[neu] = nachher.get(neu,0)+1
    r[s+4] = neu
h = 0xFFC0
for _ in range(2):
    c = sum(r) & 0xFFFF; r[h+0x1E:h+0x20] = c.to_bytes(2,'little'); r[h+0x1C:h+0x1E] = (c^0xFFFF).to_bytes(2,'little')
open(pfad,'wb').write(d)
print("Seed", seed, "-", len(stellen), "Stellen neu verteilt, davon", len(perlen), "Zauberperlen")
print("vorher: ", ", ".join("%s %d"%(NAMEN[k],v) for k,v in sorted(vorher.items(), key=lambda x:-x[1])))
print("nachher:", ", ".join("%s %d"%(NAMEN[k],v) for k,v in sorted(nachher.items(), key=lambda x:-x[1])))
