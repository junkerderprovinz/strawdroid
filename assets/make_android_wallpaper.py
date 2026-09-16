# -*- coding: utf-8 -*-
"""Android-Hintergrundbild fuer StrawDroid.

Die Marke allein auf einer Flaeche war das Problem: das dunkle Rechteck des
Emulators sah damit aus wie ein dunkles Rechteck mit einem Aufkleber. Der Grund
traegt hier deshalb selbst etwas, aber leise genug, dass App-Symbole darauf
noch lesbar bleiben. Vier Schichten, von hinten nach vorn:

  1. ein warmer Verlauf, oben fast schwarz, unten eine Spur waermer
  2. ein Strohgeflecht als Diagonalraster, knapp ueber der Sichtbarkeitsgrenze
  3. ein weicher Fackelschein hinter der Figur
  4. ein Aehrenfeld am unteren Rand, in dem die Figur steht

Gezeichnet wird auf dem doppelten Raster und am Ende heruntergerechnet. Duenne
Linien und die Spitzen der Aehren werden sonst treppig, und eine treppige Aehre
sieht aus wie ein Zeichenfehler, nicht wie Stroh.

    python wp.py <marke.png> <ziel.png>
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

BREITE, HOEHE = 1080, 2400
SS = 2                                  # Ueberabtastung
B, H = BREITE * SS, HOEHE * SS

GRUND_OBEN = (17, 16, 13)
GRUND_UNTEN = (30, 27, 20)

SCHEIN = (214, 176, 74)                 # Fackelton, warmes Gold
GEFLECHT = (236, 222, 175)
HALM = (232, 214, 156)

MARKE_ANTEIL = 0.60                     # Breite der Marke, Anteil der Bildbreite
MARKE_MITTE = 0.370                     # Hoehe der Markenmitte, Anteil der Bildhoehe


def verlauf():
    """Der Grund. Zeilenweise, weil ein Verlauf ueber 4800 Zeilen sonst bandet."""
    bild = Image.new("RGB", (1, H))
    zeichner = ImageDraw.Draw(bild)
    for y in range(H):
        t = y / (H - 1)
        # Quadratisch statt linear: die Waerme sammelt sich unten am Feld,
        # oben bleibt es ruhig genug fuer die Statusleiste.
        t = t * t
        zeichner.point(
            (0, y),
            fill=tuple(int(a + (b - a) * t) for a, b in zip(GRUND_OBEN, GRUND_UNTEN)),
        )
    return bild.resize((B, H), Image.BILINEAR)


def geflecht(bild):
    """Strohgeflecht: zwei Diagonalscharen, leicht ungleich, damit es gewebt
    aussieht und nicht wie ein Karo. Die Deckkraft ist Absicht so niedrig: auf
    einem Telefon liegt hier meist ein App-Symbol drueber."""
    schicht = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    z = ImageDraw.Draw(schicht)
    for schar, (dx, abstand, deckung, dicke) in enumerate(
        ((1, 96, 9, 3), (-1, 132, 6, 2))
    ):
        start = -H
        x = start
        while x < B + H:
            z.line(
                [(x, 0), (x + dx * H, H)],
                fill=GEFLECHT + (deckung,),
                width=dicke,
            )
            x += abstand
    bild.alpha_composite(schicht)


def schein(bild, mx, my, radius):
    """Fackelschein. Klein gezeichnet und hochskaliert: ein weicher Verlauf
    entsteht so in einem Bruchteil der Zeit und ist am Ende nicht zu
    unterscheiden."""
    n = 256
    kl = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    z = ImageDraw.Draw(kl)
    for i in range(n // 2, 0, -1):
        t = i / (n / 2)
        # Hoch potenziert: der Schein faellt schnell ab und steht als Kreis
        # nirgends als Kante im Bild.
        a = int(112 * (1 - t) ** 2.0)
        if a <= 0:
            continue
        z.ellipse([n / 2 - i, n / 2 - i, n / 2 + i, n / 2 + i], fill=SCHEIN + (a,))
    kl = kl.filter(ImageFilter.GaussianBlur(6))
    gr = kl.resize((radius * 2, radius * 2), Image.BICUBIC)
    bild.alpha_composite(gr, (int(mx - radius), int(my - radius)))


def halm(z, x, boden, hoehe, neigung, deckung):
    """Ein Halm: Stengel als Bogen, darauf paarweise Koerner, oben zwei Grannen.

    Bewusst kein Stroh-Klischee aus geraden Strichen. Ein gerader Strich liest
    sich als Gitter, erst die Kruemmung macht daraus ein Feld."""
    farbe = HALM + (deckung,)
    spitze_x = x + neigung
    spitze_y = boden - hoehe

    # Stengel, als Polygonzug aus einer quadratischen Bezierkurve.
    kx, ky = x + neigung * 0.35, boden - hoehe * 0.55
    punkte = []
    for i in range(15):
        t = i / 14
        px = (1 - t) ** 2 * x + 2 * (1 - t) * t * kx + t * t * spitze_x
        py = (1 - t) ** 2 * boden + 2 * (1 - t) * t * ky + t * t * spitze_y
        punkte.append((px, py))
    z.line(punkte, fill=farbe, width=max(2, int(hoehe / 260)))

    # Koerner am oberen Drittel, paarweise nach aussen.
    aehre = hoehe * 0.24
    paare = max(4, int(aehre / 46))
    for i in range(paare):
        t = i / max(1, paare - 1)
        # Entlang der Kurve, obere 30 Prozent.
        s = 0.76 + 0.24 * t
        px = (1 - s) ** 2 * x + 2 * (1 - s) * s * kx + s * s * spitze_x
        py = (1 - s) ** 2 * boden + 2 * (1 - s) * s * ky + s * s * spitze_y
        laenge = aehre * 0.20 * (1 - 0.45 * t)
        for seite in (-1, 1):
            wx = px + seite * laenge * 0.85
            wy = py - laenge * 0.75
            z.line([(px, py), (wx, wy)], fill=farbe, width=max(2, int(hoehe / 330)))

    # Zwei Grannen ueber der Spitze, sonst endet der Halm stumpf.
    for seite in (-1, 1):
        z.line(
            [(spitze_x, spitze_y), (spitze_x + seite * aehre * 0.16, spitze_y - aehre * 0.34)],
            fill=HALM + (max(1, deckung - 10),),
            width=2,
        )


# Die Hoehenbereiche der drei Reihen UEBERLAPPEN sich absichtlich. Getrennte
# Bereiche gaben jeder Reihe eine eigene, fast waagerechte Oberkante, und drei
# waagerechte Kanten uebereinander sehen aus wie ein Kamm. Erst der Ueberlapp
# franst die Silhouette aus.
#
# anzahl, h_min, h_max, deckung, unschaerfe
REIHEN = (
    (70, 0.22, 0.58, 28, 9),
    (46, 0.40, 0.82, 42, 4),
    (26, 0.58, 1.00, 60, 0),
)


def feld(bild, boden, tiefe, reihen):
    """Das Aehrenfeld. Drei Reihen: hinten klein und blass, vorn hoch und
    deutlicher. Die Staffelung macht die Tiefe, nicht die Anzahl.

    Die Reihen werden in zwei Aufrufen gezeichnet, hinten und vorn, damit die
    Marke dazwischen liegen kann. Wird alles vor die Marke gelegt, verschwinden
    ihre Beine; wird alles dahinter gelegt, schwebt sie ueber dem Feld statt
    darin zu stehen.

    Der Zufallsgeber wird bei jedem Aufruf gleich gesetzt und dann fuer die
    uebersprungenen Reihen leergedreht, sonst bekaeme der zweite Aufruf andere
    Halme als der erste und die Reihen passten nicht mehr zueinander."""
    schicht = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    zufall = random.Random(20260913)     # fest, damit zwei Laeufe dasselbe Bild geben
    for nr, (anzahl, h_min, h_max, deckung, unschaerfe) in enumerate(REIHEN):
        teil = Image.new("RGBA", (B, H), (0, 0, 0, 0))
        zt = ImageDraw.Draw(teil)
        for i in range(anzahl):
            x = zufall.uniform(-60, B + 60)
            hoehe = tiefe * zufall.uniform(h_min, h_max)
            neigung = zufall.uniform(-1, 1) * hoehe * 0.13
            deck = deckung + zufall.randint(-6, 6)
            # JEDER Zufallswert wird vor dem Ueberspringen gezogen, auch der
            # hier. Steht er im Argument des halm-Aufrufs, zieht der zweite
            # Aufruf ihn nicht, die Folge verschiebt sich, und die vordere
            # Reihe steht dann an anderen Stellen als im ersten Durchlauf.
            fuss = boden + zufall.uniform(0, 40)
            if nr not in reihen:
                continue                # gezogen, aber nicht gezeichnet
            halm(zt, x, fuss, hoehe, neigung, deck)
        if nr not in reihen:
            continue
        if unschaerfe:
            teil = teil.filter(ImageFilter.GaussianBlur(unschaerfe))
        schicht.alpha_composite(teil)
    bild.alpha_composite(schicht)


def strahlen(bild, mx, my, r_innen, r_aussen, anzahl=48):
    """Strohstrahlen als Wappenstrahl. Abwechselnd lang und kurz, sonst wird
    aus dem Strahlenkranz ein Zahnrad: gleich lange Speichen lesen sich als
    Mechanik, ungleiche als Licht."""
    schicht = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    z = ImageDraw.Draw(schicht)
    for i in range(anzahl):
        w = 2 * math.pi * i / anzahl
        lang = i % 2 == 0
        ra = r_aussen if lang else r_aussen * 0.62
        z.line(
            [(mx + math.cos(w) * r_innen, my + math.sin(w) * r_innen),
             (mx + math.cos(w) * ra, my + math.sin(w) * ra)],
            fill=SCHEIN + (34 if lang else 20,),
            width=8 if lang else 4,
        )
    # Weichgezeichnet, damit die Strahlen hinter der Marke nicht als Striche
    # gegen ihre Kontur stossen.
    bild.alpha_composite(schicht.filter(ImageFilter.GaussianBlur(5)))


def ring(bild, mx, my, radius):
    """Geflochtener Ring: zwei Reifen und dazwischen schraege Halme, die sich
    kreuzen. Das ist derselbe Flechtzopf, der der Figur um Brust und Huefte
    liegt, nur aufgezogen auf einen Kreis."""
    schicht = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    z = ImageDraw.Draw(schicht)
    dicke = int(B * 0.030)
    for r, deckung, breite in ((radius - dicke, 54, 4), (radius + dicke, 54, 4)):
        z.ellipse([mx - r, my - r, mx + r, my + r], outline=GEFLECHT + (deckung,),
                  width=breite)
    schritte = 132
    for i in range(schritte):
        w = 2 * math.pi * i / schritte
        w2 = w + 2 * math.pi / schritte * 2.1
        for a, b in (((radius - dicke, w), (radius + dicke, w2)),
                     ((radius + dicke, w), (radius - dicke, w2))):
            z.line([(mx + math.cos(a[1]) * a[0], my + math.sin(a[1]) * a[0]),
                    (mx + math.cos(b[1]) * b[0], my + math.sin(b[1]) * b[0])],
                   fill=GEFLECHT + (40,), width=3)
    bild.alpha_composite(schicht)


def vignette(bild):
    """Randabdunklung, und zwar nur der Rand.

    Die erste Fassung zeichnete einen kleinen Kreis und zog ihn auf das Bild:
    das Ergebnis war ein schwarzes Oval mitten im Bild, das den Fackelschein
    komplett verschluckt hat. Die Abdunklung muss ausserhalb eines Ovals
    liegen, das GROESSER ist als das Bild, sonst ist sie kein Rand, sondern ein
    Scheinwerfer. Deshalb 1.35: die Kurve setzt erst kurz vor der Kante ein."""
    n = 192
    ueber = 1.35
    kl = Image.new("L", (n, n), 255)
    z = ImageDraw.Draw(kl)
    for i in range(int(n / 2 * ueber), 0, -1):
        t = min(1.0, i / (n / 2 * ueber))
        z.ellipse([n / 2 - i, n / 2 - i, n / 2 + i, n / 2 + i],
                  fill=int(96 * t ** 3.2))
    maske = kl.resize((B, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))
    dunkel = Image.new("RGBA", (B, H), (8, 7, 5, 255))
    bild.paste(dunkel, (0, 0), maske)


def marke_laden(pfad, anteil):
    marke = Image.open(pfad).convert("RGBA")
    breite = int(B * anteil)
    hoehe = int(marke.height * breite / marke.width)
    return marke.resize((breite, hoehe), Image.LANCZOS), breite, hoehe


def feldbild(marke_pfad):
    """Nachtfeld: die Figur steht in einem Aehrenfeld, Fackelschein dahinter."""
    bild = verlauf().convert("RGBA")
    geflecht(bild)

    mitte_y = int(H * MARKE_MITTE)
    schein(bild, B // 2, mitte_y, int(B * 0.62))

    marke, breite, hoehe = marke_laden(marke_pfad, MARKE_ANTEIL)

    # Das Feld waechst vom UNTEREN BILDRAND nach oben, nicht von den Fuessen der
    # Figur. In der ersten Fassung stand seine Grundlinie knapp unter der Marke,
    # also standen die Halme links und rechts NEBEN ihr wie Kratzer, und die
    # untere Bildhaelfte blieb leer. Vom Rand aus gewachsen liegt es als
    # Vordergrund vor der Figur, und das untere Drittel traegt etwas.
    fuss = mitte_y + hoehe // 2
    boden, tiefe = H + int(H * 0.02), H - fuss + int(H * 0.10)

    feld(bild, boden, tiefe, reihen=(0, 1))
    bild.alpha_composite(marke, ((B - breite) // 2, mitte_y - hoehe // 2))
    feld(bild, boden, tiefe, reihen=(2,))

    vignette(bild)
    return bild.convert("RGB").resize((BREITE, HOEHE), Image.LANCZOS)


def wappenbild(marke_pfad):
    """Wappen: Strahlenkranz und geflochtener Ring, die Figur in der Mitte.

    Die Marke sitzt hier hoeher und kleiner als im Feldbild. Ein Wappen wird
    mittig gelesen, und der Ring braucht ringsum Luft, sonst schneidet ihn der
    Bildrand an und aus dem Kreis wird ein Bogen."""
    bild = verlauf().convert("RGBA")
    geflecht(bild)

    mitte_y = int(H * 0.42)
    schein(bild, B // 2, mitte_y, int(B * 0.58))
    # Die Strahlen beginnen INNERHALB des Rings und enden knapp vor der
    # Bildkante. Die erste Fassung liess sie bei 0.52 der Bildbreite
    # beginnen, also schon ausserhalb des linken und rechten Randes: sichtbar
    # blieben nur die nach oben und unten, und die gingen im Verlauf unter.
    strahlen(bild, B // 2, mitte_y, int(B * 0.20), int(B * 0.92))

    marke, breite, hoehe = marke_laden(marke_pfad, 0.50)
    ring(bild, B // 2, mitte_y, int(B * 0.46))
    bild.alpha_composite(marke, ((B - breite) // 2, mitte_y - hoehe // 2))

    vignette(bild)
    return bild.convert("RGB").resize((BREITE, HOEHE), Image.LANCZOS)


ARTEN = {"feld": feldbild, "wappen": wappenbild}


if __name__ == "__main__":
    art, marke, ziel = sys.argv[1], sys.argv[2], sys.argv[3]
    ARTEN[art](marke).save(ziel)
    print(art, ziel, os.path.getsize(ziel), "B")
