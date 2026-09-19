# -*- coding: utf-8 -*-
"""Dunkelfassung der StrawDroid-Marke: die Tinte hell, die Augen dunkel.

Die Zeichnung ist fuer hellen Grund gebaut. Auf dem dunklen Grund des Emulators
sind die beiden frei stehenden Aehren oben reines #1d1d1b und unsichtbar, und
die Kontur liest sich als Luecke zwischen Gold und Grund. Umgefaerbt wird
deshalb die Tinte an allen drei Stellen, die sie traegt:

  * .cls-3 fill: Helmzeichnung, die beiden Aehren, die Augen
  * .cls-1 stroke: die 7px-Kontur der Glieder
  * die zwei <path> ohne class, Koerperkontur und Strohlinien, ohne
    fill-Attribut und damit per SVG-Vorgabe schwarz

Die Augen bleiben dunkel, weil cremefarbene Augen auf Gold blind wirken. Sie
sind die einzigen <circle>-Elemente und lassen sich so getrennt ansprechen.

Gelesen und geschrieben wird im Binaermodus, damit die Zeilenenden bleiben.
"""
import os
import re
import sys

TINTE_ALT = "#1d1d1b"


def faerben(quelle, ziel, tinte, auge=TINTE_ALT):
    with open(quelle, "rb") as fh:
        svg = fh.read().decode("utf-8")

    # Die klassenlosen Pfade brauchen ein explizites fill, sonst greift die
    # SVG-Vorgabe Schwarz.
    svg = svg.replace("<path d=", f'<path fill="{tinte}" d=')

    svg = svg.replace(TINTE_ALT, tinte)

    # Per style statt per fill, weil die .cls-3-Regel im <style>-Block ein
    # fill-Attribut ueberstimmt.
    svg = re.sub(r'(<circle class="cls-3")', rf'\1 style="fill:{auge}"', svg)

    with open(ziel, "wb") as fh:
        fh.write(svg.encode("utf-8"))
    return ziel


if __name__ == "__main__":
    quelle, ziel, tinte = sys.argv[1], sys.argv[2], sys.argv[3]
    auge = sys.argv[4] if len(sys.argv) > 4 else TINTE_ALT
    print(faerben(quelle, ziel, tinte, auge), os.path.getsize(ziel), "B")
