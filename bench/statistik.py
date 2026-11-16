"""Kennzahlen aus Messreihen: Perzentile, Mittelwert, Minimum, Maximum.

Perzentile mit linearer Interpolation (wie numpy.percentile, Standard). Leere
Reihen und None-Werte werden sauber behandelt, damit ein fehlgeschlagener
Messpunkt nicht die ganze Auswertung abbricht.
"""

from __future__ import annotations

from collections.abc import Iterable


# ---------------------------------------------------------------------------
# Einzelnes Perzentil
# ---------------------------------------------------------------------------
def perzentil(werte: Iterable[float | None], p: float) -> float | None:
    """p zwischen 0 und 100. Liefert None für eine leere Reihe."""
    reihe = sorted(w for w in werte if w is not None)
    if not reihe:
        return None
    if len(reihe) == 1:
        return reihe[0]
    position = (len(reihe) - 1) * p / 100
    unten = int(position)
    oben = min(unten + 1, len(reihe) - 1)
    anteil = position - unten
    return reihe[unten] + (reihe[oben] - reihe[unten]) * anteil


# ---------------------------------------------------------------------------
# Zusammenfassung einer Reihe
# ---------------------------------------------------------------------------
def runde(wert: float | None, stellen: int = 3) -> float | None:
    return None if wert is None else round(wert, stellen)


def kennzahlen(werte: Iterable[float | None], stellen: int = 3) -> dict:
    reihe = [w for w in werte if w is not None]
    if not reihe:
        return {"anzahl": 0}
    return {
        "anzahl": len(reihe),
        "mittel": runde(sum(reihe) / len(reihe), stellen),
        "min": runde(min(reihe), stellen),
        "p10": runde(perzentil(reihe, 10), stellen),
        "p50": runde(perzentil(reihe, 50), stellen),
        "p90": runde(perzentil(reihe, 90), stellen),
        "p99": runde(perzentil(reihe, 99), stellen),
        "max": runde(max(reihe), stellen),
    }
