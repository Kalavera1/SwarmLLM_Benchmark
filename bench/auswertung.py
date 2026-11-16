"""Vergleichstabelle: die wichtigsten Kennzahlen je Profil aus den letzten Ergebnissen.

Liest pro Profil und Block die jüngste Ergebnisdatei (results/<profil>/<block>/)
und baut daraus eine Markdown-Tabelle. Rohdaten (results/raw/) bleiben außen vor.
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Zeilen der Tabelle: (Überschrift, Block, Pfad in den Kennzahlen)
# ---------------------------------------------------------------------------
ZEILEN = [
    ("Integration bestanden", "integration", ("bestanden",)),
    ("Wächter bestanden", "waechter", ("bestanden",)),
    ("TTFT kalt 128k (s)", "prefill", ("kennzahlen", "ttft_kalt_128k_s")),
    ("TTFT kalt 500k (s)", "prefill", ("kennzahlen", "ttft_kalt_500k_s")),
    ("TTFT warm 500k (s)", "prefill", ("kennzahlen", "ttft_warm_500k_s")),
    ("tok/s 1 Nutzer", "decode", ("kennzahlen", "pro_nutzer_tok_s_p50_bei_1")),
    ("tok/s pro Nutzer bei 16", "decode", ("kennzahlen", "pro_nutzer_tok_s_p50_bei_16")),
    ("tok/s gesamt bei 16", "decode", ("kennzahlen", "gesamt_tok_s_bei_16")),
    ("Nadel 500k gefunden", "nadel", ("kennzahlen", "500k_gefunden")),
    ("Nutzer mit Zielwerten (Ziel 30)", "lastmix", ("kennzahlen", "max_nutzer_mit_zielen")),
    ("Agent Erfolgsquote", "agent", ("kennzahlen", "erfolgsquote")),
    ("Bilder richtig", "bilder", ("kennzahlen", "richtig")),
    ("ABAP Kriterien-Quote", "abap", ("kennzahlen", "kriterien_quote")),
]


# ---------------------------------------------------------------------------
# Jüngste Ergebnisdatei je Profil und Block
# ---------------------------------------------------------------------------
def juengste(ordner: Path, profil: str, block: str) -> dict | None:
    dateien = sorted((ordner / profil / block).glob("*.json"))
    if not dateien:
        return None
    return json.loads(dateien[-1].read_text(encoding="utf-8"))


def wert(daten: dict | None, pfad: tuple[str, ...]):
    for schluessel in pfad:
        if not isinstance(daten, dict):
            return None
        daten = daten.get(schluessel)
    return daten


def zelle(w) -> str:
    if w is None:
        return "–"
    if w is True:
        return "ja"
    if w is False:
        return "**nein**"
    return str(w)


# ---------------------------------------------------------------------------
# Tabelle bauen
# ---------------------------------------------------------------------------
def tabelle(ordner: Path, nur_profil: str | None = None) -> str:
    profile = sorted(p.name for p in ordner.iterdir() if p.is_dir() and p.name != "raw") if ordner.is_dir() else []
    if nur_profil:
        profile = [p for p in profile if p == nur_profil]
    if not profile:
        return "Keine Ergebnisse gefunden."

    kopf = "| Kennzahl | " + " | ".join(profile) + " |"
    trenner = "|---|" + "---|" * len(profile)
    zeilen = [kopf, trenner]
    for titel, block, pfad in ZEILEN:
        werte = [zelle(wert(juengste(ordner, p, block), pfad)) for p in profile]
        zeilen.append(f"| {titel} | " + " | ".join(werte) + " |")

    kosten = []
    for p in profile:
        summe = 0.0
        for datei in (ordner / p).glob("*/*.json"):
            summe += json.loads(datei.read_text(encoding="utf-8")).get("kosten_usd") or 0.0
        kosten.append(f"{summe:.2f}")
    zeilen.append("| Messkosten gesamt ($) | " + " | ".join(kosten) + " |")
    return "\n".join(zeilen)
