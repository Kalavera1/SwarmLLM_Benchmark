#!/usr/bin/env python3
"""Modell-Wache: sucht auf Hugging Face nach neuen Modellen aus der Beobachtungsliste.

Liest profiles/beobachten.txt (je Zeile: <autor> <suchbegriff>), fragt die
öffentliche Hugging-Face-Suche und meldet jedes Repo, das noch in keinem Profil
steht und noch nicht gemeldet wurde – mit Größe und Vorprüfung aus neu.py.

Läuft täglich als GitHub Action (.github/workflows/modell-wache.yml), die bei
Funden ein Issue anlegt. Geht auch von Hand auf dem Steuerrechner:
  python3 profiles/wache.py                       Funde anzeigen
  python3 profiles/wache.py --bekannt <datei>     Repos, die in <datei> vorkommen, überspringen
  python3 profiles/wache.py --markdown <datei>    Funde als Issue-Text schreiben (nur bei Funden)

Braucht keinen Token: Suche und Dateigrößen sind für öffentliche Repos frei.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neu  # noqa: E402 (Pfad muss vorher gesetzt sein)

BEOBACHTEN = neu.PROFILE_ORDNER / "beobachten.txt"


# ---------------------------------------------------------------------------
# Beobachtungsliste lesen: "<autor> <suchbegriff>", Kommentare mit #
# ---------------------------------------------------------------------------
def lies_liste(pfad: Path = BEOBACHTEN) -> list[tuple[str, str]]:
    eintraege = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#", 1)[0].strip()
        if zeile:
            autor, _, begriff = zeile.partition(" ")
            eintraege.append((autor.strip(), begriff.strip()))
    return eintraege


# ---------------------------------------------------------------------------
# Was schon bekannt ist: Repos aus allen Profilen (MODEL_QUELLE, MODEL_ID)
# und aus früheren Meldungen (Text der alten Issues)
# ---------------------------------------------------------------------------
def repos_in_profilen() -> set[str]:
    bekannt = set()
    for datei in neu.PROFILE_ORDNER.glob("*/profile.env"):
        for treffer in re.finditer(r"^(?:MODEL_QUELLE|MODEL_ID)=['\"]?([^'\"\s]+)", datei.read_text(), re.M):
            bekannt.add(treffer.group(1).lower())
    return bekannt


def ist_bekannt(repo: str, profile: set[str], alte_meldungen: str) -> bool:
    return repo.lower() in profile or repo.lower() in alte_meldungen.lower()


# ---------------------------------------------------------------------------
# Suchen: je Eintrag die neuesten Repos; Neues mit Vorprüfung versehen
# ---------------------------------------------------------------------------
def finde_neue(liste: list[tuple[str, str]], alte_meldungen: str = "") -> list[dict]:
    profile = repos_in_profilen()
    funde = []
    for autor, begriff in liste:
        for modell in neu.hf_suche(autor, begriff):
            repo = modell.get("id", "")
            if not repo or ist_bekannt(repo, profile, alte_meldungen):
                continue
            try:
                pruefung = neu.vorpruefung(repo)
            except (urllib.error.URLError, OSError, ValueError) as fehler:
                pruefung = {"gb": 0, "platz": f"Vorprüfung fehlgeschlagen ({fehler})", "bilder": None}
            funde.append({"repo": repo, "erstellt": (modell.get("createdAt") or "")[:10], "suche": begriff} | pruefung)
    return funde


# ---------------------------------------------------------------------------
# Ausgabe: Text für die Konsole oder Markdown für das Issue
# ---------------------------------------------------------------------------
def als_markdown(funde: list[dict]) -> str:
    bilder = {True: "ja", False: "nein", None: "unklar"}
    zeilen = [
        f"Die Modell-Wache hat {len(funde)} neue Repos auf Hugging Face gefunden "
        "(Beobachtungsliste: `profiles/beobachten.txt`).",
        "",
        "| Repo | erstellt | Gewichte (ganzes Repo) | Bilder | Vorprüfung für 2× 96 GB |",
        "|---|---|---|---|---|",
    ]
    for f in funde:
        link = f"[{f['repo']}](https://huggingface.co/{f['repo']})"
        zeilen.append(f"| {link} | {f['erstellt']} | {f['gb']} GB | {bilder[f['bilder']]} | {f['platz']} |")
    zeilen += [
        "",
        "**Aufnehmen** (auf dem Steuerrechner, siehe ANLEITUNG „Neues Modell aufnehmen“):",
        "```bash",
        "python3 profiles/neu.py <name> --quelle <repo> --wie <ähnliches-profil> --trocken",
        "```",
        "Bei GGUF-Repos mit vielen Quantisierungen zählt die Tabelle alle Dateien; "
        "mit `--auswahl <Quantisierung>` rechnet `neu.py` nur eine.",
        "",
        "Dieses Issue schließen, wenn entschieden ist. Bereits gemeldete Repos kommen nicht noch einmal.",
    ]
    return "\n".join(zeilen) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bekannt", type=Path, help="Datei mit früheren Meldungen; Repos darin werden übersprungen")
    ap.add_argument("--markdown", type=Path, help="Funde als Markdown in diese Datei schreiben (nur bei Funden)")
    args = ap.parse_args(argv)

    alte = args.bekannt.read_text(encoding="utf-8") if args.bekannt and args.bekannt.is_file() else ""
    try:
        funde = finde_neue(lies_liste(), alte)
    except OSError as fehler:
        print(f"FEHLER: Hugging Face nicht erreichbar ({fehler}).", file=sys.stderr)
        return 1

    if not funde:
        print("Nichts Neues.")
        return 0
    for f in funde:
        print(f"NEU: {f['repo']} ({f['erstellt']}, {f['gb']} GB) – {f['platz']}")
    if args.markdown:
        args.markdown.write_text(als_markdown(funde), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
