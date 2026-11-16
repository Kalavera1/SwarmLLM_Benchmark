"""Erzeugt Testbilder mit bekannter Antwort, ohne Pillow (nur zlib und struct).

Motiv: farbige Quadrate auf weißem Grund, ohne Überlappung. Die Frage lautet
z. B. „Wie viele rote Quadrate siehst du?“ – die richtige Antwort steht fest.
Die Bilder gehen als data-URL (base64-PNG) direkt in die Anfrage.
"""

from __future__ import annotations

import base64
import random
import struct
import zlib

# ---------------------------------------------------------------------------
# Farben (RGB) mit deutschem Namen für die Frage
# ---------------------------------------------------------------------------
FARBEN = {
    "rot": (220, 30, 30),
    "blau": (30, 70, 220),
    "grün": (30, 160, 60),
    "gelb": (235, 200, 20),
}
WEISS = (255, 255, 255)


# ---------------------------------------------------------------------------
# PNG schreiben (Format: Signatur, IHDR, IDAT, IEND)
# ---------------------------------------------------------------------------
def _chunk(typ: bytes, daten: bytes) -> bytes:
    return struct.pack(">I", len(daten)) + typ + daten + struct.pack(">I", zlib.crc32(typ + daten) & 0xFFFFFFFF)


def png(breite: int, hoehe: int, pixel: list[bytearray]) -> bytes:
    """pixel: eine bytearray pro Zeile mit RGB-Werten (3 Byte pro Pixel)."""
    roh = b"".join(b"\x00" + bytes(zeile) for zeile in pixel)  # Filter 0 = keiner
    kopf = struct.pack(">IIBBBBB", breite, hoehe, 8, 2, 0, 0, 0)  # 8 Bit, RGB
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", kopf) + _chunk(b"IDAT", zlib.compress(roh, 6)) + _chunk(b"IEND", b"")


# ---------------------------------------------------------------------------
# Motiv: Quadrate auf einem Raster, damit sie sich nie überlappen
# ---------------------------------------------------------------------------
def quadrate_bild(anzahl: dict[str, int], seed: int, groesse: int = 768) -> bytes:
    """anzahl: Farbe -> Anzahl Quadrate, z. B. {"rot": 3, "blau": 2}."""
    zufall = random.Random(seed)
    raster = 4  # 4x4 Felder = höchstens 16 Quadrate
    feld = groesse // raster
    felder = [(x, y) for x in range(raster) for y in range(raster)]
    zufall.shuffle(felder)
    gesamt = sum(anzahl.values())
    if gesamt > len(felder):
        raise ValueError(f"Höchstens {len(felder)} Quadrate möglich, verlangt: {gesamt}")

    pixel = [bytearray(WEISS * groesse) for _ in range(groesse)]
    belegt = iter(felder)
    for farbe, menge in anzahl.items():
        rgb = bytes(FARBEN[farbe])
        for _ in range(menge):
            fx, fy = next(belegt)
            seite = zufall.randint(feld // 2, feld - 16)
            x0 = fx * feld + zufall.randint(4, feld - seite - 4)
            y0 = fy * feld + zufall.randint(4, feld - seite - 4)
            for y in range(y0, y0 + seite):
                pixel[y][x0 * 3 : (x0 + seite) * 3] = rgb * seite
    return png(groesse, groesse, pixel)


def data_url(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode()


def bild_inhalt(png_bytes: bytes) -> dict:
    """Bildteil einer Chat-Nachricht im OpenAI-Format."""
    return {"type": "image_url", "image_url": {"url": data_url(png_bytes)}}
