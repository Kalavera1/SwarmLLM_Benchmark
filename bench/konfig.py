"""Konfiguration: Modellprofil, Messziel und Zugangsdaten zusammenführen.

Woher die Werte kommen (spätere Quelle gewinnt):
  1. profiles/<name>/profile.env    Modell, Fähigkeiten, Startparameter
  2. benchmark.conf (bzw. .env)       alle eigenen Werte und Zugangsdaten (nie im Repo, Regel 2)
  3. runpod/.aktueller-pod.json      vom Pod-Skript geschrieben: URL, Key, Kosten
  4. Umgebungsvariablen              z. B. BENCH_ZIEL_URL für einen Einzeltest
  5. Kommandozeile                   --ziel, --ueber-gateway
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Pfade im Repo
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
PROFILE_ORDNER = REPO / "profiles"
ERGEBNIS_ORDNER = REPO / "results"
POD_DATEI = REPO / "runpod" / ".aktueller-pod.json"
ENV_DATEI = REPO / ".env"
KONF_DATEI = REPO / "benchmark.conf"

STANDARD_ZIEL = "http://127.0.0.1:8000/v1"
STANDARD_GATEWAY = "http://127.0.0.1:4000/v1"


# ---------------------------------------------------------------------------
# .env-Dateien lesen
# Einfaches Format KEY=VALUE. Kommentare (#) und Leerzeilen werden übersprungen,
# umschließende Anführungszeichen entfernt, "export " am Anfang ignoriert.
# ---------------------------------------------------------------------------
def lies_env_datei(pfad: Path) -> dict[str, str]:
    werte: dict[str, str] = {}
    if not pfad.is_file():
        return werte
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        if zeile.startswith("export "):
            zeile = zeile[len("export ") :]
        schluessel, _, wert = zeile.partition("=")
        wert = wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "'\"":
            wert = wert[1:-1]
        werte[schluessel.strip()] = wert
    return werte


# ---------------------------------------------------------------------------
# Eigene Werte: benchmark.conf (Vorlage benchmark.conf.example). Aus älteren
# Ständen wird .env weiter gelesen; benchmark.conf gewinnt bei doppelten Werten.
# ---------------------------------------------------------------------------
def lies_einstellungen() -> dict[str, str]:
    return lies_env_datei(ENV_DATEI) | lies_env_datei(KONF_DATEI)


# ---------------------------------------------------------------------------
# Modellprofil
# Ein Profil beschreibt ein Modell samt Fähigkeiten. Die Testblöcke fragen nur
# das Profil, nie den Modellnamen – so bleibt jeder Block modellunabhängig.
# ---------------------------------------------------------------------------
@dataclass
class Profil:
    name: str
    werte: dict[str, str]

    def get(self, schluessel: str, standard: str = "") -> str:
        return self.werte.get(schluessel, standard)

    @property
    def served_name(self) -> str:
        """Name, unter dem der Server das Modell anbietet (vLLM: --served-model-name)."""
        return self.get("SERVED_NAME") or self.get("MODEL_ID") or self.get("MODEL_QUELLE") or self.name

    @property
    def max_model_len(self) -> int:
        return int(self.get("MAX_MODEL_LEN", "0") or 0)

    @property
    def kann_bilder(self) -> bool:
        return self.get("VISION", "0") == "1"

    @property
    def key_pflicht(self) -> bool:
        """Regel 8: Standard ist Pflicht. Nur der lokale Mock darf ohne Key laufen."""
        return self.get("KEY_PFLICHT", "1") != "0"

    @property
    def denkstufen(self) -> dict[str, dict]:
        """Denkstufen als Name -> zusätzliche Felder der Anfrage.

        Format im Profil: DENKSTUFEN='aus={"chat_template_kwargs":{"enable_thinking":false}};an={}'
        Ohne Eintrag gibt es nur die Stufe "standard" ohne Zusatzfelder.
        """
        roh = self.get("DENKSTUFEN")
        if not roh:
            return {"standard": {}}
        stufen: dict[str, dict] = {}
        for teil in roh.split(";"):
            if not teil.strip():
                continue
            name, _, json_text = teil.partition("=")
            stufen[name.strip()] = json.loads(json_text) if json_text.strip() else {}
        return stufen

    def denk_extra(self, stufe: str) -> dict:
        """Zusatzfelder für eine Denkstufe; unbekannte Stufe = keine Zusatzfelder."""
        return dict(self.denkstufen.get(stufe, {}))


def lade_profil(name: str) -> Profil:
    pfad = PROFILE_ORDNER / name / "profile.env"
    if not pfad.is_file():
        verfuegbar = sorted(p.parent.name for p in PROFILE_ORDNER.glob("*/profile.env"))
        raise SystemExit(f"Profil '{name}' nicht gefunden ({pfad}). Verfügbar: {', '.join(verfuegbar) or '-'}")
    return Profil(name=name, werte=lies_env_datei(pfad))


# ---------------------------------------------------------------------------
# Laufender Pod (vom Pod-Skript geschrieben, steht in .gitignore)
# ---------------------------------------------------------------------------
def lade_pod_info() -> dict:
    if not POD_DATEI.is_file():
        return {}
    try:
        return json.loads(POD_DATEI.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Messziel: wohin die Anfragen gehen und mit welchem Key
# ---------------------------------------------------------------------------
@dataclass
class Ziel:
    basis_url: str  # endet auf /v1
    api_key: str
    modell: str
    ueber_gateway: bool = False
    pod: dict = field(default_factory=dict)

    @property
    def server_url(self) -> str:
        """Server-Wurzel ohne /v1, für /metrics und /tokenize von vLLM."""
        return self.basis_url[: -len("/v1")] if self.basis_url.endswith("/v1") else self.basis_url

    @property
    def kosten_pro_stunde(self) -> float:
        try:
            return float(
                self.pod.get("kosten_pro_stunde")
                or os.environ.get("BENCH_KOSTEN_PRO_STUNDE")
                or lies_einstellungen().get("BENCH_KOSTEN_PRO_STUNDE")
                or 0
            )
        except ValueError:
            return 0.0


def ziel_aufloesen(profil: Profil, ziel_url: str | None = None, ueber_gateway: bool = False) -> Ziel:
    env = lies_einstellungen()

    def wert(name: str, standard: str = "") -> str:
        return os.environ.get(name) or env.get(name) or standard

    pod = lade_pod_info()
    # Pod-Daten nur übernehmen, wenn der Pod zu diesem Profil gehört
    if pod and pod.get("profil") not in (None, profil.name):
        pod = {}

    if ueber_gateway:
        url = ziel_url or wert("LITELLM_URL", STANDARD_GATEWAY)
        key = wert("LITELLM_MASTER_KEY")
        modell = profil.get("LITELLM_NAME") or profil.served_name
    else:
        url = ziel_url or os.environ.get("BENCH_ZIEL_URL") or pod.get("url") or wert("BENCH_ZIEL_URL", STANDARD_ZIEL)
        key = pod.get("api_key") or wert("VLLM_API_KEY")
        modell = profil.served_name
    return Ziel(basis_url=url.rstrip("/"), api_key=key, modell=modell, ueber_gateway=ueber_gateway, pod=pod)
