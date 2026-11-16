#!/usr/bin/env python3
"""Pinnt ein Modellprofil (Regel 4): Modell-Revision und Image-Digest eintragen.

Liest aus profiles/<profil>/profile.env:
  MODEL_QUELLE        Hugging-Face-Repo, z. B. nvidia/Qwen3.8-27B-NVFP4
  VLLM_IMAGE_QUELLE   Image mit Tag, z. B. vllm/vllm-openai:v0.30.0
und schreibt zurück:
  MODEL_ID, MODEL_REVISION (voller Commit-Hash), MODELL_GROESSE_GB
  VLLM_IMAGE (Image per @sha256-Digest)

Läuft auf dem Mediaserver (braucht Internet und für das Image Docker).
Aufruf: python3 profiles/pin.py <profil> [--nur-modell | --nur-image]

Erst nach dem Pinnen lassen sich Profile starten; die CI prüft, dass MODEL_ID
nie ohne vollen MODEL_REVISION-Hash im Repo steht.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from bench.konfig import lies_einstellungen, lies_env_datei  # noqa: E402 (Pfad muss vorher gesetzt sein)

USER_AGENT = "SwarmLLM_Benchmark-pin/1.0"


# ---------------------------------------------------------------------------
# Hugging Face: Commit-Hash der aktuellen Revision und Gesamtgröße der Dateien
# ---------------------------------------------------------------------------
def hf_revision(repo: str, token: str) -> tuple[str, float]:
    url = f"https://huggingface.co/api/models/{repo}/revision/main?blobs=true"
    anfrage = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 (feste https-URL)
    if token:
        anfrage.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(anfrage, timeout=60) as antwort:  # noqa: S310
        daten = json.load(antwort)
    groesse = sum(d.get("size") or 0 for d in daten.get("siblings", [])) / 1e9
    return daten["sha"], round(groesse, 1)


# ---------------------------------------------------------------------------
# Docker: Digest ohne das ganze Image zu laden (buildx), sonst mit pull
# ---------------------------------------------------------------------------
def image_digest(ref: str) -> str:
    name = ref.split("@")[0].rsplit(":", 1)[0] if ":" in ref.split("/")[-1] else ref.split("@")[0]
    lauf = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", ref, "--format", "{{json .Manifest}}"],
        capture_output=True,
        text=True,
    )
    if lauf.returncode == 0:
        digest = json.loads(lauf.stdout).get("digest", "")
        if digest.startswith("sha256:"):
            return f"{name}@{digest}"
    print("buildx nicht verfügbar – lade das Image mit docker pull (kann dauern) …")
    subprocess.run(["docker", "pull", ref], check=True)
    repo_digest = subprocess.run(
        ["docker", "inspect", "--format", "{{index .RepoDigests 0}}", ref],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return repo_digest


# ---------------------------------------------------------------------------
# Profil-Datei aktualisieren: vorhandene Zeile ersetzen oder am Ende anhängen
# ---------------------------------------------------------------------------
def setze_werte(datei: Path, werte: dict[str, str]) -> None:
    text = datei.read_text(encoding="utf-8")
    neu_angehaengt = []
    for schluessel, wert in werte.items():
        zeile = f"{schluessel}={wert}"
        muster = re.compile(rf"^{schluessel}=.*$", re.M)
        if muster.search(text):
            text = muster.sub(zeile, text)
        else:
            neu_angehaengt.append(zeile)
    if neu_angehaengt:
        text = text.rstrip("\n") + f"\n\n# Gepinnt am {date.today().isoformat()} mit profiles/pin.py\n"
        text += "\n".join(neu_angehaengt) + "\n"
    datei.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("profil")
    gruppe = ap.add_mutually_exclusive_group()
    gruppe.add_argument("--nur-modell", action="store_true")
    gruppe.add_argument("--nur-image", action="store_true")
    args = ap.parse_args()

    datei = REPO / "profiles" / args.profil / "profile.env"
    profil = lies_env_datei(datei)
    if not profil:
        print(f"FEHLER: {datei} fehlt oder ist leer.", file=sys.stderr)
        return 1

    werte: dict[str, str] = {}
    if not args.nur_image:
        quelle = profil.get("MODEL_QUELLE")
        if not quelle:
            print("FEHLER: MODEL_QUELLE fehlt im Profil.", file=sys.stderr)
            return 1
        token = lies_einstellungen().get("HF_TOKEN", "")
        sha, groesse = hf_revision(quelle, token)
        werte |= {"MODEL_ID": quelle, "MODEL_REVISION": sha, "MODELL_GROESSE_GB": str(groesse)}
        print(f"Modell: {quelle}@{sha} ({groesse} GB)")
    if not args.nur_modell:
        quelle = profil.get("VLLM_IMAGE_QUELLE")
        if not quelle:
            print("FEHLER: VLLM_IMAGE_QUELLE fehlt im Profil.", file=sys.stderr)
            return 1
        werte["VLLM_IMAGE"] = image_digest(quelle)
        print(f"Image: {werte['VLLM_IMAGE']}")

    setze_werte(datei, werte)
    print(f"Eingetragen in {datei.relative_to(REPO)}. Bitte prüfen, committen und als Pull Request einreichen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
