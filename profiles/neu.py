#!/usr/bin/env python3
"""Legt ein neues Modellprofil an, mit Vorprüfung, ob das Modell auf 2 Karten passt.

Fragt Hugging Face nach Dateigrößen, Bildfähigkeit und Kontextlänge und schreibt
profiles/<name>/profile.env als Entwurf (PROFIL_STATUS=entwurf). Ein Entwurf
startet nicht. Danach von Hand: Startparameter mit dem vLLM-Recipe des Modells
abgleichen, pinnen (profiles/pin.py), PROFIL_STATUS=bereit setzen, Pull Request.

Aufruf (auf dem Steuerrechner, braucht Internet):
  python3 profiles/neu.py <name> --quelle <org/repo>                  aus der Vorlage
  python3 profiles/neu.py <name> --quelle <org/repo> --wie <profil>   Startparameter eines ähnlichen Profils übernehmen
  python3 profiles/neu.py <name> --quelle <org/repo> --trocken        nur die Vorprüfung, nichts schreiben
  --auswahl <text>   nur Dateien zählen, deren Pfad <text> enthält – z. B. eine
                     Quantisierung in einem GGUF-Repo mit vielen Varianten

Die Vorprüfung ist eine grobe Rechnung (Gewichte gegen 2× 96 GB), keine Messung:
Wie viel Kontext wirklich passt, zeigt erst der Lauf.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from bench.konfig import lies_einstellungen  # noqa: E402 (Pfad muss vorher gesetzt sein)

PROFILE_ORDNER = REPO / "profiles"
USER_AGENT = "SwarmLLM_Benchmark-neu/1.0"

# ---------------------------------------------------------------------------
# Eckdaten der Testhardware (nur 2 Karten, siehe README) und Grenzen der
# Vorprüfung. 96 GB pro Karte dezimal gerechnet – eher zu knapp als zu großzügig.
# ---------------------------------------------------------------------------
KARTEN = 2
VRAM_PRO_KARTE_GB = 96
VRAM_GB = KARTEN * VRAM_PRO_KARTE_GB
ANTEIL_GUT = 0.75  # bis hier bleibt genug Platz für KV-Cache und langen Kontext
ANTEIL_KNAPP = 0.95  # bis hier passt es, aber mit wenig Platz für den KV-Cache
RAM_RESERVE_GB = 64  # für Betriebssystem, Container und KV-Auslagerung
RAM_ZIELSERVER_GB = 384  # geplanter Arbeitsspeicher im Zielserver (README)
ZIEL_KONTEXT = 524288  # 500k-Pflichtpunkt der Testsuite (512 × 1024)
GEWICHT_ENDUNGEN = (".safetensors", ".gguf", ".bin", ".pt", ".pth")


# ---------------------------------------------------------------------------
# Hugging Face: JSON holen. Eine Stelle für alle Anfragen, damit Tests sie
# ersetzen können. Ohne Token klappt es für öffentliche Repos.
# ---------------------------------------------------------------------------
def hf_json(url: str, token: str = "") -> dict | list:
    anfrage = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 (feste https-URL)
    if token:
        anfrage.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(anfrage, timeout=60) as antwort:  # noqa: S310
        return json.load(antwort)


def hf_modell(repo: str, token: str = "") -> dict:
    """Modell-Infos mit Dateigrößen (siblings), pipeline_tag und Commit (sha)."""
    return hf_json(f"https://huggingface.co/api/models/{repo}/revision/main?blobs=true", token)


def hf_config(repo: str, token: str = "") -> dict:
    """config.json des Modells; leer, wenn es keine gibt (z. B. reine GGUF-Repos)."""
    try:
        daten = hf_json(f"https://huggingface.co/{repo}/resolve/main/config.json", token)
    except urllib.error.HTTPError as fehler:
        if fehler.code == 404:
            return {}
        raise
    return daten if isinstance(daten, dict) else {}


def hf_suche(autor: str, begriff: str) -> list[dict]:
    """Neueste Repos eines Autors, deren Name den Begriff enthält (öffentliche Suche)."""
    abfrage = urllib.parse.urlencode(
        {"author": autor, "search": begriff, "sort": "createdAt", "direction": "-1", "limit": "100"}
    )
    daten = hf_json(f"https://huggingface.co/api/models?{abfrage}")
    return daten if isinstance(daten, list) else []


# ---------------------------------------------------------------------------
# Vorprüfung: Größe der Gewichte, Platz auf den Karten, Bilder, Kontext
# ---------------------------------------------------------------------------
def gewichte_gb(siblings: list[dict], auswahl: str = "") -> float:
    """Summe der Gewichtsdateien in GB; mit auswahl nur passende Pfade."""
    summe = 0
    for datei in siblings:
        pfad = datei.get("rfilename", "")
        if pfad.endswith(GEWICHT_ENDUNGEN) and auswahl in pfad:
            summe += datei.get("size") or 0
    return round(summe / 1e9, 1)


def bewerte_platz(gb: float) -> tuple[str, str, int]:
    """(Stufe, Erklärung, nötiger Arbeitsspeicher in GB) für Gewichte von gb GB."""
    if gb <= 0:
        return "unklar", "keine Gewichtsdateien gefunden – Repo-Name oder --auswahl prüfen", 64
    rest = round(VRAM_GB - gb)
    if gb <= ANTEIL_GUT * VRAM_GB:
        return "passt", f"passt in den VRAM, ≈ {rest} GB bleiben für KV-Cache und Kontext", 64
    if gb <= ANTEIL_KNAPP * VRAM_GB:
        return "knapp", f"passt knapp in den VRAM, nur ≈ {rest} GB für den KV-Cache – langer Kontext fraglich", 64
    ram = math.ceil(gb - ANTEIL_GUT * VRAM_GB + RAM_RESERVE_GB)
    text = (
        f"passt nicht in {VRAM_GB} GB VRAM – Teile müssen in den Arbeitsspeicher "
        f"(CPU-Experten, z. B. llama.cpp oder KTransformers statt vLLM), Host-RAM ≥ ≈ {ram} GB"
    )
    if ram > RAM_ZIELSERVER_GB:
        text += f"; mehr als die geplanten {RAM_ZIELSERVER_GB} GB des Zielservers"
        return "zu-gross", text, ram
    return "auslagern", text, ram


def bildfaehig(info: dict, config: dict) -> tuple[bool | None, str]:
    """(ja/nein/unklar, Begründung) aus pipeline_tag und config.json."""
    tag = info.get("pipeline_tag") or ""
    if tag in ("image-text-to-text", "image-to-text", "any-to-any", "video-text-to-text"):
        return True, f"pipeline_tag {tag}"
    if "vision_config" in config:
        return True, "vision_config in config.json"
    if tag == "text-generation" and config:
        return False, "pipeline_tag text-generation, keine vision_config"
    return None, "nicht erkennbar – Modellkarte lesen"


def kontext(config: dict) -> int | None:
    """Kontextlänge laut config.json (auch verschachtelt unter text_config)."""
    for quelle in (config, config.get("text_config") or {}):
        wert = quelle.get("max_position_embeddings")
        if isinstance(wert, int) and wert > 0:
            return wert
    return None


# ---------------------------------------------------------------------------
# Profiltext: Vorlage für neue Modelle oder Kopie eines ähnlichen Profils
# ---------------------------------------------------------------------------
VORLAGE = """\
PROFIL_STATUS=entwurf

# --- Modell und Image (Regel 4): pinnen mit  python3 profiles/pin.py {name}
MODEL_QUELLE={quelle}
# Image mit Tag aus dem vLLM-Recipe des Modells, z. B. vllm/vllm-openai:v0.30.0
VLLM_IMAGE_QUELLE=
VLLM_IMAGE=

# --- Server: Startparameter aus dem vLLM-Recipe des Modells übernehmen.
# --tensor-parallel-size 2 verteilt das Modell über beide Karten.
SERVED_NAME={name}
MAX_MODEL_LEN={kontext}
SERVE_ARGS='--tensor-parallel-size 2 --max-model-len {kontext}'
SPEC_CONFIG=
SERVE_ENV=
KV_CPU_OFFLOAD_GB=

# --- Fähigkeiten für die Testsuite (DENKSTUFEN leer = nur Stufe "standard")
VISION={vision}
DENKSTUFEN=

# --- Host
GPU_ANZAHL={karten}
DISK_GB={disk}
HOST_RAM_MIN_GB={ram}
P2P_PFLICHT=1
HARDWARE='{karten}x RTX PRO 6000 Blackwell (je {vram} GB)'
"""

# Von pin.py gesetzte Felder: Im neuen Profil fehlen sie, bis es gepinnt ist
# (ein leeres MODEL_REVISION= würde die Pin-Prüfung der CI verletzen).
GEPINNTE_FELDER = ("MODEL_ID", "MODEL_REVISION", "MODELL_GROESSE_GB")


def setze(text: str, schluessel: str, wert: str) -> str:
    """Zeile SCHLUESSEL=... ersetzen oder am Ende anhängen."""
    muster = re.compile(rf"^{schluessel}=.*$", re.M)
    if muster.search(text):
        return muster.sub(lambda _: f"{schluessel}={wert}", text)
    return text.rstrip("\n") + f"\n{schluessel}={wert}\n"


def ohne_kopfkommentar(text: str) -> str:
    """Den Kopfkommentar eines Profils entfernen (er beschreibt das alte Modell)."""
    zeilen = text.splitlines()
    while zeilen and (not zeilen[0].strip() or zeilen[0].startswith("#")):
        zeilen.pop(0)
    return "\n".join(zeilen) + "\n"


def profiltext(name: str, quelle: str, werte: dict[str, str], kopf: str, vorbild: str | None) -> str:
    """Kompletter Inhalt von profile.env."""
    if vorbild is None:
        rumpf = VORLAGE.format(name=name, quelle=quelle, karten=KARTEN, vram=VRAM_PRO_KARTE_GB, **werte)
    else:
        rumpf = ohne_kopfkommentar(vorbild)
        rumpf = re.sub(r"^# Gepinnt am .*\n", "", rumpf, flags=re.M)
        for feld in GEPINNTE_FELDER:
            rumpf = re.sub(rf"^{feld}=.*\n", "", rumpf, flags=re.M)
        rumpf = re.sub(r"^VLLM_IMAGE=.*$", "VLLM_IMAGE=", rumpf, flags=re.M)
        rumpf = setze(rumpf, "MODEL_QUELLE", quelle)
        rumpf = setze(rumpf, "SERVED_NAME", name)
        rumpf = setze(rumpf, "PROFIL_STATUS", "entwurf")
        rumpf = setze(rumpf, "VISION", werte["vision"])
        rumpf = setze(rumpf, "DISK_GB", werte["disk"])
        # Kontext auf das neue Modell begrenzen, auch in den vLLM-Argumenten
        rumpf = setze(rumpf, "MAX_MODEL_LEN", werte["kontext"])
        rumpf = re.sub(r"--max-model-len \d+", f"--max-model-len {werte['kontext']}", rumpf)
        # Arbeitsspeicher: den größeren Wert aus Vorbild und Vorprüfung
        alt_ram = re.search(r"^HOST_RAM_MIN_GB=(\d+)", rumpf, re.M)
        ram = max(int(werte["ram"]), int(alt_ram.group(1)) if alt_ram else 0)
        rumpf = setze(rumpf, "HOST_RAM_MIN_GB", str(ram))
        rumpf = rumpf.replace(f"profiles/pin.py {vorbild_name(vorbild)}", f"profiles/pin.py {name}")
    return kopf + "\n" + rumpf


def vorbild_name(text: str) -> str:
    """Profilname aus der Kopfzeile '# Profil "<name>": …' des Vorbilds."""
    treffer = re.search(r'^# Profil "([^"]+)"', text, re.M)
    return treffer.group(1) if treffer else ""


# ---------------------------------------------------------------------------
# Vorprüfung für ein Repo: alles, was das neue Profil und die Ausgabe brauchen
# ---------------------------------------------------------------------------
def vorpruefung(quelle: str, auswahl: str = "", token: str = "") -> dict:
    info = hf_modell(quelle, token)
    config = hf_config(quelle, token)
    gb = gewichte_gb(info.get("siblings", []), auswahl)
    stufe, platz, ram = bewerte_platz(gb)
    bilder, bilder_grund = bildfaehig(info, config)
    laenge = kontext(config)
    return {
        "quelle": quelle,
        "gb": gb,
        "stufe": stufe,
        "platz": platz,
        "ram": ram,
        "bilder": bilder,
        "bilder_grund": bilder_grund,
        "kontext": laenge,
    }


def kopfkommentar(name: str, pruefung: dict, auswahl: str, vorbild: str | None) -> str:
    bilder = {True: "ja", False: "nein", None: "unklar"}[pruefung["bilder"]]
    laenge = pruefung["kontext"] or "unbekannt (keine config.json)"
    zeilen = [
        f'# Profil "{name}": {pruefung["quelle"]}',
        f"# STATUS: ENTWURF – angelegt am {date.today().isoformat()} mit profiles/neu.py"
        + (f" nach dem Vorbild {vorbild}." if vorbild else " aus der Vorlage."),
        "#",
        "# Vor dem ersten Lauf:",
        "#   1. Startparameter mit dem vLLM-Recipe bzw. der Modellkarte abgleichen",
        f"#   2. pinnen: python3 profiles/pin.py {name}",
        "#   3. PROFIL_STATUS=bereit setzen und als Pull Request einreichen",
        "#",
        "# Vorprüfung (Hugging Face, grobe Rechnung, keine Messung):",
        f"#   Gewichte: {pruefung['gb']} GB" + (f" (nur Dateien mit '{auswahl}')" if auswahl else ""),
        f"#   Platz:    {pruefung['platz']}",
        f"#   Bilder:   {bilder} ({pruefung['bilder_grund']})",
        f"#   Kontext:  {laenge} Tokens laut config.json",
    ]
    return "\n".join(zeilen) + "\n"


def profilwerte(pruefung: dict) -> dict[str, str]:
    laenge = min(pruefung["kontext"] or ZIEL_KONTEXT, ZIEL_KONTEXT)
    return {
        "kontext": str(laenge),
        "vision": "1" if pruefung["bilder"] else "0",
        "disk": str(math.ceil(pruefung["gb"] * 1.2 + 20)),
        "ram": str(pruefung["ram"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", help="Profilname, z. B. qwen4-27b (Kleinbuchstaben, Ziffern, - und .)")
    ap.add_argument("--quelle", required=True, help="Hugging-Face-Repo, z. B. Qwen/Qwen4-27B")
    ap.add_argument("--wie", help="vorhandenes Profil, dessen Startparameter übernommen werden")
    ap.add_argument("--auswahl", default="", help="nur Gewichtsdateien, deren Pfad diesen Text enthält")
    ap.add_argument("--trocken", action="store_true", help="nur die Vorprüfung zeigen, nichts schreiben")
    args = ap.parse_args(argv)

    # Eingaben prüfen, bevor das Netz gefragt wird
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", args.name):
        print("FEHLER: Profilname nur aus Kleinbuchstaben, Ziffern, '-' und '.'.", file=sys.stderr)
        return 1
    ziel = PROFILE_ORDNER / args.name / "profile.env"
    if ziel.exists() and not args.trocken:
        print(f"FEHLER: {ziel.relative_to(REPO)} gibt es schon.", file=sys.stderr)
        return 1
    vorbild = None
    if args.wie:
        vorbild_datei = PROFILE_ORDNER / args.wie / "profile.env"
        if not vorbild_datei.is_file():
            print(f"FEHLER: Vorbild-Profil {args.wie} nicht gefunden.", file=sys.stderr)
            return 1
        vorbild = vorbild_datei.read_text(encoding="utf-8")

    # Hugging Face fragen
    try:
        pruefung = vorpruefung(args.quelle, args.auswahl, lies_einstellungen().get("HF_TOKEN", ""))
    except urllib.error.HTTPError as fehler:
        hinweis = "Repo-Name oder HF_TOKEN prüfen" if fehler.code in (401, 403, 404) else ""
        print(f"FEHLER: Hugging Face antwortet mit HTTP {fehler.code} für {args.quelle}. {hinweis}", file=sys.stderr)
        return 1
    except OSError as fehler:
        print(f"FEHLER: Hugging Face nicht erreichbar ({fehler}). Internet prüfen.", file=sys.stderr)
        return 1

    kopf = kopfkommentar(args.name, pruefung, args.auswahl, args.wie)
    print("\n".join(z[2:] if z.startswith("# ") else z.lstrip("#") for z in kopf.splitlines()))
    if args.trocken:
        print("Trockenlauf – nichts geschrieben.")
        return 0

    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(profiltext(args.name, args.quelle, profilwerte(pruefung), kopf, vorbild), encoding="utf-8")
    print(f"Angelegt: {ziel.relative_to(REPO)} (Entwurf). Nächste Schritte stehen oben in der Datei.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
