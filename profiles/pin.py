#!/usr/bin/env python3
"""Pinnt ein Modellprofil (Regel 4): Modell-Revision und Image-Digest eintragen.

Liest aus profiles/<profil>/profile.env:
  MODEL_QUELLE        Hugging-Face-Repo, z. B. nvidia/Qwen3.8-27B-NVFP4
  VLLM_IMAGE_QUELLE   Image mit Tag, z. B. vllm/vllm-openai:v0.30.0
und schreibt zurück:
  MODEL_ID, MODEL_REVISION (voller Commit-Hash), MODELL_GROESSE_GB
  VLLM_IMAGE (Image per @sha256-Digest)

Läuft auf dem Steuerrechner und braucht nur Internet: Die Revision kommt von
Hugging Face, der Image-Digest direkt von der Registry (Docker Hub, ghcr.io) –
Docker ist nicht nötig. Nur wenn die Registry nicht antwortet, wird ersatzweise
Docker verwendet, falls vorhanden.

Aufruf:
  python3 profiles/pin.py <profil>               Modell und Image pinnen
  python3 profiles/pin.py <profil> --trocken     nur anzeigen, nichts schreiben
  python3 profiles/pin.py <profil> --nur-modell  bzw. --nur-image

Erst nach dem Pinnen lassen sich Profile starten; die CI prüft, dass MODEL_ID
nie ohne vollen MODEL_REVISION-Hash im Repo steht.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
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
# Image-Referenz zerlegen: "vllm/vllm-openai:v0.30.0" -> Registry, Repo, Tag
# Ohne Registry-Angabe gilt Docker Hub; Einzelnamen liegen dort unter library/.
# ---------------------------------------------------------------------------
def zerlege_image(ref: str) -> tuple[str, str, str, str]:
    """Liefert (registry, repo, tag, name_fuer_ausgabe)."""
    ohne_digest = ref.split("@")[0]
    name, _, tag = ohne_digest.rpartition(":")
    if not name or "/" in tag:  # kein Tag angegeben (der Doppelpunkt gehörte zu einem Port)
        name, tag = ohne_digest, "latest"
    teile = name.split("/")
    if len(teile) > 1 and ("." in teile[0] or ":" in teile[0] or teile[0] == "localhost"):
        registry, repo = teile[0], "/".join(teile[1:])
    else:
        registry, repo = "docker.io", name if "/" in name else f"library/{name}"
    return registry, repo, tag, name


# ---------------------------------------------------------------------------
# Digest direkt von der Registry (OCI-Distribution-API), ohne Docker:
#   1. anonymes Lese-Token holen (Docker Hub: auth.docker.io, ghcr.io: /token)
#   2. HEAD auf das Manifest; der Digest steht im Header Docker-Content-Digest
# Angefragt wird zuerst der Index (Multi-Arch), damit derselbe Digest wie bei
# "docker buildx imagetools inspect" herauskommt.
# ---------------------------------------------------------------------------
MANIFEST_TYPEN = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


def registry_urls(registry: str, repo: str, tag: str) -> tuple[str, str]:
    """(Token-URL, Manifest-URL) für eine Registry."""
    if registry == "docker.io":
        token = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
        return token, f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}"
    return f"https://{registry}/token?scope=repository:{repo}:pull", f"https://{registry}/v2/{repo}/manifests/{tag}"


def registry_digest(ref: str) -> str:
    registry, repo, tag, name = zerlege_image(ref)
    token_url, manifest_url = registry_urls(registry, repo, tag)
    anfrage = urllib.request.Request(token_url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:  # noqa: S310 (feste https-URL)
        token = json.load(antwort).get("token", "")
    kopf = {"User-Agent": USER_AGENT, "Accept": MANIFEST_TYPEN, "Authorization": f"Bearer {token}"}
    anfrage = urllib.request.Request(manifest_url, method="HEAD", headers=kopf)  # noqa: S310
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:  # noqa: S310
        digest = antwort.headers.get("Docker-Content-Digest", "")
    if not digest.startswith("sha256:"):
        raise ValueError(f"Registry lieferte keinen Digest für {ref}")
    return f"{name}@{digest}"


# ---------------------------------------------------------------------------
# Digest ermitteln: erst direkt von der Registry; nur wenn das scheitert,
# ersatzweise mit Docker (buildx ohne Download, sonst docker pull)
# ---------------------------------------------------------------------------
def image_digest(ref: str) -> str:
    try:
        return registry_digest(ref)
    except (OSError, ValueError, json.JSONDecodeError) as fehler:
        print(f"Registry nicht erreichbar ({fehler}) – versuche es mit Docker …")
    name = zerlege_image(ref)[3]
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
    ap.add_argument("--trocken", action="store_true", help="nur anzeigen, was eingetragen würde; nichts schreiben")
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
        try:
            sha, groesse = hf_revision(quelle, token)
        except urllib.error.HTTPError as fehler:
            hinweis = "Repo-Name im Profil oder HF_TOKEN prüfen" if fehler.code in (401, 403, 404) else ""
            print(f"FEHLER: Hugging Face antwortet mit HTTP {fehler.code} für {quelle}. {hinweis}", file=sys.stderr)
            return 1
        except OSError as fehler:
            print(f"FEHLER: Hugging Face nicht erreichbar ({fehler}). Internet prüfen.", file=sys.stderr)
            return 1
        werte |= {"MODEL_ID": quelle, "MODEL_REVISION": sha, "MODELL_GROESSE_GB": str(groesse)}
        print(f"Modell: {quelle}@{sha} ({groesse} GB)")
    if not args.nur_modell:
        quelle = profil.get("VLLM_IMAGE_QUELLE")
        if not quelle:
            print("FEHLER: VLLM_IMAGE_QUELLE fehlt im Profil.", file=sys.stderr)
            return 1
        werte["VLLM_IMAGE"] = image_digest(quelle)
        print(f"Image: {werte['VLLM_IMAGE']}")

    if args.trocken:
        print(f"Trockenlauf – {datei.relative_to(REPO)} bleibt unverändert. Ohne --trocken würde eingetragen:")
        for schluessel, wert in werte.items():
            print(f"  {schluessel}={wert}")
        return 0
    setze_werte(datei, werte)
    print(f"Eingetragen in {datei.relative_to(REPO)}. Bitte prüfen, committen und als Pull Request einreichen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
