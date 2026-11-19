# DarkSoulCave PROTOTYP Kartenplaetze (Max: die Hoehle benutzt nur eigene KOPIEN von Karten in den neuen Nummern
# 0x80..0xFE, ohne NPCs/Szenen; die Originale 0x00..0x7E bleiben unveraendert). NICHT in work/bau.sh eingetragen.
# Aufruf: python3 soe_kartenplaetze.py ROM [--kopien=80:05,81:17,...] [--original] [--gefiltert=05,17,...]
#
# Grundlage: work/dsc/plaetze/STELLEN.md (alle Leser von 7E:0ADB). Im Original lesen nur 2 Stellen eine Tabelle je Karte:
#  1. 90:8F6E/8F74 LDA $A0FDE5,X / $A0FDE6,X (X = Karte*4): Zeiger auf den Kartenkopf (Grafik, Kollision, Paletten,
#     Typ, Ausloeser-Listen). -> Tabelle mit 256 Eintraegen nach KT (FF:0000), nur die zwei Operanden umgebogen.
#     Kopie 0x80+i bekommt den Kopfzeiger ihres Originals (die gepackten Daten werden mitbenutzt, nichts kopiert).
#  2. 8C:D2A1..D2BC (Karte*5 per $4202, LDA $93801B,X): Raumskript-Zeiger. Hier wird NICHT der Operand an D2B1
#     geaendert (dort haengt soe_raumfilter seinen Hook ein), sondern D2A1 (LDA $0ADB ; ORA #$0500) durch JSL 'rs'
#     ersetzt: Karte < 0x80 -> genau wie bisher weiter (A = Karte|0500); Karte >= 0x80 -> Zeiger aus RST (FF:0400,
#     3 Byte je Kopie) nach $26..$28 und Ruecksprung direkt auf 8C:D2BD (JSL 8C:D2FD = Skript starten).
#     Damit laufen Kopien NIE durch den Raumfilter-Hook und bekommen immer "ihr" Skript, egal ob AKT (30:7002) an ist.
#  3. Spielstand-Laden (8D:B2A0, Kette: vorheriger JSL bleibt erhalten): steht im geladenen Stand eine Kopie-Nummer,
#     wird sie auf das Original (ORIG-Tabelle) umgesetzt. Gleiche Karte/Kollision -> die Position bleibt gueltig.
#     (Speichern in der Hoehle sperrt schon soe_speicher ueber 30:7002.)
# Raumskript der Kopien: Ist soe_raumfilter VORHER eingebaut, nimmt jede Kopie das bereinigte Skript ihres Originals
# aus dessen Tabelle (ohne NPCs/Dialoge/Szenen, mit Musik/Einblenden/Monstern); sonst (oder mit --original) das
# Original-Skript. --gefiltert=KK,.. beschraenkt das auf bestimmte Original-Karten.
# Weitere Tabelle fuer andere Module: ORIG (FF:0600, 256 Byte): ORIG[k] = Original-Karte von k (k < 0x80: k selbst,
# unbenutzte Kopie-Plaetze: 04). Damit koennen Hooks mit Karten-Tabellen (KT/ERL/KISTEN, CMP #5E/#04 ...) Kopien
# auf ihr Original abbilden: LDA $7E0ADB ; AND #$00FF ; TAX ; LDA $FF0600,X ; AND #$00FF.
# Nicht behandelt (bewusst): Ausloeser-Listen im mitbenutzten Kopf -> Tueren/Truhen der Kopie benutzen die Tuer-
# und Truhenskripte des Originals (Ziel = Original-Karte, bis der Hoehlen-Tuer-Hook umleitet; Truhen filtert
# soe_raumfilter bei AKT=1). Story-Vergleiche unserer Hooks (CMP #18/#1D/...) greifen in Kopien nicht (gewollt).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm import assemble

BANK = 0xFF
KT   = 0xFF0000      # 256 x 4 Byte Kopfzeiger (Ersatz fuer A0:FDE5)
RST  = 0xFF0400      # 128 x 3 Byte Raumskript-Zeiger fuer 0x80..0xFF
ORIG = 0xFF0600      # 256 Byte Original-Karte
CODE = 0xFF0700
ALT_KT, ALT_RS = 0xA0FDE5, 0x93801B
PLATZHALTER = 0x04   # unbenutzte Kopie-Plaetze und 7F: Brunnen/Hoehlendorf
# Testauswahl (Max: spaeter ~100 Karten ohne NPCs/Szenen, Nummern egal)
KOPIEN = {0x80: 0x05, 0x81: 0x17, 0x82: 0x29, 0x83: 0x3A, 0x84: 0x54,
          0x85: 0x0F, 0x86: 0x1E, 0x87: 0x12, 0x88: 0x22, 0x89: 0x4B}

def off(a):
    b = a >> 16
    return (a & 0x3FFFFF) if b >= 0xC0 or b & 0x40 else ((b & 0x3F) << 16) | (a & 0xFFFF)
def L(a): return [a & 0xFF, (a >> 8) & 0xFF, a >> 16]

def raumfilter_tabelle(r):
    """Adresse der Raumskript-Ersatztabelle von soe_raumfilter, wenn dessen Hook an 8C:D2B1 sitzt, sonst None."""
    o = off(0x8CD2B1)
    if r[o] != 0x22: return None
    try:
        import soe_raumfilter
    except Exception:
        return None
    hook = r[o + 1] | r[o + 2] << 8 | r[o + 3] << 16
    if hook >> 16 != soe_raumfilter.CODE_BANK: return None
    return (soe_raumfilter.CODE_BANK << 16) | 0x1000

def einbau(pfad, kopien=KOPIEN, original=False, gefiltert=None):
    d = bytearray(open(pfad, 'rb').read()); H = len(d) % 1024; r = memoryview(d)[H:]
    assert all(0x80 <= k <= 0xFE for k in kopien), 'Kopie-Nummern nur 0x80..0xFE'
    assert all(0 <= v <= 0x7E for v in kopien.values()), 'Original nur 0x00..0x7E'
    alt_k = bytes(r[off(ALT_KT):off(ALT_KT) + 127 * 4])
    alt_r = bytes(r[off(ALT_RS):off(ALT_RS) + 127 * 5])
    rf = None if original else raumfilter_tabelle(r)
    orig = [k for k in range(0x80)] + [kopien.get(0x80 + i, PLATZHALTER) for i in range(0x80)]
    orig[0x7F] = PLATZHALTER
    kt = bytearray(); rst = bytearray(); quelle = {}
    for k in range(256):
        o = orig[k]; kt += alt_k[o * 4:o * 4 + 4]
    for i in range(0x80):
        k = 0x80 + i; o = orig[k]; p = alt_r[o * 5:o * 5 + 3]; q = 'original'
        if rf is not None and k in kopien and (gefiltert is None or o in gefiltert):
            e = bytes(r[off(rf + o * 5):off(rf + o * 5) + 3])
            if e[2] != 0xFF: p = e; q = 'gefiltert'
        rst += p; quelle[k] = q
    code, lab = assemble(CODE, [
      # ---- 8C:D2A1 (LDA $0ADB ; ORA #$0500) -> JSL rs ; NOP ; NOP.  M/X 16 bit, DB = 8C.
      'rs:', [0xAF, 0xDB, 0x0A, 0x7E, 0x29, 0xFF, 0x00, 0xC9, 0x80, 0x00], ('bra8', 0xB0, 'rs_k'),
      [0x09, 0x00, 0x05, 0x6B],                                       # Original: A = Karte|0500 -> STA $4202 ...
      'rs_k:', [0x29, 0x7F, 0x00, 0x48, 0x0A, 0x18, 0x63, 0x01, 0xAA, 0x68],   # X = (Karte-80)*3
      [0xBF] + L(RST) + [0x85, 0x26, 0xBF] + L(RST + 1) + [0x85, 0x27],     # $26..$28 = Skriptzeiger (wie D2B1..D2BB)
      [0xA9, 0xBC, 0xD2, 0x83, 0x01, 0x6B],                           # Ruecksprung -> 8C:D2BD (JSL 8C:D2FD)
      # ---- 8D:B2A0 Laden: bisherigen Hook aufrufen, danach Kopie-Nummer -> Original
      'la:', [0x22, 0, 0, 0, 0x08, 0xC2, 0x30, 0x48, 0xDA, 0xAF, 0xDB, 0x0A, 0x7E, 0x29, 0xFF, 0x00, 0xC9, 0x80, 0x00],
      ('bra8', 0x90, 'la_w'),
      [0xAA, 0xBF] + L(ORIG) + [0x29, 0xFF, 0x00, 0x8F, 0xDB, 0x0A, 0x7E],
      'la_w:', [0xFA, 0x68, 0x28, 0x6B],
    ])
    code = bytearray(code)
    o = off(0x8DB2A0); assert r[o] == 0x22, 'Lade-Hook 8D:B2A0 fehlt: ' + bytes(r[o:o + 4]).hex()
    la = lab['la'] - CODE; code[la + 1:la + 4] = r[o + 1:o + 4]              # Kette: alter JSL-Zielort
    def put(adr, bs):
        o = off(adr); assert all(b == 0xFF for b in r[o:o + len(bs)]), 'nicht frei: %06X' % adr; r[o:o + len(bs)] = bs
    put(KT, bytes(kt)); put(RST, bytes(rst)); put(ORIG, bytes(orig)); put(CODE, bytes(code))
    for a, alt, neu in ((0x908F6E, ALT_KT, KT), (0x908F74, ALT_KT + 1, KT + 1)):
        o = off(a); assert bytes(r[o:o + 4]) == bytes([0xBF]) + alt.to_bytes(3, 'little'), hex(a)
        r[o + 1:o + 4] = neu.to_bytes(3, 'little')
    o = off(0x8CD2A1); assert bytes(r[o:o + 6]) == bytes([0xAD, 0xDB, 0x0A, 0x09, 0x00, 0x05]), bytes(r[o:o + 6]).hex()
    r[o:o + 6] = bytes([0x22] + L(lab['rs']) + [0xEA, 0xEA])
    o = off(0x8DB2A0); r[o:o + 4] = bytes([0x22] + L(lab['la']))
    h = 0xFFC0
    for _ in range(2):
        s = sum(r) & 0xFFFF; r[h + 0x1E:h + 0x20] = s.to_bytes(2, 'little'); r[h + 0x1C:h + 0x1E] = (s ^ 0xFFFF).to_bytes(2, 'little')
    open(pfad, 'wb').write(d)
    print('Kartenplaetze eingebaut: %d Kopien (%s), Raumfilter %s' % (len(kopien),
          ' '.join('%02X=%02X/%s' % (k, kopien[k], quelle[k][0]) for k in sorted(kopien)), 'gefunden' if rf else 'nicht da'))

if __name__ == '__main__':
    kop = KOPIEN; gef = None
    for x in sys.argv[2:]:
        if x.startswith('--kopien='): kop = {int(a, 16): int(b, 16) for a, b in (e.split(':') for e in x[9:].split(','))}
        if x.startswith('--gefiltert='): gef = {int(k, 16) for k in x[12:].split(',')}
    einbau(sys.argv[1], kop, original='--original' in sys.argv, gefiltert=gef)
