# -*- coding: utf-8 -*-
"""Hintergrundbild fuer StrawKnights Selkies-Flaeche.

Der Satz auf der Flaeche steht da, weil die halbe Minute vor dem ersten Bild
sonst ein schwarzes Rechteck ist, und ein schwarzes Rechteck ist von einem
kaputten Container nicht zu unterscheiden.

**Englisch, nicht deutsch.** Bis 2026-09-13 stand hier deutscher Text mit
Umlaut-Umschreibung ("Das Geraetefenster erscheint hier..."), sichtbar auf
jedem Screenshot eines oeffentlichen Repos, dessen gesamte Doku englisch ist.
Aufgefallen ist es erst, als der erste Screenshot fuer das README gemacht wurde.

Das Icon erzeugt dieses Skript nicht mehr. Marke und Kachel kommen aus
`strawknight.svg` ueber `.github/assets/gen-banner.mjs` beziehungsweise die
Icon-Ableitung daraus, damit Banner, Kachel und Flaeche dieselbe Zeichnung
zeigen. Die frueheren Fassungen lasen `android.png`, eine Datei, die nie im
Repo lag: das Skript lief damit bei niemandem ausser seinem Autor.

    python assets/make_assets.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

HIER = os.path.dirname(os.path.abspath(__file__))

TAFEL = (22, 22, 22)          # Carbon-Grund, derselbe Ton wie xsetroot faellt zurueck

# Absichtlich gross: Selkies zieht die Flaeche auf die Groesse des Browserfensters,
# und ein hochskaliertes Bild wird weich. 2560 auf 1440 deckt jedes uebliche
# Fenster ab, ohne dass die Datei ins Gewicht faellt.
BREITE, HOEHE = 2560, 1440


def schrift(groesse):
    for pfad in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(pfad):
            return ImageFont.truetype(pfad, groesse)
    return ImageFont.load_default()


def hintergrund(breite=BREITE, hoehe=HOEHE):
    bild = Image.new("RGB", (breite, hoehe), TAFEL)
    zeichner = ImageDraw.Draw(bild)

    marke = Image.open(os.path.join(HIER, "icon.png")).convert("RGBA")
    kante = 300
    f = min(kante / marke.width, kante / marke.height)
    m = marke.resize((int(marke.width * f), int(marke.height * f)), Image.LANCZOS)
    bild.paste(m, ((breite - m.width) // 2, hoehe // 2 - 250), m)

    titel = schrift(52)
    zeile = schrift(28)
    # Der Satz muss zu JEDEM Zeitpunkt stimmen. Die erste Fassung sagte
    # "Android is starting" und blieb danach fuer immer stehen, also behauptete
    # sie den Rest der Sitzung etwas Falsches, sichtbar neben einem laufenden
    # Geraet. Ein Hinweis, der nur eine halbe Minute lang wahr ist, ist danach
    # eine Fehlinformation an prominenter Stelle.
    for text, font, farbe, y in (
        ("StrawKnight", titel, (200, 200, 200), hoehe // 2 + 40),
        ("The device window appears here once the emulator has booted.",
         zeile, (120, 120, 120), hoehe // 2 + 120),
        ("Right-click the desktop for a terminal.",
         zeile, (95, 95, 95), hoehe // 2 + 168),
    ):
        w = zeichner.textlength(text, font=font)
        zeichner.text(((breite - w) / 2, y), text, font=font, fill=farbe)

    return bild


if __name__ == "__main__":
    ziel = os.path.join(HIER, "wallpaper.png")
    hintergrund().save(ziel)
    print(f"wallpaper.png geschrieben ({os.path.getsize(ziel)} B)")
