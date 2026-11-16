"""Zahl aus einer Modellantwort lesen ('ERGEBNIS: 2.825,00' oder 'ERGEBNIS: 2825.0').

Gemeinsam genutzt von den Blöcken agent und rechnen. Gilt die letzte
ERGEBNIS-Zeile, weil Modelle beim Nachdenken oft Zwischenergebnisse nennen.
"""

from __future__ import annotations

import re

MUSTER = re.compile(r"ERGEBNIS:\s*\**\s*(-?[\d.,]*\d)")
TAUSENDER_PUNKT = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


# ---------------------------------------------------------------------------
# Deutsche (2.825,50) und englische (2,825.50) Schreibweise erkennen
# ---------------------------------------------------------------------------
def zahl_normalisieren(zahl: str) -> float | None:
    if "," in zahl and "." in zahl:
        # das Zeichen weiter rechts ist das Dezimaltrennzeichen
        deutsch = zahl.rfind(",") > zahl.rfind(".")
        zahl = zahl.replace(".", "").replace(",", ".") if deutsch else zahl.replace(",", "")
    elif "," in zahl:
        zahl = zahl.replace(",", ".")
    elif TAUSENDER_PUNKT.match(zahl):
        # 10.955 ist im Deutschen zehntausend… – drei Nachkommastellen nennt kaum ein Modell
        zahl = zahl.replace(".", "")
    try:
        return float(zahl)
    except ValueError:
        return None


def ergebnis_lesen(text: str) -> float | None:
    treffer = MUSTER.findall(text)
    return zahl_normalisieren(treffer[-1]) if treffer else None
