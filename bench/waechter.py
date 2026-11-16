"""Qualitäts-Wächter: erkennt kaputte Ausgaben, bevor Durchsatzwerte zählen.

Anlass: Ein Community-Test sah GLM-5.3-Flash auf SM120 schnell laufen, aber jede
Antwort lief in eine Endlosschleife („locklock…“). Hohe tok/s sind dann wertlos.

Geprüft wird jede Antwort auf:
  leer               kein Inhalt und kein Denk-Text
  wiederholung       Anteil wiederholter Wort-4-Gramme (normaler Text: < 0,2)
  schleife           ein kurzes Muster (1–40 Zeichen), das sich am Stück oft wiederholt
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Schwellwerte: ab wann eine Antwort als kaputt gilt
# ---------------------------------------------------------------------------
MAX_WIEDERHOLUNG = 0.5  # mehr als die Hälfte aller 4-Gramme doppelt
MIN_WOERTER_FUER_WIEDERHOLUNG = 60  # kurze Antworten wiederholen sich natürlicherweise
MAX_SCHLEIFE = 12  # Muster öfter als 12-mal am Stück

SCHLEIFE = re.compile(r"(.{1,40}?)\1{" + str(MAX_SCHLEIFE) + r",}", re.S)


# ---------------------------------------------------------------------------
# Kennzahlen eines Textes
# ---------------------------------------------------------------------------
def wiederholungs_anteil(text: str) -> float:
    woerter = text.split()
    if len(woerter) < 4:
        return 0.0
    gramme = [tuple(woerter[i : i + 4]) for i in range(len(woerter) - 3)]
    return 1 - len(set(gramme)) / len(gramme)


def laengste_schleife(text: str) -> str:
    """Das sich wiederholende Muster, falls eines MAX_SCHLEIFE-mal am Stück vorkommt.

    Muster ohne Buchstaben oder Ziffern zählen nicht: Trennlinien (=====),
    Einrückungen und Markdown-Tabellen sind normal.
    """
    for treffer in SCHLEIFE.finditer(text):
        if any(zeichen.isalnum() for zeichen in treffer.group(1)):
            return treffer.group(1)
    return ""


def analyse(inhalt: str, denken: str = "") -> dict:
    gesamt = (denken + "\n" + inhalt).strip()
    woerter = len(gesamt.split())
    anteil = wiederholungs_anteil(gesamt)
    muster = laengste_schleife(gesamt[-20000:])  # Schleifen zeigen sich am Ende
    gruende = []
    if not gesamt:
        gruende.append("leer")
    if woerter >= MIN_WOERTER_FUER_WIEDERHOLUNG and anteil > MAX_WIEDERHOLUNG:
        gruende.append(f"wiederholung {anteil:.2f}")
    if muster:
        gruende.append(f"schleife {muster[:20]!r}")
    return {"woerter": woerter, "wiederholung": round(anteil, 3), "kaputt": bool(gruende), "gruende": gruende}


def ist_kaputt(inhalt: str, denken: str = "") -> bool:
    return analyse(inhalt, denken)["kaputt"]
