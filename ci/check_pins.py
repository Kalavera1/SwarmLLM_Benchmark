#!/usr/bin/env python3
"""Prüft Regel 4 (Alles gepinnt) für alle Dateien, die Git verfolgt.

Geprüft wird:
- Container-Images in YAML (`image: ...`) und in Variablen (`IMAGE=...`,
  `VLLM_IMAGE=...`) müssen per Digest gepinnt sein (`@sha256:` + 64 Hex).
- GitHub Actions (`uses: owner/repo@...`) müssen auf einen vollen
  Commit-SHA (40 Hex) zeigen, nicht auf einen Tag.
- Modell-Profile (`profiles/**/*.env`): Wer `MODEL_ID` setzt, muss auch
  `MODEL_REVISION` als vollen Commit-Hash (40 Hex) setzen.

Markdown-Dateien werden nicht geprüft – Doku darf Beispiele enthalten.
Eine Zeile kann bewusst ausgenommen werden mit dem Kommentar `pin-check: ignore`.

Aufruf: python3 ci/check_pins.py [Dateien ...]   (ohne Argumente: alle Git-Dateien)
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Muster: woran ein korrekter Pin zu erkennen ist
#   DIGEST      @sha256: gefolgt von genau 64 Hex-Zeichen
#   COMMIT_SHA  genau 40 Hex-Zeichen (voller Git-Commit-Hash)
# ---------------------------------------------------------------------------
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}\b")
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")

# ---------------------------------------------------------------------------
# Muster: welche Zeilen überhaupt geprüft werden
#   YAML_IMAGE   "image: <ref>" in Stack- oder Compose-Dateien
#   VAR_IMAGE    "<NAME>IMAGE=<ref>" in Shell- und .env-Dateien, auch mit export
#   USES         "uses: <action>@<version>" in GitHub-Workflows
#   PROFILE_VAR  MODEL_ID und MODEL_REVISION in Modell-Profilen
# Die benannte Gruppe "ref" bzw. "val" fängt den Wert hinter dem Schlüssel.
# ---------------------------------------------------------------------------
YAML_IMAGE = re.compile(r"^\s*-?\s*image:\s*[\"']?(?P<ref>[^\"'\s#]+)")
VAR_IMAGE = re.compile(r"^\s*(?:export\s+)?(?P<name>[A-Z0-9_]*IMAGE)\s*=\s*[\"']?(?P<ref>[^\"'\s#]*)")
USES = re.compile(r"^\s*-?\s*uses:\s*[\"']?(?P<ref>[^\"'\s#]+)")
PROFILE_VAR = re.compile(r"^\s*(?:export\s+)?(?P<name>MODEL_ID|MODEL_REVISION)\s*=\s*[\"']?(?P<val>[^\"'\s#]*)")

# ---------------------------------------------------------------------------
# Einstellungen
#   IGNORE_MARKER     bewusste Ausnahme, muss in der Zeile sichtbar stehen
#   CHECKED_SUFFIXES  Dateiendungen, die geprüft werden ("" = ohne Endung,
#                     z. B. Skripte); Markdown fehlt absichtlich
# ---------------------------------------------------------------------------
IGNORE_MARKER = "pin-check: ignore"
CHECKED_SUFFIXES = {".yml", ".yaml", ".env", ".sh", ".toml", ".conf", ""}


# ---------------------------------------------------------------------------
# Ergebnis: ein Verstoß mit Datei, Zeilennummer und Meldung
# Ausgabe im Format "datei:zeile: meldung", das Editoren anklickbar machen.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Verstoss:
    datei: str
    zeile: int
    text: str

    def __str__(self) -> str:
        return f"{self.datei}:{self.zeile}: {self.text}"


# ---------------------------------------------------------------------------
# Prüflogik für eine Datei
# Bekommt Dateiname und Zeilen, liefert die Liste der Verstöße. Liest selbst
# keine Dateien – deshalb lässt sie sich mit künstlichen Zeilen testen.
# ---------------------------------------------------------------------------
def ist_variablen_referenz(ref: str) -> bool:
    """`${IMAGE}` oder `$IMAGE` wird an anderer Stelle gesetzt und dort geprüft."""
    return ref.startswith("$")


def pruefe_zeilen(datei: str, zeilen: list[str]) -> list[Verstoss]:
    verstoesse: list[Verstoss] = []
    ist_profil = datei.startswith("profiles/") and datei.endswith(".env")
    profil_werte: dict[str, tuple[int, str]] = {}

    for nr, zeile in enumerate(zeilen, start=1):
        # Ausnahmen: markierte Zeilen und Kommentare
        if IGNORE_MARKER in zeile or zeile.lstrip().startswith("#"):
            continue

        # Images (YAML und Variablen) brauchen einen Digest
        for muster in (YAML_IMAGE, VAR_IMAGE):
            treffer = muster.match(zeile)
            if not treffer:
                continue
            ref = treffer.group("ref")
            if not ref or ist_variablen_referenz(ref):
                continue
            if not DIGEST.search(ref):
                verstoesse.append(Verstoss(datei, nr, f"Image nicht per Digest gepinnt: {ref}"))

        # Actions brauchen einen vollen Commit-SHA (lokale Actions ausgenommen)
        treffer = USES.match(zeile)
        if treffer:
            ref = treffer.group("ref")
            if not ref.startswith("./") and not ref.startswith("docker://"):
                _, _, version = ref.partition("@")
                if not COMMIT_SHA.match(version):
                    verstoesse.append(Verstoss(datei, nr, f"Action nicht per Commit-SHA gepinnt: {ref}"))

        # Modell-Profile: Werte erst sammeln, Bewertung nach der Schleife
        if ist_profil:
            treffer = PROFILE_VAR.match(zeile)
            if treffer:
                profil_werte[treffer.group("name")] = (nr, treffer.group("val"))

    # Modell-Profile: MODEL_ID verlangt eine MODEL_REVISION als Commit-Hash
    if ist_profil and "MODEL_ID" in profil_werte:
        nr_id, _ = profil_werte["MODEL_ID"]
        if "MODEL_REVISION" not in profil_werte:
            verstoesse.append(Verstoss(datei, nr_id, "MODEL_ID ohne MODEL_REVISION"))
        else:
            nr_rev, rev = profil_werte["MODEL_REVISION"]
            if not COMMIT_SHA.match(rev):
                verstoesse.append(
                    Verstoss(datei, nr_rev, f"MODEL_REVISION ist kein voller Commit-Hash: {rev or '(leer)'}")
                )

    return verstoesse


# ---------------------------------------------------------------------------
# Dateiauswahl
# Geprüft werden nur Dateien, die Git verfolgt – also genau das, was ins Repo
# kommt. Lokale .env oder Caches bleiben außen vor.
# ---------------------------------------------------------------------------
def git_dateien() -> list[str]:
    ausgabe = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True).stdout
    return [d for d in ausgabe.splitlines() if d]


def soll_geprueft_werden(datei: str) -> bool:
    pfad = Path(datei)
    return pfad.suffix in CHECKED_SUFFIXES and pfad.name not in {"LICENSE"}


# ---------------------------------------------------------------------------
# Hauptprogramm
# Prüft alle Dateien, gibt die Verstöße aus. Exit-Code 1 bei Verstößen,
# damit der CI-Schritt rot wird; 0, wenn alles gepinnt ist.
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    dateien = argv or git_dateien()
    verstoesse: list[Verstoss] = []
    geprueft = 0
    for datei in dateien:
        if not soll_geprueft_werden(datei) or not Path(datei).is_file():
            continue
        geprueft += 1
        zeilen = Path(datei).read_text(encoding="utf-8", errors="replace").splitlines()
        verstoesse.extend(pruefe_zeilen(datei, zeilen))

    for v in verstoesse:
        print(v)
    if verstoesse:
        print(f"\n{len(verstoesse)} Verstoß/Verstöße gegen Regel 4 (Alles gepinnt).")
        return 1
    print(f"Pin-Prüfung: {geprueft} Dateien geprüft, keine Verstöße.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
