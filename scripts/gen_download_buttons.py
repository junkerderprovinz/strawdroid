"""Generate the README's download buttons from one template.

From a template, because hand-drawn buttons are chances to type one number
differently, and the point of a row of them is that they look like one control
repeated.

THE GEOMETRY is ArrowLoop's, so the buttons here and there are the same object:
245.3 tall with rx 38.2, which is the Buy Me a Coffee button's own height and
corner, and 720 wide rather than that button's 841.9 because at 841.9 a third
of the face sits empty next to the longest word.

THE COLOUR is the thing's own and there is no outline (jdp: "die butotns sollen
keine rahmenliniehaben und farbig sein"). A filled shape in a colour somebody
already associates with the thing does the work an outline was doing, faster:
the eye finds "the blue one" before it reads the word.

WHAT A CONTAINER REPO ACTUALLY OFFERS is not a bundle, it is an image. The
older rule said container repos get no download row at all, on the grounds that
a button pointing at a `docker run` line is not a download. That was right
while there was no image to point at. There is one now, so the first button
points at the published package, which is the thing a reader wants.

The second button is the source archive, and it is labelled as exactly that.
GitHub attaches "Source code (zip)" to every release automatically: it is the
whole repository at that tag, not the Dockerfile alone. Calling it anything
else on the button would send somebody looking for an image to a folder of
YAML.

THE MARKS are Font Awesome Free (icons CC BY 4.0). Each is a trademark of its
owner and is used the one way a trademark may be used without permission: to
name the thing it points at. Both buttons link to that thing, the marks are
unmodified, and nothing here claims endorsement by Docker or GitHub.

Run from anywhere:  python scripts/gen_download_buttons.py
Writes .github/assets/download-buttons/*.svg, which are committed.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", ".github", "assets", "download-buttons")
BRANDS = os.path.join(HERE, "brand-paths")

W, H, R = 720.0, 245.3, 38.2

GLYPH = 112.0
GX, GY = 78.0, (H - GLYPH) / 2

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
  <title>{alt}</title>
  <rect width="{w}" height="{h}" rx="{r}" ry="{r}" fill="{bg}"/>
  <g transform="translate({gx} {gy}) scale({scale})" fill="{ink}">
    <path d="{path}"/>
  </g>
  <text x="238" y="110" font-family="{font}" font-size="82" font-weight="700" fill="{ink}">{head}</text>
  <text x="240" y="180" font-family="{font}" font-size="50" font-weight="400" fill="{ink}" fill-opacity="0.72">{sub_text}</text>
</svg>
"""

# slug, brand file, background, ink, heading, second line, accessible name
#
# GitHub's own colour is black, and a black button without an outline vanishes
# into GitHub's dark theme, exactly as a black macOS button did in ArrowLoop's
# row. The slate below stays visible on both themes.
BUTTONS = [
    ("docker-image", "docker", "#1d63ed", "#ffffff",
     "Docker", "ghcr.io image", "Pull the container image from GHCR"),
    ("source-zip", "github", "#4d5562", "#ffffff",
     "Source", "zip archive", "Download the source archive for this release"),
]


def brand(name):
    """Path data plus the viewBox width and height it was drawn in."""
    with open(os.path.join(BRANDS, name + ".txt"), "rb") as fh:
        path = fh.read().decode("utf-8").strip()
    with open(os.path.join(BRANDS, name + ".box.txt"), "rb") as fh:
        box = [float(v) for v in fh.read().decode("utf-8").split()]
    return path, box[2], box[3]


def main():
    os.makedirs(OUT, exist_ok=True)
    for slug, mark, bg, ink, head, sub, alt in BUTTONS:
        path, bw, bh = brand(mark)
        # Scale on the LONGER axis so two marks of different proportions end up
        # the same optical size. Docker's is 640 wide by 512 tall, GitHub's 496
        # square; scaling on width alone would leave the square one oversized.
        scale = GLYPH / max(bw, bh)
        # Re-centre horizontally: a wide mark scaled on its width sits left of
        # a square one at the same x.
        gx = GX + (GLYPH - bw * scale) / 2
        gy = GY + (GLYPH - bh * scale) / 2
        svg = TEMPLATE.format(w=W, h=H, r=R, bg=bg, ink=ink, gx=gx, gy=gy,
                              scale=scale, path=path, font=FONT, head=head,
                              sub_text=sub, alt=alt)
        ziel = os.path.join(OUT, slug + ".svg")
        with open(ziel, "wb") as fh:
            fh.write(svg.encode("utf-8"))
        print(f"{slug}.svg  {os.path.getsize(ziel)} B")


if __name__ == "__main__":
    main()
