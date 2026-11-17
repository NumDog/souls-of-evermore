# Secret of Evermore (DE): technisches Wissen

Grundlage ist die deutsche ROM `Secret Of Evermore [dt].smc`: HiROM, 512-Byte-Header, Region 9 (Deutschland), CRC32 ohne Header 27F60E77.
Unsere Patches erweitern die ROM auf 4 MB. Der eigene Code liegt in **Bank $F0** (Datei-Offset 0x300000).
Adressen sind SNES-Adressen. Datei-Offset ohne Header: Banks ≥ $C0 → `adr & 0x3FFFFF`, Banks $80–$BF → `((bank&0x3F)<<16)|adr`.

## Bauen
Basis (ab v39): `~/Downloads/Secret Of Evermore [dt] HART-nur-Monster.smc` (Monster-HP/ATK ×2 in der ROM, Level-Zuwächse original). Schwer rechnet daraus ×3/4 (= ×1,5), Normal ×1/2 (= Original). Früher: `HART+Level (vor NG+).smc` (Level-Zuwächse ×2).
Die Reihenfolge ist wichtig, weil spätere Patches auf frühere Hooks aufbauen:

1. `soe_ngplus_patch.py <basis> <ziel>`: ROM auf 4 MB, NG+-Skalierung der Gegner
2. `soe_waffe_plus.py`: Waffe +1
3. `soe_ngplus_ende.py`: Abspann-Weiche, NG+-Datensatz, Namen übernehmen, „New Game +N“ im Menü
4. `soe_mindestschaden.py`: Mindestschaden im NG+
5. `soe_formel_plus.py`: Formel +1
6. `soe_menue_plus.py`: „+N“ hinter Waffennamen im Ringmenü
7. `soe_zufall_live.py`: Fundsachen-Zufall beim Finden
8. `soe_haendler.py`: Händler-Zufall und Preise (braucht `work/haendlerpreise.json`)
9. `soe_einstellungen.py`: Einstellungsmenü
10. `soe_vulgor_larven.py`: doppelte Lavawürmer bei Vulgor
11. `soe_gegner_zufall.py`: Gegner-Randomizer
12. `soe_ton_sicher.py`: Warteschleifen auf den Soundchip mit Zeitlimit
13. `soe_waffe_meldung.py`: Meldung „<Waffe> erhalten!“ bei Chaos-Waffenfunden + Laserschwert-Spruch am Anfang
15. `soe_menue_kraft.py`: echte Waffenkraft im Ring-Menü
19. `soe_ton_fremd.py`: Geräusche fremder Gegner stumm
18. `soe_vulgor_rache.py`: 2 Raptoren nach der Bronze-Axt im Vulgor-Raum
17. `soe_belohnung.py`: Erfahrung und Geld × Schwierigkeitsfaktor
16. `soe_aufstehen.py`: Aufstehen statt Game Over (Schwer/Chaos), Geld bleibt liegen
14. `soe_laser_start.py`: Startwaffe je Gegner-Modus (Chaos Laserschwert, Gebiet Drachentöter)
(`soe_hund_schwarz.py` gibt es noch, ist aber nicht mehr im Bau: Max wollte die Originalfarbe zurück.)

Werkzeuge: `asm.py` (Mini-Assembler mit Marken: `('bra8',op,'marke')`, `('jmp','marke')`, `('jsr','marke')`) und `dis65816.py rom ADR LÄNGE [m8] [x8]` (Disassembler).
Installieren: fertige ROM nach `~/Library/Application Support/OpenEmu/Game Library/roms/Super Nintendo (SNES)/Secret Of Evermore [dt].smc` kopieren, vorher die alte Datei nach `~/Downloads/SoE Sicherung Spielstaende/` sichern.

## Testen mit Mesen 2 (ohne Fenster)
`mesen/app/Mesen.app/Contents/MacOS/Mesen --testrunner rom.smc skript.lua`
- Lua-Skript immer mit `print("start")` beginnen. Mesen beendet sich manchmal zufällig mit 255, dann den Test wiederholen.
- Batterie-Speicherung: `~/Library/Application Support/Mesen2/Saves/<romname>.srm`, vor jedem Lauf frisch kopieren (`work/orig_sav.srm`).
- Tasten: `emu.setInput({start=true},0)` im Ereignis `inputPolled`. Port 1 = SnesController (ist eingestellt).
- Titel-Demo (ohne Eingabe): ab ca. Frame 2700 der Vulgor-Kampf. Laden: Start bei 2450, B bei 2760 und 2810.
- Speicher-Rückrufe auf Register ($42xx) und VRAM funktionieren in Mesen nicht.
- In-Game: Y = Ringmenü des Jungen (zweimal hoch = Waffen-Ring), X = Menü des Hundes.

## Speicher (WRAM $7E)
| Adresse | Inhalt |
|---|---|
| 0A35 / 0A3F / 0A41 / 0A43 | Junge Max-HP / Angriff / Verteidigung / Magie-Abwehr |
| 0A49 (4 B) / 0A50 | Junge EXP / Level |
| 0A7F… / 0A9A | Hund Werte / Level |
| 0ABA | ausgerüstete Waffe (ID gerade: 02 Knochenknüppel … 18 Neutronenspeer, 1A Bazooka) |
| 0ABE / 0AC0 / 0AC2 / 0AC4 | angelegte Rüstungen als Zeiger 0x4142 + 10·Nr (0 = nichts); Nr muss im Inventar 231D+Nr ≥ 1 sein, sonst Hänger im Menü |
| 0AD2–0ADA | Waffen-Reihenfolge im Ring (FF = leer) |
| 0AC6 / 0AC9 / 0ACC / 0ACF | Geld: Krallen / Juwelen / Goldmünzen / Credits (je 3 B) |
| 0ADB | aktuelle Karte |
| 0ADD + 2·i | Waffen-Level (hi = Stufe) |
| 0100 | Bildzähler (NMI) |
| 2210 / 2234 | Name Junge / Hund |
| 2250–2256 | **unser** Waffe+1-Zähler (Nibbles), Bit7 von 2256 = Lade-Merker |
| 2257 | **unser** NG+-Zyklus |
| 2258 ff. | Story-Flags (Bit n = $2258 + n/8). Formel gelernt = Flag 0–34 |
| 22DA / 22DB | Waffen-Besitz-Bits (22DA: 20 Tarantelaxt, 40 Bronzeaxt; 22DB: 02 Speer, 04 Bronzespeer) |
| 2261 | Bits 1/2 = Junge/Hund nicht spielbar (beim ENDE beide gesetzt) |
| 22FF + i | Zutaten (Item 0x200+i). **2304 = Matschpfeffer (0x205)** |
| 2315–231C | Verbrauchsgüter (Item 0x800+i: 0 Blatt, 1 Nektar, 2 Honig, 3 Hundekuchen, 4 Flügel, 5 Elixier, 6 Elfenstaub, 7 Zauberperle), 231D–2344 Rüstungen |
| 2348 | Region (Schlüssel für die Gebiets-Listen, &7) |
| 2391 | Skript-Variable „gefundenes Item“ (0x139) |
| 2441 | Waffe vergeben/ausrüsten (ID schreiben → Spiel gibt sie und rüstet aus). Auch Ring-Menü, Raumwechsel, Laden und Spielstart schreiben hier! |
| 2F52+2i / 2F98+2i | Formel-Fortschritt / Formel-Stufe |
| 3DE5 + k·0x8E | Gegner-Objekte: +0x2A HP, +0x60 Vorlage (≥ $8000 = Monster aus der ROM) |
| 4EB3 / 4F61 | aktuelle HP Junge / Hund; Objekt Junge 4E89, Hund 4F37 |
| 4EA3 / 4EA5 | Position Junge x / y in Pixeln (Objekt +0x1A/+0x1C; Hund 4F51/4F53) |
| 0B97 / 0BC7 / 0E6E | Händler: Waren (Byte, FF-Ende) / Preise (Wort) / Art |

## Batterie-Speicherung (SRAM $30:6000–7FFF)
Spielstände liegen in Slots à ca. 0x340 B. Unsere Bereiche:
| SRAM | Inhalt |
|---|---|
| 7C00 "NG" / 7C02 / 7C04–7D90 | NG+-Datensatz (Merker, Talismane, WRAM-Blöcke) |
| 7E00 / 7E40 | Textpuffer „New Game +N“ / „Waffe +N“ |
| 7E80 | globaler Zufallszustand (Xorshift16) |
| 7E82–7EB0 | Hilfsvariablen (Zufallszustände 7E9C/7EA6/7EA8, Händler-Ware 7E84, Gegner-Modus 7E8A …) |
| 7E91 | Schwer-Stufe (0 ×1,5, 1 ×2, 2 ×3, 3 ×5, 4 ×10) |
| **7E90** | **Einstellungen**: Bit0 Gegner normal, Bit1 Fundsachen original, Bit7 Fundsachen neu, Bit2 Händler original, Bit5 Händler neu, Bits3–4 Gegner-Modus (0 Original, 1 Ähnlich, 2 Chaos, 3 Gebiet), Bit6 Gegner neu |
| 7EB2 / 7EB4 / 7EB6 | Sonderfund-Zähler / aktuelle Schwelle / Händler-Mischungscode |
| 7EB8 | Merker „echte Waffen-Gabe“ (nur dann Waffe +1) |
| 7EBA / 7EBC / 7EBE | gemerkte Fund-Waffe / Spruch-Merker / Startwaffe (Hund-Szene) |
| 7EC0–7EDB | Textpuffer Waffen-Meldung |
| 7FC0–7FC5 | Mini-Skript für die Rückkehr zum Eingang |
| 7FEA / 7FEC / 7FEE / 7FF8 | Todesstelle x / y / Zustand (1 gemerkt, 2 scharf) / Abstand |
| 7FC8 / 7FCC / 7FCE / 7FD2 / 7FD4 / 7FD8–7FE0 | Geld-Rückgabe überspringen / letzte Larven-Position x,y / Rache-Zähler / Rache erledigt / Mini-Skript Raptoren |
| 7EF0 / 7EF1 / 7EF2 / 7EF4 / 7EF6 | Raumeingang: Karte / gültig / x·8 / y·8 / Merker „zum Eingang“ |
| 7EE0–7EEB / 7EEC / 7EED / 7EEE | Blutfleck: Geld (4 Währungen) / Karte / gültig / Merker „unser Aufstehen“ |
| 7E9A | Durchgangs-Code (wird beim Verlassen des Menüs gesetzt) |
| 7F00–7F8F | Gebiets-Listen (8 Regionen × 18 B Bitfeld) |
Achtung: Laden eines OpenEmu-Save-States überschreibt die komplette SRAM. Mesen füllt eine neue SRAM mit FF.

## ROM-Daten
| Wo | Was |
|---|---|
| 0xEB678 + Nr·74 | Monster-Vorlagen ($8E:B678). +0x0F HP, +0x19 ATK, +0x1B DEF, +0x23 EXP, +0x27 Geld, +0x00 Namenszeiger. Ab Nr 51 Monster. |
| 0xC9532 … (US + 0x395) | Level-Tabellen (Junge HP C9532, DEF C9610, ATK C96EE, MDEF C97CC; Hund C98AA …), EXP C8F65 |
| 0x507A0 | Waffennamen (Klartext) |
| 0x5000A / 0x50026 | Waffen-Besitz-Adresse/Bit je ID |
| 0x502A1 / 0x502E7 | Formel-gelernt-Adresse/Bit |
| 0x52333 | „Neues Spiel“ |
| 8C:E712 | Händler: Waren-Nr → Ring-Byte |
| 0x10AD10–0x10ADF0 | Paletten des Jungen (8 Varianten) |
| 0x10AE10 / AE30 / AE50 / AE70 | Paletten des Hundes: Wolf / Windhund / Pudel / Toaster (auch Hunde-Symbol) |

Wichtige Monster-Nummern: 110 Raptor (normal), 89/90 Skript-Raptoren, 112 Lavawurm, 113 Moskito, 118 Vulgors Herzkammer, 122/123 Klauen, 96 Sachmet (Statue).

## Hooks im Original-Code (→ eigener Code)
| Stelle | Zweck |
|---|---|
| 8F:B10C / BFD7 / C007 | Monster-HP beim Erscheinen / Angriff / Verteidigung → Skalierung (Trampoline F0:0010/0040/0070, nur bei Vorlage ≥ $8000) |
| 8F:847C / 8F:92AA | Waffenkraft / Waffe erhalten (+1) |
| 8D:B2A0 | Laden vergibt Waffe neu → Lade-Merker |
| 8C:DF82 | Skript lädt Karte → NG+ sichern (Karte 0x63 = ENDE) und zurückholen |
| 8D:CBD5 / 8C:E5CB / 80:8C24 | Namenseingabe überspringen |
| 8D:C924 | Text „Neues Spiel“ im Lade-Menü |
| 8D:CBC0 | Einstellungsmenü (New-Game-Zweig) |
| 8F:C1CC | Schaden am Spieler (Mindestschaden) |
| 8C:DC49 | Skriptbefehl Flag setzen (Formel +1) |
| 8E:A479 | Ringmenü-Titel (Waffe +N) |
| 8E:A4A2 / 8E:A4D1 | Ringmenü: Kraft aktuelle / ausgewählte Waffe (C4:3EB4 Zeigertabelle) → echte Kraft mit +N |
| 8C:DBC9 | Skriptbefehl Variable = Ausdruck (Fundsachen-Zufall) |
| 8C:E6C8 / E70C | Händler: Ware / Preis (Skriptbefehl 0x89 `<ware> <preis>`) |
| (Sperr-Karten Gegner-Zufall) | 0x18 Vulgor, 0x5C erster Boss |
| 8C:837F … 8C:8532 (10 Stellen) | `CMP $2140/$2142 ; BNE *` Warten auf Soundchip → F0:3600 (Zeitlimit, Merker $7F:FFF0) |
| 8F:8292 / 8F:82D4 / 8F:866E | Erfahrung Junge / Hund (Vorlage +0x23, 32 Bit) / Geld (Vorlage +0x27, Währung = $2348) → × Schwierigkeitsfaktor (F0:3E00) |
| 8F:8093 | Spielbeginn: Startwaffe (LDA #2 ; STA $2441) → F0:3A00 (Chaos 08 Laserschwert, Gebiet 04 Drachentöter; setzt Lade-Merker → kein +1) |
| 8F:B045 | Gegner erscheinen ($02 Vorlage, $46/$48 Position) → F0:1980 → Gegner-Zufall → Larven → Original |

Skript-Zahlencodes: `b0–bf` = 0–15, `82 xx` = Byte, `84 xx xx` = Wort. Fundstelle: `18 39 01 84 <id lo hi> 17 3d 01 <mapref> 00 a3 <39 Schnüffeln | 3a/3b Kürbis> 0c <flag>`.
Text-Routinen: `8C:B097` Textfeld leeren, `8C:A198` Text aus $22/$24 in Feld Y, `8C:B397` Fenster aktualisieren (**nicht** `8C:B051`, das macht den Bildschirm schwarz).
Hardware-Register **immer lang adressieren** (`$00:4204`), sonst landet der Zugriff bei DBR=7E im RAM.

## Speicher-Belegung Bank $F0
0010–009F Trampoline · 0100 Skalierung · 0180 Level-Bonus · 0200/0280/0300/0380 Waffe+1 · 0400–07FF NG+ (Stash/Restore/Name/Trigger) · 0800–0A00 Namen überspringen, Menütext · 0C00 ATKX (aus) · 0D00 Mindestschaden · 0E00 Formel+1 · 0F00 Ringmenü +N · 1000–11FF Fundsachen · 1200 Händler 1 · 1400–17FF Einstellungsmenü · 1800 Larven · 1980 Gegner-Vor-Hook · 1A00–1FFF Gegner-Zufall · 2000–27FF Gegner-Listen · 2800–2DFF Menütexte und Tabellen · 2E00 Händlerpreise · 2F00 Rüstungs-Mischung · 2F40 Händler 2 · 2F80 Waffenliste · 3000 Fundsachen-Zufall · 3400 Chaos-Schwellen · 3500 Händler-Mischtabellen · 3600 Ton-Sicherheitsnetz

## Skript-Engine und Texte
- Befehlstabelle: 8C:ECBE + Befehl·2 (z. B. 18 → 8C:DBBA, 52 → 8C:DD87, a3 → 8C:D789, 29 → 8C:D7B2).
- `a3 nn` = globales Skript nn starten. Tabelle in 93:8000: Eintrag bei 93:8000 + [93:8000] + [93:8008] + nn·3 (3 Byte p).
  Adresse aus p: Bank = 0x93 + (p>>15), Adresse = 0x8000 | (p & 0x7FFF). `29 p p p` = Skript an Adresse p starten (als Kind-Faden).
- Fundablauf: Skript 3a → 3e (Prüfung), 3f (Gegenstand geben + Meldung „X gefunden!“), 41 („Du hast genug X!“).
- Story-Waffe: `18 e9 01 <waffe>` ($2441 = Waffe), `29 33 3f 00` (Fanfare/Pose 93:BF33), `52 <text>` („Bronzeaxt erhalten!“).
- `52 tt tt` = Text zeigen. 8C:D0F6: Text-ID → Zeiger aus 92:8000+ID (3 Byte, Bit15 des 2. Worts = komprimiert, Bank = Byte+0xC0).
  Unkomprimiert: Klartext bis 0. Komprimiert: Entpacker 8C:D147 (Nibbles, Wörterbuch 92:A41E[letztes Zeichen·14+n]), nachgebaut in `soe_text.py`.
- Text 0x42 „Zauberperle gefunden!“, 0x3F „¢ Zauberperlen gefunden!“ (¢ = Anzahl), 0x231 „Du hast genug Zauberperlen!“. Fundtexte beginnen mit 0x97.
- Dialogtexte (Befehl `51 tt tt`): 8C:D0B8 Text-ID → Zeiger (wie D0F6), Anzeige 8C:A198. Steuerzeichen: 0x96 Junge spricht, 0x80 '=' 0x80 Pause, 0x86 auf Knopf warten, ä=E3 ö=EF ü=F3.
- Hund-Szene am Anfang (Prähistorika): Skript 94:8820 `18 e9 01 b2` (Knochenknüppel), danach `51 57 06` Text 0x657. Beim Spielstart steht 22DA schon auf 02.
- OpenEmu-Save-States (snes9x): Blöcke NAM/CPU/REG/PPU/DMA/VRA/RAM/SRA/FIL/SND/…; Mehrbyte-Werte big-endian (REG: PB DB P A D S X Y PC). SND = SPC-RAM (64 KB) + Zustand; toter Soundchip: SPC-RAM $F1 und $FA–$FC = 0.
- Klartext-Anzeige: 8C:C8E4 zeigt Text ab [$22] (Bank $24, auch SRAM $30 geht).

## Tod / Game Over (Stand 17.11., für das Lagerfeuer-System)
- Todestext Klartext bei C5:0723: `96 92 "Leider haben " 80 '=' 80 81 " und " 82 " nicht überlebt..." 80 A5 81 00` (81 = Name Junge, 82 = Name Hund).
- Game-Over-Routine in Bank 8E um E1xx–E3EC: schaltet Bildebenen ab (8E:E230 STZ $212C…), sperrt Junge/Hund (TSB $4E99/$4F47 Bit 0x40, $4E9B/$4F49 Bit 0x100),
  zeigt den Text (8E:E2F2 LDA #$0723 → 8C:A198), blendet aus (Schleife 8E:E304–E3A6), dann **8E:E3BA JSL $8EE53B = Lade-Menü**;
  ohne Bit 0x40 in $7E22EA → JML $80:84C9 (Neustart).
- Hauptschleife des Spiels: 8E:E4D9–E538 (JSL 8E:E3EF pro Bild).
- Elfenstaub (0x806) belebt im Original wieder („Elfenstaub holt Dich zurück, wenn Du gestorben bist“) → mögliche Vorlage für Wiederbeleben.
- Skriptbefehl 0x22 `22 x y kk kk` = Kartenwechsel (8C:DF5A): 8085D8, 8CD2CE, 8FB33F, $0ADB=Karte, 908E95 (laden), $46/$48 = x·8/y·8, STZ $44, 8FB3E5, 8CD27E, Faden beenden. Hauptschleife ruft die Skript-Engine bei 8E:E42D (JSL 8C:D3E2).
- Skriptbefehl `BA nn x y` = Gegner erzeugen (8C:E0DA): Vorlage aus Tabelle 8E:B55A[nn·2] (Raptor 110 = 0x0D, Dschungel-Raptor 89 = 0x2B, Boss-Raptor 90 = 0x6B, Vulgors Herzkammer 118 = 0x14). Objekt-Freiliste: $3DE3, weiter über +$5E; leer → BRK in 8F:B28E!, Position x·8/y·8 → 8F:B045. `3C`/`C2` sind Varianten mit Zusatzwert ($08).
- Skript-Faden starten: 8C:D2FD ($26/$28 = Zeiger p) sucht freien Platz ab 7E:28FC (Größe 0x4F), X+0/X+2 = echte Adresse/Bank (danach umbiegbar, z. B. auf SRAM 30:7FC0), X+3 = 2 (läuft), X+0B/0D = Eltern-Faden. **Laufen** tut nur, was in der aktiven Liste steht: 7E:2F28 + n·2 (Null-Ende, $86 = Ende); anhängen wie 8C:D26B. Engine 8C:D3E2 arbeitet die Liste ab.
- Elfenstaub-Zustand: $00AC,Y aktiv, $14,Y Bit 0x08 Schutz (gelöscht in 91:B216 wenn der Zähler ($60) 0x1C20 erreicht).
- Sterben eines Helden: 90:84E4 ff. (Y = 4E89 Junge / 4F37 Hund). $00AC,Y = Elfenstaub aktiv → 90:84F0 Wiederbeleben (HP 1 bei 90:84FD, Meldung C5:1F33 „Das Glück war Dir hold...“). Sonst Junge → 90:8559 STY $143E = Game-Over-Auslöser; Hund bleibt liegen. Hauptschleife 8E:E41F: $143E ≠ 0/FFFF → 8E:E124 Game Over.
- Spielstände des Todes: „fast tot“, „erst tot“ (Sterbe-Animation, PC 8F:97F7), „tot 2“ (Text sichtbar).

## Sound (Stand 17.11.)
- Treiber-Start (Spielstart): 8C:830C lädt den Treiber von 81:8000 und 81:80DC per IPL (8C:8417), dann Sample-Set 0.
- Befehle an den Treiber: 8C:84F1 / 8C:8527 / 8C:8554 (A = Befehl, Y = Wert; Handshake über $2142 = $9F).
  Befehl 04 = Geräusch (8C:8662: A = Geräusch-Nr, 63 Aufrufer), 06 = Musik, 26 = ? (8C:8641), 0E/02 = Hochladen beginnen/enden.
- Musik: 8C:85E7 (A = Song). 81:9900 = Anzahl (70). Song → Sample-Set: Tabelle 81:9903 + 3·(Anzahl+1) (bisher 1:1).
  8C:8581 lädt das Sample-Set (Zeiger 3 Byte bei 81:9903 + 3·Set, Ziel in Bank 8A), nur wenn es sich vom aktuellen ($0E4D) unterscheidet;
  Blockliste wird per 8C:835A/8362 übertragen.
- Folge: Die Geräusche hängen am Sample-Set der aktuellen Musik/Gegend. Ein fremder Gegner fordert eine Geräusch-Nr an, deren Sample
  im aktuellen Set fehlt → falscher Ton (Raptor im Vulkan) oder Absturz des Soundchips (Flippo).
- „Nachladen“ geht praktisch nicht: Im SPC-RAM ist nur ein Set; zwei Sets zusammenzuführen hieße, das Sample-Format und den Treiber zu verstehen.
- Umgesetzt (v59, soe_ton_fremd.py): Geräusche fremder Gegner stummschalten. WRAM 7F:F000 Karte, F002/F004 heimische Vorlagen, F032/F034 fremde, F080 Bitfeld „passt nicht“. Weitere Geräuschwege: 8C:84F1 mit A=4 direkt (z. B. 8F:8A99, Waffen).
- Ursprünglicher Plan: Beim Erscheinen (Gegner-Zufall-Hook) merken, welche Vorlagen im Raum heimisch sind;
  in 8C:8662 prüfen, ob das aktuelle Objekt ($4C) ein Gegner mit fremder Vorlage ist → Geräusch auslassen.
- Effekte (Slots 7E:3364, Schritt 0x40): 91:9759 liefert freien Platz in Y (DBR=7E), $28/$2E = Besitzer-Objekt, $2A = Dauer, LDX #Typ + JSL 91:973E startet. Typ 8 = Wiederbelebungs-Kreis (blau, wie Elfenstaub). Neues Objekt aus Skript BA steht danach in $0341.
- Objekt +0x0C: Farb-/Paletten-Wert (NICHT Unsichtbar-Bit; 09/0B wirkten nur im Topfraum unsichtbar). 7E:E000-FFFF im Spiel ungenutzt (nur beim Start geloescht) -> Schein-Objekt 7E:FF00 fuer Effekt-Besitzer. Truhen/Toepfe/Kuerbisse sind keine Objekte, sondern Kacheln der Raumgrafik.
- Effekt-Befehl Blitz-Palette 91:C4DD: Halter < 4E89 (Gegner) -> freie Palette via 90:CEB5; Junge (4E89) -> Slot 0C (Palette 6); sonst Slot 0E (Palette 7 = Hund!). Palette laden 90:CF5D (A = Daten, X = Slot), $127A,X = belegt.
## Vulgor-Raum-Skript (Karte 0x18) – Stand 17.11.
- Skript-Verteiler 8C:D48A (LDA [$82] ; JSR (ECBE,X)), Skriptzeiger $82/$84. Opcodes: `09 <ausdruck> <off16>` = wenn Ausdruck falsch -> springe (rel. zum Befehlsende), `04 <off16>` = Sprung, `BA idx x y` = Gegner.
  Ausdruck: `05 nn nn` = Flag nn lesen, `85 nn nn` = Flag lesen + Ende, `94` = NICHT + Ende, `29`/`14`/`a8` = Verknuepfungen. Flag nn = Bit (nn&7) in 7E:2258+nn/8. Flag 0x44 (2260 Bit4) = Vulgor besiegt.
- 94:D5A0 Raumskript. D5DA: Vulgor besiegt (und nicht Spaet-Spiel) -> kein Kampf (D5E6..., Sprung D6C5). D617: Flag44=0 -> normaler Vulgor (D61E: BA 10/11/14 = Klauen 122/123, Herz 118),
  sonst D66B: Bedingung Flags 486/423 (Spaet-Spiel) -> D677: STARKER VULGOR (BA 85/86/84 = Vorlagen 120/121/119: HP 2250/2500/6000, Herz-EXP 10000, Geld 4000) = Original-Rueckkampf.
- Test-Weiche (Lua, funktioniert): D5DA..D5E5 = `09 85 44 00 19 00 09 85 GG GG 91 00` -> besiegt & Flag GG=0 -> starker Vulgor sofort.
- Mesen-Trick: OpenEmu-RAM in laufendes Spiel einspielen (work/inject.lua: Slot laden, f3350 WRAM 0200-1EFF + 2000-1FFFF schreiben, Warp ueber 7EF0-7EF6) -> Raum wird korrekt neu geladen.
- Paletten: WRAM-Kopie 7E:6187 (512 Byte, Palette p bei 6187+32p). Uebertragung 80:85FA (Quelle [$26]/$28, X = Bytes, $2E = Startfarbe; $0106 Bit7 = sofort per DMA, sonst Warteschlange). Bau-Kette endet jetzt mit soe_vulgor_gold.
- Vulgor-Kampfablauf: 94:D6C9 `09 85 9A 04` (Flag 49A = nach erstem Kampf) -> D752; D760 `08 85 44 00` = WENN-wahr-Sprung (Opcode 08); D766 `09 05 44 00 94`. Ausdrucks-Syntax: `29` = UND (infix), `14` = NICHT (nachgestellt), Bit 0x80 = Ende. Ausgang Vulgor-Raum loest bei Junge-y ~503 aus (7E:4EA5).
- Bau-Kette endet jetzt: ... soe_blutfleck_glanz, soe_vulgor_gold, soe_name (ROM-Kopf „SOULS OF EVERMORE“). QR-Codes brauchen tools/qr (swiftc -O tools/qr.swift -o tools/qr).
