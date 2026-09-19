# -*- coding: utf-8 -*-
"""Icons fuer StrawDroid und TrialYard, transparent.

Beide Marken werden in ein Quadrat von 512 Kanten gesetzt und nach ihrer
laengeren Achse skaliert, weil Roboter und Muelleimer hoeher als breit sind. Ein
kleiner Rand bleibt, weil Unraid die Kachel beschneidet und eine Marke an der
Kante angeschnitten aussieht.
"""
import os
import sys
from PIL import Image

HIER = os.path.dirname(os.path.abspath(__file__))
KANTE = 512
ANTEIL = 0.86  # wieviel der Kachel die Marke fuellen darf


def quadrat(marke):
    """Die Marke mittig in eine transparente Kachel, nach der langen Achse."""
    platz = int(KANTE * ANTEIL)
    faktor = min(platz / marke.width, platz / marke.height)
    breite = max(1, int(marke.width * faktor))
    hoehe = max(1, int(marke.height * faktor))
    skaliert = marke.resize((breite, hoehe), Image.LANCZOS)
    bild = Image.new("RGBA", (KANTE, KANTE), (0, 0, 0, 0))
    bild.alpha_composite(skaliert, ((KANTE - breite) // 2, (KANTE - hoehe) // 2))
    return bild


def beschnitten(pfad):
    """Auf die Tinte beschneiden, bevor skaliert wird.

    Sonst entscheidet der Leerraum der Quelldatei ueber die Groesse, und zwei
    Marken aus zwei Quellen kommen unterschiedlich gross heraus.
    """
    im = Image.open(pfad).convert("RGBA")
    kasten = im.getchannel("A").getbbox()
    return im.crop(kasten) if kasten else im


sk = quadrat(beschnitten(os.path.join(HIER, "android-robot.png")))
sk.save(os.path.join(HIER, "strawdroid-icon.png"))

# Die SVG des Muelleimers traegt keine Farbe, ist also schwarz und waere auf
# Unraids dunkler Kachel unsichtbar.
GOLD = (212, 168, 83)
ty_pfad = os.path.join(HIER, "trialyard-raw.png")
if not os.path.exists(ty_pfad):
    sys.exit("trialyard-raw.png fehlt, erst die SVG rastern")
eimer = beschnitten(ty_pfad)
# Volle Deckkraft nur dort, wo die Vorlage Tinte hat.
farbig = Image.composite(Image.new("RGBA", eimer.size, GOLD + (255,)),
                         Image.new("RGBA", eimer.size, (0, 0, 0, 0)),
                         eimer.getchannel("A"))
quadrat(farbig).save(os.path.join(HIER, "trialyard-icon.png"))

print("beide Icons geschrieben")
