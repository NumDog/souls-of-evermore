# Souls of Evermore

Eine Fan-Mod für die **deutsche SNES-Version von Secret of Evermore**.
Im Spiel heißt sie noch „Souls of Evermore“. Mehr Herausforderung, mehr Zufall, ein New Game+ – und ein Tod wie in Dark Souls.

> **Beta (Stand v169):** Noch nicht komplett durchgespielt. Fehler gern melden (am besten mit Screenshot und Spielstand).

## Hauptfunktionen

- **Schwierigkeit von x0,5 bis x10:** Sehr leicht x0,5 (mit Laserschwert, Atomaxt, Laserlanze und Bazooka zum Start) / Leicht x0,75 / Normal (Original) / Schwer x1,5 / Sehr schwer x2 / Extrem x3 / Wahnsinn x5 / Albtraum x10 – Lebenspunkte und Angriff der Gegner, Erfahrung und Geld wachsen mit.
- **New Game+:** Nach dem Abspann geht es mit Level, Ausrüstung und Formeln weiter („New Game +N“), die Gegner werden pro Zyklus stärker (bis x10).
- **Zufallsmodi:** Gegner (Original / Ähnlich / Gebiet / Chaos, fest oder je Raum neu), Fundsachen (fest pro Durchgang oder immer neu) und Händler (mit Original-Preisen, ohne doppelte Waren).
- **Dark-Souls-Tod:** Kein Game Over mehr. Der Junge steht wieder auf, sein Geld bleibt an der Todesstelle liegen (markiert durch einen leuchtenden Kreis). Hinlaufen holt es zurück – wer vorher erneut stirbt, verliert es.
- **Waffen +N:** Doppelt gefundene Waffen werden stärker (+50 % pro Stufe, bis +15), die echte Kraft steht im Ring-Menü. Doppelt bekommene Formeln werden „+1“ (je +1 = 25 % mehr Wirkung, bis +15); die Zauberleiste zeigt +N und Level.
- **Talismane:** genaue Beschreibung mit Zahlen; doppelt bekommen = +1 (Bonus nochmal). Mythenschärpe +10 % Erfahrung/Geld, Schleifstab +10 % Schwertkraft.
- **Schaden bis 9999** pro Schlag.
- **Grenzen raus:** Level bis 999, KP bis 9999, New Game+ bis +99.
- **Goldener Vulgor:** Einmal pro Durchgang ein goldener Rückkampf (x5). Sieg bringt einen **Waffen-Orb** (+1 auf die ausgerüstete Waffe) – danach rächen ihn 10 Raptoren.
- **Souls Cave:** Zufalls-Dungeon mit 99 Untergeschossen (Eingang am Brunnen). Schachbrett als Knotenpunkt, vier Zugänge in zufällige Räume, Säubern versiegelt den Zugang, je Untergeschoss 4 Räume, Treppe und ein Boss, Boss-Marathon auf jedem 5. Untergeschoss (alle Bosse, danach alles +1 und ein Endbosskristall), Händler-Teleporter auf dem Schachbrett, Flügel als Notausgang, Beute von jedem Monster, Tod nimmt die Beute – nur die Gotteshand bringt sie heraus.
- **Verwandelnde Städte (Souls Cave):** Dschungeldorf, Nobilia, Ivor Tower und eine eigene Stadt – alle Menschen werden zu Monstern, Häuser bleiben betretbar.
- **Alle Bosse im Cave-Zufall** mit Boss-Musik; goldener Vulgor immer da, nach jedem Sieg +100 %.
- **Gegner-Info:** Name, KP, EP, Geld und Anzahl der Gegner im Raum bei jedem Treffer.
- Startwaffe je nach Einstellung (Knochenknüppel, Drachentöter oder Laserschwert), Vulgor mit doppelten Lavawürmern, Sicherheitsnetz gegen Tonhänger.

Die ausführliche Liste steht in [`release/LIESMICH.txt`](release/LIESMICH.txt).

## Patchen

**Eine ROM ist nicht enthalten.** Du brauchst deine eigene, legal erstellte Kopie der deutschen Version.

1. ROM: *Secret of Evermore (Deutschland)*, ohne 512-Byte-Header, **CRC32 `27F60E77`**.
2. Einen BPS-Patcher öffnen, z. B. [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) (im Browser, entfernt einen Header automatisch) oder Floating IPS (Flips).
3. ROM und [`Souls-of-Evermore-v169-beta.bps`](https://github.com/NumDog/souls-of-evermore/releases/download/v169-beta/Souls-of-Evermore-v169-beta.bps) (Releases-Seite) auswählen und anwenden.
4. Die fertige 4-MB-ROM läuft z. B. in OpenEmu, snes9x, bsnes oder Mesen.

## Selbst bauen

Die Python-Skripte (`soe_*.py`) bauen die Mod Schritt für Schritt in eine ROM ein, `bps.py` erzeugt daraus den Patch.
Die Reihenfolge der Bau-Kette ist wichtig und steht in [`WISSEN.md`](WISSEN.md) (Abschnitt „Bauen“), zusammen mit technischen Notizen zu Adressen, Hooks und Tests mit Mesen 2.
Werkzeuge: `asm.py` (Mini-Assembler), `dis65816.py` (Disassembler), `bps.py` (BPS-Patch erstellen), `tools/qr.swift` (QR-Codes fuer die Trinkgeld-Seiten, nur macOS: `swiftc -O tools/qr.swift -o tools/qr`).

## Kontakt & Trinkgeld

Im Spiel: Einstellungsmenue -> letzte Zeile -> A = Info, die Trinkgeld-Seiten zeigen QR-Codes.


- E-Mail: numdoks@gmail.com
- BTC: `bc1pfky3u0htczylv8tdf2jjcclhdc005e294rljvcwutcwjgqak67rswl2nv3`
- ETH: `0xcDf1355E4365A2ad842F0333E4737372D2128064`
- SOL: `3paG1KXBdFamy7cBVxvHj1yKQ9XGgm4bWHzYQhDoqNKJ`

## Rechtliches

Secret of Evermore ist © Square / Square Enix. Dies ist ein nicht-kommerzielles Fan-Projekt.
Der Patch enthält keine Daten des Originalspiels außer den geänderten Stellen.
