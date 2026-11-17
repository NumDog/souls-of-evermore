# Gemeinsame Angaben fuer Infoseite (soe_einstellungen.py) und ENDE-Bildschirm (soe_ende_text.py).
# Nur ASCII, keine Umlaute (ae/oe/ue schreiben). Auch per Umgebungsvariable SOE_INFO_* ueberschreibbar.
import os
NAME = os.environ.get('SOE_INFO_NAME', '(Name folgt)')
MAIL = os.environ.get('SOE_INFO_MAIL', 'numdoks@gmail.com')
TEXT = os.environ.get('SOE_INFO_TEXT', 'Danke fuers Spielen!')
ETH  = os.environ.get('SOE_INFO_ETH',  '0xcDf1355E4365A2ad842F0333E4737372D2128064')
BTC  = os.environ.get('SOE_INFO_BTC',  'bc1pfky3u0htczylv8tdf2jjcclhdc005e294rljvcwutcwjgqak67rswl2nv3')
