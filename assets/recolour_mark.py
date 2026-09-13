# -*- coding: utf-8 -*-
"""Dunkelfassung der StrawKnight-Marke: die Tinte hell, die Augen dunkel.

Die Zeichnung ist fuer hellen Grund gebaut. Auf dem dunklen Grund des Emulators
passiert zweierlei: die beiden Aehren oben stehen frei und sind reines
#1d1d1b, also unsichtbar, und die Kontur ringsum liest sich nicht als Linie,
sondern als Luecke zwischen Gold und Grund.

Umgefaerbt wird deshalb die Tinte, nicht der Grund. Betroffen sind drei Stellen,
und alle drei muessen mit, sonst bleibt die Haelfte schwarz:

  * .cls-3  fill  - Helmzeichnung, die beiden Aehren, die Augen
  * .cls-1  stroke - die 7px-Kontur der Glieder
  * die zwei <path> OHNE class - Koerperkontur und Strohlinien in einem Pfad,
    ohne fill-Attribut, also per SVG-Vorgabe schwarz. Ein Ersetzen der
    Farbwerte allein laesst diese beiden unberuehrt, und sie sind der groesste
    Schwarzanteil des ganzen Bildes.

Die Augen bleiben dunkel. Cremefarbene Augen auf Gold sind keine Augen mehr,
die Figur wirkt blind. Sie sind die einzigen <circle>-Elemente, also sauber
adressierbar, ohne den Rest der Klasse anzufassen.

Nur Binaermodus, wie fuer jede Datei in einem Repo-Baum.
"""
import os
import re
import sys

TINTE_ALT = "#1d1d1b"


def faerben(quelle, ziel, tinte, auge=TINTE_ALT):
    with open(quelle, "rb") as fh:
        svg = fh.read().decode("utf-8")

    # Die klassenlosen Pfade zuerst: ein explizites fill davor, sonst greift
    # die SVG-Vorgabe Schwarz und kein Ersetzen der Welt erreicht sie.
    svg = svg.replace("<path d=", f'<path fill="{tinte}" d=')

    # Danach die benannte Tinte, fill wie stroke in einem Zug.
    svg = svg.replace(TINTE_ALT, tinte)

    # Die Augen zurueck ins Dunkle, und zwar per style, nicht per fill. Ein
    # fill-Attribut ist eine Praesentationsangabe und steht in der
    # SVG-Kaskade UNTER einer Regel aus dem <style>-Block, also hat .cls-3 das
    # Attribut ueberstimmt und die Augen blieben cremefarben. Inline style
    # gewinnt.
    svg = re.sub(r'(<circle class="cls-3")', rf'\1 style="fill:{auge}"', svg)

    with open(ziel, "wb") as fh:
        fh.write(svg.encode("utf-8"))
    return ziel


if __name__ == "__main__":
    quelle, ziel, tinte = sys.argv[1], sys.argv[2], sys.argv[3]
    auge = sys.argv[4] if len(sys.argv) > 4 else TINTE_ALT
    print(faerben(quelle, ziel, tinte, auge), os.path.getsize(ziel), "B")
