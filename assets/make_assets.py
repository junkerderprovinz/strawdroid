# -*- coding: utf-8 -*-
"""Icon und Hintergrund fuer StrawKnight.

Das Icon liegt auf einer SOLIDEN Flaeche, nie auf Transparenz: Unraids
Kachelgitter zeichnet hinter dem Bild eine eigene Flaeche, und ein
freigestelltes Logo nimmt dort mal die helle, mal die dunkle an.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = "D:/github/strawknight/assets"
GH = "D:/github/strawknight/.github/assets"
os.makedirs(ZIEL, exist_ok=True)
os.makedirs(GH, exist_ok=True)

GRUND = (18, 18, 18)          # Unraid-dunkel, die Hauskonvention fuer Icons
TAFEL = (22, 22, 22)          # Carbon-Hintergrund fuer die Schreibtischflaeche
GRUEN = (61, 220, 132)

robot = Image.open(os.path.join(HIER, "android.png")).convert("RGBA")


def icon(kante):
    """Der Roboterkopf auf einer soliden Kachel, mit Luft ringsum."""
    bild = Image.new("RGBA", (kante, kante), GRUND + (255,))
    # Achtzig Prozent Breite: der Kopf ist breit und flach, gemessen 913 auf
    # 512. An der Hoehe ausgerichtet waere er winzig, an der Breite ohne Rand
    # klebt er an den Kanten.
    breite = int(kante * 0.72)
    hoehe = int(breite * robot.height / robot.width)
    skaliert = robot.resize((breite, hoehe), Image.LANCZOS)
    bild.alpha_composite(skaliert, ((kante - breite) // 2, (kante - hoehe) // 2))
    return bild


icon(512).save(os.path.join(ZIEL, "icon.png"))
icon(512).save(os.path.join(GH, "icon.png"))


def schrift(groesse):
    for pfad in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(pfad):
            return ImageFont.truetype(pfad, groesse)
    return ImageFont.load_default()


def hintergrund(breite=1920, hoehe=1080):
    """Die Flaeche, auf der der Emulator sitzt.

    Der Satz unten steht da, weil die halbe Minute vor dem ersten Bild sonst
    ein schwarzes Rechteck ist, und ein schwarzes Rechteck ist von einem
    kaputten Container nicht zu unterscheiden.
    """
    bild = Image.new("RGB", (breite, hoehe), TAFEL)
    zeichner = ImageDraw.Draw(bild)

    marke = robot.resize((260, int(260 * robot.height / robot.width)), Image.LANCZOS)
    bild.paste(marke, ((breite - marke.width) // 2, hoehe // 2 - 190), marke)

    titel = schrift(46)
    zeile = schrift(24)
    # Der Satz muss zu JEDEM Zeitpunkt stimmen. Die erste Fassung sagte
    # "Android startet gerade" und blieb danach fuer immer stehen, also
    # behauptete sie den Rest der Sitzung etwas Falsches, sichtbar neben einem
    # laufenden Geraet. Ein Hinweis, der nur eine halbe Minute lang wahr ist,
    # ist danach eine Fehlinformation an prominenter Stelle.
    for text, font, farbe, y in (
        ("StrawKnight", titel, (200, 200, 200), hoehe // 2 - 40),
        ("Das Geraetefenster erscheint hier, sobald der Emulator hochgefahren ist.",
         zeile, (120, 120, 120), hoehe // 2 + 30),
        ("Rechtsklick auf die Flaeche fuer ein Terminal.",
         zeile, (95, 95, 95), hoehe // 2 + 70),
    ):
        w = zeichner.textlength(text, font=font)
        zeichner.text(((breite - w) / 2, y), text, font=font, fill=farbe)

    return bild


hintergrund().save(os.path.join(ZIEL, "wallpaper.png"))
print("icon.png und wallpaper.png geschrieben")
