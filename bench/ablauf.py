"""Ablauf eines Messlaufs: Kontext, Aufwärmen, Block ausführen, Ergebnis speichern.

Jeder Block bekommt einen Kontext mit Profil, Client und Stufe und gibt ein
Wörterbuch zurück. Der Ablauf ergänzt drumherum:
  - Aufwärmrunde vor dem Block (JIT, CUDA-Graphs; zählt nicht mit)
  - vLLM-Zähler vor und nach dem Block (Prefix-Cache, spekulatives Decoding)
  - Dauer und Kosten des Blocks
  - Metadaten nach Regel 6 und Speichern als JSON
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from bench import VERSION, texte
from bench.client import Antwort, Client
from bench.konfig import ERGEBNIS_ORDNER, REPO, Profil, Ziel


# ---------------------------------------------------------------------------
# Kontext für einen Lauf
# ---------------------------------------------------------------------------
@dataclass
class Kontext:
    profil: Profil
    ziel: Ziel
    client: Client
    stufe: str = "schnell"  # "schnell" oder "voll"
    ausgabe: Callable[[str], None] = print
    _zeichen_pro_token: float | None = None
    kalibrierung: str = ""
    rohdaten: list[dict] = field(default_factory=list)
    _sperre: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def voll(self) -> bool:
        return self.stufe == "voll"

    def log(self, text: str) -> None:
        self.ausgabe(f"  {text}")

    @property
    def zeichen_pro_token(self) -> float:
        """Einmal pro Lauf kalibriert, dann gemerkt. Die Sperre verhindert, dass
        parallele Threads (Lastmix) gleichzeitig kalibrieren."""
        with self._sperre:
            if self._zeichen_pro_token is None:
                self._zeichen_pro_token, self.kalibrierung = texte.kalibrieren(self.client)
                self.log(f"Kalibrierung: {self._zeichen_pro_token:.2f} Zeichen pro Token ({self.kalibrierung})")
        return self._zeichen_pro_token

    def max_kontext(self) -> int:
        """Größter nutzbarer Kontext: Profil, sonst Angabe des Servers, sonst 128k."""
        if self.profil.max_model_len:
            return self.profil.max_model_len
        status, daten = self.client.get_json("/models")
        if status == 200:
            for modell in daten.get("data", []):
                if modell.get("id") == self.client.modell and modell.get("max_model_len"):
                    return int(modell["max_model_len"])
        return 131072

    def denk_extra(self, bevorzugt: str = "aus") -> dict:
        """Zusatzfelder für eine Denkstufe, falls das Profil sie kennt; sonst keine."""
        return self.profil.denk_extra(bevorzugt) if bevorzugt in self.profil.denkstufen else {}

    def merke(self, art: str, antwort: Antwort, **extra) -> None:
        """Rohdaten einer Anfrage für results/raw/ (nicht im Repo)."""
        self.rohdaten.append({"art": art, **extra, **antwort.kurz()})


# ---------------------------------------------------------------------------
# Parallele Ausführung
# Jede Aufgabe ist eine Funktion ohne Argumente; Ergebnisse in Eingabereihenfolge.
# ---------------------------------------------------------------------------
def parallel(aufgaben: list[Callable[[], object]], gleichzeitig: int) -> list:
    if not aufgaben:
        return []
    with ThreadPoolExecutor(max_workers=max(1, gleichzeitig)) as pool:
        zukuenfte = [pool.submit(a) for a in aufgaben]
        return [z.result() for z in zukuenfte]


# ---------------------------------------------------------------------------
# Aufwärmrunde: zwei kurze Anfragen, nicht mitgezählt (Erfahrung B300: die
# erste Anfrage nach dem Start war wegen JIT bis zu 3x langsamer)
# ---------------------------------------------------------------------------
def aufwaermen(ctx: Kontext) -> None:
    for _ in range(2):
        ctx.client.chat([{"role": "user", "content": "Sag Hallo."}], max_tokens=16, extra=ctx.denk_extra())


# ---------------------------------------------------------------------------
# Metadaten nach Regel 6
# ---------------------------------------------------------------------------
def git_stand() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unbekannt"


def metadaten(ctx: Kontext) -> dict:
    p = ctx.profil
    pod = ctx.ziel.pod
    return {
        "zeitpunkt_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "bench_version": VERSION,
        "repo_stand": git_stand(),
        "profil": p.name,
        "stufe": ctx.stufe,
        "modell": {
            "served_name": p.served_name,
            "model_id": p.get("MODEL_ID") or p.get("MODEL_QUELLE"),
            "revision": p.get("MODEL_REVISION") or "nicht gepinnt",
        },
        "runtime": {
            "image": p.get("VLLM_IMAGE") or p.get("VLLM_IMAGE_QUELLE") or "unbekannt",
            "startparameter": p.get("SERVE_ARGS"),
            "umgebung": p.get("SERVE_ENV"),
        },
        "hardware": {
            "beschreibung": p.get("HARDWARE") or "unbekannt",
            "pod_id": pod.get("pod_id"),
            "gpu": pod.get("gpu"),
            "cloud": pod.get("cloud"),
            "rechenzentrum": pod.get("rechenzentrum"),
            "kosten_pro_stunde": ctx.ziel.kosten_pro_stunde or None,
        },
        "ziel": {
            # Nur Host und Pfad, nie der Key
            "url": ctx.ziel.basis_url,
            "ueber_gateway": ctx.ziel.ueber_gateway,
        },
        "kalibrierung": {"zeichen_pro_token": ctx._zeichen_pro_token, "quelle": ctx.kalibrierung or None},
    }


# ---------------------------------------------------------------------------
# vLLM-Zähler: Differenz vor/nach dem Block
# Nur Zähler (Endung _total) ergeben als Differenz Sinn. Daraus abgeleitet:
# Trefferquote des Prefix-Caches und Akzeptanzrate beim spekulativen Decoding.
# ---------------------------------------------------------------------------
def zaehler_differenz(vorher: dict[str, float], nachher: dict[str, float]) -> dict:
    if not vorher or not nachher:
        return {}
    diff = {
        name.removeprefix("vllm:"): round(nachher[name] - vorher.get(name, 0.0), 3)
        for name in nachher
        if name.endswith("_total") and nachher[name] - vorher.get(name, 0.0) != 0
    }
    abgeleitet = {}
    anfragen = diff.get("prefix_cache_queries_total")
    if anfragen:
        abgeleitet["prefix_cache_trefferquote"] = round(diff.get("prefix_cache_hits_total", 0) / anfragen, 4)
    entwuerfe = diff.get("spec_decode_num_draft_tokens_total")
    if entwuerfe:
        abgeleitet["spec_decode_akzeptanz"] = round(diff.get("spec_decode_num_accepted_tokens_total", 0) / entwuerfe, 4)
    return {"differenz": diff, "abgeleitet": abgeleitet}


# ---------------------------------------------------------------------------
# Speichern
#   results/<profil>/<block>/<zeitpunkt>-<stufe>.json   Zusammenfassung (ins Repo)
#   results/raw/<profil>/<block>/<zeitpunkt>.json        jede Anfrage (nicht im Repo)
# ---------------------------------------------------------------------------
def speichern(ctx: Kontext, block: str, ergebnis: dict, ordner: Path = ERGEBNIS_ORDNER) -> Path:
    stempel = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ziel = ordner / ctx.profil.name / block / f"{stempel}-{ctx.stufe}.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if ctx.rohdaten:
        roh = ordner / "raw" / ctx.profil.name / block / f"{stempel}.json"
        roh.parent.mkdir(parents=True, exist_ok=True)
        roh.write_text(json.dumps(ctx.rohdaten, ensure_ascii=False) + "\n", encoding="utf-8")
    return ziel


# ---------------------------------------------------------------------------
# Einen Block ausführen
# Ein Fehler im Block bricht nicht den ganzen Lauf ab: Er landet im Ergebnis,
# und der nächste Block startet. Das spart Geld, wenn der Pod schon läuft.
# ---------------------------------------------------------------------------
def fuehre_block_aus(ctx: Kontext, name: str, modul, ordner: Path = ERGEBNIS_ORDNER) -> dict:
    ctx.ausgabe(f"\n== {name} ({modul.EBENE}): {modul.BESCHREIBUNG}")
    ctx.rohdaten = []
    if getattr(modul, "AUFWAERMEN", True):
        aufwaermen(ctx)
    zaehler_vorher = ctx.client.metriken()
    start = time.monotonic()
    try:
        inhalt = modul.ausfuehren(ctx)
    except Exception as fehler:  # noqa: BLE001 (bewusst breit, siehe Kommentar oben)
        inhalt = {"bestanden": False, "fehler": f"{type(fehler).__name__}: {fehler}"}
    dauer = time.monotonic() - start
    kosten = ctx.ziel.kosten_pro_stunde * dauer / 3600

    ergebnis = {
        "block": name,
        "ebene": modul.EBENE,
        "meta": metadaten(ctx),
        "dauer_s": round(dauer, 1),
        "kosten_usd": round(kosten, 3) if kosten else None,
        "vllm_zaehler": zaehler_differenz(zaehler_vorher, ctx.client.metriken()),
        **inhalt,
    }
    pfad = speichern(ctx, name, ergebnis, ordner)
    status = {True: "BESTANDEN", False: "NICHT BESTANDEN", None: "gemessen"}.get(ergebnis.get("bestanden"), "?")
    if ergebnis.get("uebersprungen"):
        status = f"übersprungen ({ergebnis['uebersprungen']})"
    ctx.ausgabe(f"   -> {status}, {dauer:.0f} s, gespeichert: {pfad.relative_to(ordner.parent)}")
    if ergebnis.get("fehler"):
        ctx.ausgabe(f"   Fehler: {ergebnis['fehler']}")
    return ergebnis
