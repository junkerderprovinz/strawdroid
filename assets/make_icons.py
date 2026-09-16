# -*- coding: utf-8 -*-
"""Icons fuer StrawDroid und TrialYard, transparent, auf jdps Wunsch.

Beide Marken werden in ein QUADRAT von 512 Kanten gesetzt und darin nach ihrer
laengeren Achse skaliert, nicht nach der Breite. Der Android-Roboter ist hoch,
der Muelleimer auch: nach der Breite ausgerichtet stuenden sie oben und unten
ueber. Ein kleiner Rand bleibt, weil Unraid die Kachel beschneidet und eine
Marke, die die Kante beruehrt, angeschnitten aussieht.
"""
import io
import os
import subprocess
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

    Ohne das entscheidet der Leerraum der Quelldatei ueber die Groesse, und
    zwei Marken aus zwei Quellen kommen unterschiedlich gross heraus, obwohl
    beide 'auf 512 skaliert' wurden.
    """
    im = Image.open(pfad).convert("RGBA")
    kasten = im.getchannel("A").getbbox()
    return im.crop(kasten) if kasten else im


# --- StrawDroid: der ganze Roboter -----------------------------------------
sk = quadrat(beschnitten(os.path.join(HIER, "android-robot.png")))
sk.save(os.path.join(HIER, "strawdroid-icon.png"))

# --- TrialYard: der Muelleimer vom Desktop ----------------------------------
# Die SVG traegt keine Farbe, also ist ihr fill schwarz. Auf Unraids dunkler
# Kachel waere das unsichtbar, deshalb wird sie eingefaerbt - und zwar in das
# Gold, das die bisherige Crucible-Kachel schon trug, damit die Umbenennung
# nicht auch noch die Farbe wechselt.
GOLD = (212, 168, 83)
ty_pfad = os.path.join(HIER, "trialyard-raw.png")
if not os.path.exists(ty_pfad):
    sys.exit("trialyard-raw.png fehlt - erst die SVG rastern")
eimer = beschnitten(ty_pfad)
farbig = Image.new("RGBA", eimer.size, GOLD + (0,))
farbig.putalpha(eimer.getchannel("A"))
# Volle Deckkraft nur dort, wo die Vorlage Tinte hat.
farbig = Image.composite(Image.new("RGBA", eimer.size, GOLD + (255,)),
                         Image.new("RGBA", eimer.size, (0, 0, 0, 0)),
                         eimer.getchannel("A"))
quadrat(farbig).save(os.path.join(HIER, "trialyard-icon.png"))

print("beide Icons geschrieben")
