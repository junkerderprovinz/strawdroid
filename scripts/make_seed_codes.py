# /// script
# requires-python = ">=3.10"
# dependencies = ["segno==1.6.6", "python-barcode[images]==0.15.1"]
# ///
"""Barcodes and QR codes for `sk seed` and `sk camera`, written to rootfs/defaults/seed/codes.

Run with `uv run scripts/make_seed_codes.py`. Every code points nowhere real: the
domain is example.org, the Wi-Fi network does not exist and the one-time
password secret is the well-known RFC 4648 example. Through the emulated camera
only the QR codes are read; the linear codes are for apps that import a picture.
"""

from pathlib import Path

import barcode
import segno
from barcode.writer import ImageWriter
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "rootfs" / "defaults" / "seed" / "codes"

QR = {
    "qr-text": "StrawDroid test code",
    "qr-url": "https://example.org/strawdroid",
    "qr-wifi": "WIFI:T:WPA;S:StrawDroid-Test;P:not-a-real-network;;",
    "qr-otp": "otpauth://totp/StrawDroid:tester@example.org?secret=JBSWY3DPEHPK3PXP&issuer=StrawDroid",
    "qr-contact": "BEGIN:VCARD\nVERSION:3.0\nFN:Anna Gruber\nTEL:+12015550101\nEMAIL:anna.gruber@example.org\nEND:VCARD",
}

LINEAR = {
    "ean13": ("ean13", "400638133393"),
    "code128": ("code128", "STRAWDROID-128"),
}

# As the camera's picture (-camera-back imagefile:), a 1280x720 sheet reaches a
# portrait preview as a strip about 320 pixels wide around x=360, not around its
# middle, so each code sits there and stays smaller than the strip.
SHEET = (1280, 720)
CENTRE = (360, 360)
QR_BOX = (220, 220)
LINEAR_BOX = (300, 200)


def on_sheet(code: Image.Image, box: tuple[int, int]) -> Image.Image:
    scale = min(box[0] / code.width, box[1] / code.height)
    code = code.resize((round(code.width * scale), round(code.height * scale)), Image.Resampling.NEAREST)
    sheet = Image.new("RGB", SHEET, "white")
    sheet.paste(code, (CENTRE[0] - code.width // 2, CENTRE[1] - code.height // 2))
    return sheet


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in QR.items():
        path = OUT / f"{name}.png"
        segno.make(data, error="m").save(path, scale=12, border=4)
        on_sheet(Image.open(path).convert("RGB"), QR_BOX).save(path)
    for name, (kind, data) in LINEAR.items():
        code = barcode.get(kind, data, writer=ImageWriter())
        path = Path(code.save(str(OUT / name), options={"module_height": 18, "quiet_zone": 8}))
        on_sheet(Image.open(path).convert("RGB"), LINEAR_BOX).save(path)
    for path in sorted(OUT.iterdir()):
        print(path.relative_to(OUT.parent.parent.parent.parent))


if __name__ == "__main__":
    main()
