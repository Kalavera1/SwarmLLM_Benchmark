#!/usr/bin/env python3
"""RunPod-Steuerung über die REST-API v2: Pod anlegen, prüfen, löschen.

Befehle (alle vom Steuerrechner aus, im Repo-Ordner):
  python3 runpod/rp.py gpus                      GPU-Typen aus dem Katalog (ID für RUNPOD_GPU_ID)
  python3 runpod/rp.py kosten                    bisher verbuchte Kosten aller Pods
  python3 runpod/rp.py up <profil> [--stufe schnell|voll] [--minuten N] [--cloud COMMUNITY|SECURE] [--trocken]
  python3 runpod/rp.py warten                    bis vLLM antwortet; misst die Kaltstartzeit
  python3 runpod/rp.py check                     Host (P2P, CPU, RAM), Modellname, Key-Schutz
  python3 runpod/rp.py status                    alle eigenen Pods mit Kosten
  python3 runpod/rp.py down [--pod ID]           Pod terminieren und Kosten verbuchen
  python3 runpod/rp.py down-alle                 Notbremse: alle eigenen Pods terminieren

Sicherheitsnetz (Regel 5 und geldschonend):
  - Vor dem Anlegen: Kostenschätzung und ausdrückliche Bestätigung mit "ja".
    Eine Ausgabengrenze setzt ihr im RunPod-Konto (Limit der hinterlegten Karte),
    nicht in diesem Skript.
  - Watchdog: systemd-run (oder nohup) terminiert den Pod nach --minuten.
  - Jeder Pod wird in results/kosten.csv verbucht.
  - Pro Lauf ein neuer VLLM_API_KEY (Regel 8), nur in runpod/.aktueller-pod.json
    (steht in .gitignore, Rechte 600).

Nur Standardbibliothek. Doku der API: https://docs.runpod.io/api-reference-v2
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from bench.konfig import POD_DATEI, lade_profil, lies_einstellungen  # noqa: E402

API = os.environ.get("RUNPOD_API_URL", "https://api.runpod.io/v2")
USER_AGENT = "SwarmLLM_Benchmark-runpod/1.0"
KOSTEN_DATEI = REPO / "results" / "kosten.csv"
START_SKRIPT = REPO / "server" / "start-im-container.sh"

# Preise für 2 Karten pro Stunde, nur für die Schätzung VOR dem Anlegen.
# Quelle: computeprices.com, Stand 15.11.2026 (1,64 / 2,69 $ pro Karte).
# Nach dem Anlegen zählt der Preis, den RunPod für den Pod meldet.
PREIS_SCHAETZUNG_PRO_KARTE = {"COMMUNITY": 1.64, "SECURE": 2.69}
STANDARD_MINUTEN = {"schnell": 90, "voll": 210}


# ---------------------------------------------------------------------------
# Einstellungen aus benchmark.conf bzw. .env (nie im Repo)
# ---------------------------------------------------------------------------
def einstellung(name: str, standard: str = "") -> str:
    return os.environ.get(name) or lies_einstellungen().get(name) or standard


# ---------------------------------------------------------------------------
# HTTP gegen die RunPod-API
# ---------------------------------------------------------------------------
def api(methode: str, pfad: str, daten: dict | None = None) -> dict | list:
    key = einstellung("RUNPOD_API_KEY")
    if not key:
        raise SystemExit("FEHLER: RUNPOD_API_KEY fehlt in benchmark.conf.")
    anfrage = urllib.request.Request(  # noqa: S310 (feste https-URL)
        API + pfad,
        method=methode,
        data=json.dumps(daten).encode() if daten is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:  # noqa: S310
            roh = antwort.read()
            return json.loads(roh) if roh else {}
    except urllib.error.HTTPError as fehler:
        raise SystemExit(f"RunPod-API {methode} {pfad}: HTTP {fehler.code} {fehler.read().decode()[:500]}") from None


def http_get(url: str, key: str = "", timeout: float = 10) -> tuple[int, bytes]:
    """Einfacher GET gegen Pod-Endpunkte (Status-Seite, vLLM)."""
    anfrage = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    if key:
        anfrage.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:  # noqa: S310
            return antwort.status, antwort.read()
    except urllib.error.HTTPError as fehler:
        return fehler.code, b""
    except (urllib.error.URLError, OSError):
        return 0, b""


# ---------------------------------------------------------------------------
# Pod-Datei (aktueller Lauf) und Kostenbuch
# ---------------------------------------------------------------------------
def lies_pod() -> dict:
    if not POD_DATEI.is_file():
        raise SystemExit("Kein aktueller Pod (runpod/.aktueller-pod.json fehlt).")
    return json.loads(POD_DATEI.read_text(encoding="utf-8"))


def schreibe_pod(daten: dict) -> None:
    POD_DATEI.write_text(json.dumps(daten, indent=2) + "\n", encoding="utf-8")
    POD_DATEI.chmod(0o600)  # enthält den API-Key des Laufs


def verbraucht() -> float:
    if not KOSTEN_DATEI.is_file():
        return 0.0
    with KOSTEN_DATEI.open(encoding="utf-8") as f:
        return sum(float(z["kosten_usd"]) for z in csv.DictReader(f))


def verbuche(zeile: dict) -> None:
    KOSTEN_DATEI.parent.mkdir(parents=True, exist_ok=True)
    neu = not KOSTEN_DATEI.is_file()
    felder = ["datum_utc", "pod_id", "profil", "cloud", "gpu", "kosten_pro_stunde", "minuten", "kosten_usd", "grund"]
    with KOSTEN_DATEI.open("a", encoding="utf-8", newline="") as f:
        schreiber = csv.DictWriter(f, fieldnames=felder)
        if neu:
            schreiber.writeheader()
        schreiber.writerow({k: zeile.get(k, "") for k in felder})


# ---------------------------------------------------------------------------
# Watchdog: terminiert den Pod nach Ablauf der Zeit, auch wenn niemand zuschaut.
# systemd-run überlebt das Schließen des Terminals; nohup ist der Notbehelf.
# ---------------------------------------------------------------------------
def starte_watchdog(pod_id: str, minuten: int) -> str:
    befehl = [sys.executable, str(Path(__file__).resolve()), "down", "--pod", pod_id, "--grund", "watchdog"]
    if shutil.which("systemd-run"):
        einheit = f"swarmllm-watchdog-{pod_id}"
        lauf = subprocess.run(
            [
                "systemd-run",
                "--user",
                f"--unit={einheit}",
                f"--on-active={minuten}m",
                f"--working-directory={REPO}",
                *befehl,
            ],
            capture_output=True,
            text=True,
        )
        if lauf.returncode == 0:
            return f"systemd-Timer {einheit} (stoppen: systemctl --user stop {einheit}.timer)"
    log = REPO / "runpod" / f"watchdog-{pod_id}.log"
    with log.open("w") as ausgabe:
        subprocess.Popen(  # noqa: S603
            ["/bin/sh", "-c", f'sleep {minuten * 60} && exec "$@"', "watchdog", *befehl],
            stdout=ausgabe,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=REPO,
        )
    return (
        f"Hintergrundprozess (nohup-Ersatz), Log: {log.relative_to(REPO)} – "
        "überlebt keinen Neustart oder Ruhezustand des Steuerrechners!"
    )


def stoppe_watchdog(pod_id: str) -> None:
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", "stop", f"swarmllm-watchdog-{pod_id}.timer"], capture_output=True)


# ---------------------------------------------------------------------------
# Profil prüfen: nur gepinnte, freigegebene Profile dürfen Geld kosten
# ---------------------------------------------------------------------------
def pruefe_profil(profil) -> list[str]:
    probleme = []
    if profil.get("PROFIL_STATUS", "bereit") != "bereit":
        probleme.append(f"Profil hat Status '{profil.get('PROFIL_STATUS')}' (siehe Kommentar im Profil)")
    if not profil.get("MODEL_ID") or len(profil.get("MODEL_REVISION")) != 40:
        probleme.append("Modell nicht gepinnt: python3 profiles/pin.py " + profil.name)
    if "@sha256:" not in profil.get("VLLM_IMAGE"):
        probleme.append("Image nicht per Digest gepinnt: python3 profiles/pin.py " + profil.name)
    return probleme


# ---------------------------------------------------------------------------
# Befehle
# ---------------------------------------------------------------------------
def befehl_gpus(_args) -> int:
    katalog = api("GET", "/catalog/gpus")
    eintraege = katalog.get("data", katalog) if isinstance(katalog, dict) else katalog
    treffer = [g for g in eintraege if "6000" in json.dumps(g)] or eintraege
    for g in treffer:
        print(json.dumps(g, ensure_ascii=False))
    print("\nDie passende 'id' als RUNPOD_GPU_ID in benchmark.conf eintragen.")
    return 0


def befehl_kosten(_args) -> int:
    print(f"Bisher verbucht (results/kosten.csv): {verbraucht():.2f} $")
    print("Maßgeblich ist die Abrechnung im RunPod-Konto (Billing).")
    return 0


def befehl_up(args) -> int:
    profil = lade_profil(args.profil)
    probleme = pruefe_profil(profil)
    gpu_id = einstellung("RUNPOD_GPU_ID")
    if not gpu_id:
        probleme.append("RUNPOD_GPU_ID fehlt in benchmark.conf (python3 runpod/rp.py gpus)")
    if POD_DATEI.is_file() and not args.trocken:
        probleme.append("Es läuft schon ein Pod (runpod/.aktueller-pod.json). Erst: python3 runpod/rp.py down")

    cloud = (args.cloud or einstellung("RUNPOD_CLOUD", "COMMUNITY")).upper()
    karten = int(profil.get("GPU_ANZAHL", "2"))
    minuten = args.minuten or int(einstellung("POD_MAX_MINUTES", str(STANDARD_MINUTEN[args.stufe])))
    schaetzung = PREIS_SCHAETZUNG_PRO_KARTE.get(cloud, 2.69) * karten * minuten / 60

    print(f"Profil:   {profil.name} ({profil.get('MODEL_ID') or profil.get('MODEL_QUELLE')})")
    print(f"Hardware: {karten}× {gpu_id or '?'}, {cloud}, mind. {profil.get('HOST_RAM_MIN_GB', '-')} GB RAM")
    print(f"Laufzeit: höchstens {minuten} Min. (Watchdog), geschätzt bis {schaetzung:.2f} $")
    print(f"Bisher:   {verbraucht():.2f} $ verbucht (results/kosten.csv)")

    key = secrets.token_hex(24)
    disk = int(profil.get("DISK_GB") or max(100, int(float(profil.get("MODELL_GROESSE_GB") or 0) * 1.3) + 50))
    ram_pro_gpu = int(int(profil.get("HOST_RAM_MIN_GB") or 0) / karten) or None
    umgebung = {
        "VLLM_API_KEY": key,
        "MODEL_ID": profil.get("MODEL_ID"),
        "MODEL_REVISION": profil.get("MODEL_REVISION"),
        "SERVED_NAME": profil.served_name,
        "SERVE_ARGS": profil.get("SERVE_ARGS"),
        "SERVE_ENV": profil.get("SERVE_ENV"),
        "SPEC_CONFIG": profil.get("SPEC_CONFIG"),
        "KV_CPU_OFFLOAD_GB": profil.get("KV_CPU_OFFLOAD_GB"),
        "P2P_PFLICHT": profil.get("P2P_PFLICHT", "1"),
        "START_SKRIPT_B64": base64.b64encode(START_SKRIPT.read_bytes()).decode(),
    }
    if einstellung("HF_TOKEN"):
        umgebung["HF_TOKEN"] = einstellung("HF_TOKEN")
    gpu: dict = {"id": gpu_id, "count": karten}
    if ram_pro_gpu:
        gpu["minRamPerGpu"] = ram_pro_gpu
    if profil.get("HOST_VCPU_PRO_GPU"):
        gpu["minVcpuCountPerGpu"] = int(profil.get("HOST_VCPU_PRO_GPU"))
    koerper = {
        "name": f"swarmllm-{profil.name}",
        "image": profil.get("VLLM_IMAGE"),
        "cloud": cloud,
        "gpu": gpu,
        "disk": disk,
        "ports": ["8000/tcp", "8001/tcp"],  # direkter TCP-Port statt HTTP-Proxy (Erfahrung B300)
        "env": {k: v for k, v in umgebung.items() if v},
        "entrypoint": ["/bin/bash", "-c"],
        "cmd": ['echo "$START_SKRIPT_B64" | base64 -d > /start.sh && exec bash /start.sh'],
    }

    if args.trocken:
        anzeige = json.loads(json.dumps(koerper))
        anzeige["env"]["VLLM_API_KEY"] = "<neu erzeugt>"
        anzeige["env"]["START_SKRIPT_B64"] = f"<{len(umgebung['START_SKRIPT_B64'])} Zeichen>"
        anzeige["env"].pop("HF_TOKEN", None)
        print("\nTrockenlauf – diese Anfrage würde an POST /v2/pods gehen:")
        print(json.dumps(anzeige, indent=2, ensure_ascii=False))
        for p in probleme:
            print(f"Hinweis: {p}")
        return 0
    if probleme:
        for p in probleme:
            print(f"FEHLER: {p}", file=sys.stderr)
        return 1
    if not args.ja and input("\nPod jetzt anlegen? Das kostet Geld. Tippe 'ja': ").strip().lower() != "ja":
        print("Abgebrochen.")
        return 1

    pod = api("POST", "/pods", koerper)
    pod_id = pod["id"]
    preis = float(pod.get("cost") or 0)
    schreibe_pod(
        {
            "pod_id": pod_id,
            "profil": profil.name,
            "api_key": key,
            "kosten_pro_stunde": preis,
            "gpu": f"{karten}x {gpu_id}",
            "cloud": cloud,
            "rechenzentrum": pod.get("dataCenterId"),
            "angelegt_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "angelegt_monoton": time.time(),
            "max_minuten": minuten,
        }
    )
    print(f"\nPod {pod_id} angelegt, {preis:.2f} $/h laut RunPod.")
    print(f"Watchdog: {starte_watchdog(pod_id, minuten)}")
    print("Weiter mit: python3 runpod/rp.py warten")
    return 0


def oeffentliche_adresse(pod: dict, privat: int) -> str | None:
    for port in (pod.get("runtime") or {}).get("ports") or []:
        if int(port.get("private", 0)) == privat and port.get("public") and port.get("ip"):
            return f"http://{port['ip']}:{port['public']}"
    return None


def befehl_warten(args) -> int:
    daten = lies_pod()
    start = daten.get("angelegt_monoton", time.time())
    letzte_phase = ""
    while True:
        pod = api("GET", f"/pods/{daten['pod_id']}")
        if pod.get("status") in ("EXITED", "ERROR", "TERMINATED"):
            print(f"Pod-Status {pod.get('status')} – abbrechen und löschen: python3 runpod/rp.py down")
            return 1
        vllm = oeffentliche_adresse(pod, 8000)
        status_url = oeffentliche_adresse(pod, 8001)
        if status_url:
            code, roh = http_get(status_url + "/status.json")
            if code == 200:
                s = json.loads(roh)
                phase = f"{s['phase']}: {s['detail']}"
                if phase != letzte_phase:
                    print(f"[{(time.time() - start) / 60:5.1f} min] {phase}")
                    letzte_phase = phase
                if s["phase"] == "fehler":
                    print("Start fehlgeschlagen. Details: python3 runpod/rp.py check, danach down.")
                    return 1
        if vllm and http_get(vllm + "/v1/models", daten["api_key"])[0] == 200:
            daten["url"] = vllm + "/v1"
            daten["status_url"] = status_url
            daten["kaltstart_min"] = round((time.time() - start) / 60, 1)
            schreibe_pod(daten)
            print(f"Bereit nach {daten['kaltstart_min']} min: {daten['url']}")
            print(
                "Weiter mit: python3 runpod/rp.py check  und dann  "
                f"python3 -m bench run alle --profil {daten['profil']}"
            )
            return 0
        time.sleep(args.intervall)


def befehl_check(_args) -> int:
    daten = lies_pod()
    profil = lade_profil(daten["profil"])
    pod = api("GET", f"/pods/{daten['pod_id']}")
    status_url = oeffentliche_adresse(pod, 8001)
    host = {}
    if status_url:
        code, roh = http_get(status_url + "/host.json")
        host = json.loads(roh) if code == 200 else {}
    befunde = []

    # Host: P2P, CPU-Modell, RAM (Werte aus dem Profil)
    if not host:
        befunde.append(("host_daten", False, "Status-Seite nicht erreichbar"))
    else:
        befunde.append(("p2p", bool(host.get("p2p_ok")), json.dumps(host.get("p2p"))[:200]))
        muster = profil.get("HOST_CPU_MUSTER")
        cpu = host.get("cpu_modell", "")
        befunde.append(("cpu", not muster or bool(re.search(muster, cpu, re.I)), f"{cpu} (verlangt: {muster or '-'})"))
        ram_min = float(profil.get("HOST_RAM_MIN_GB") or 0)
        befunde.append(
            ("ram", host.get("ram_gb", 0) >= ram_min * 0.95, f"{host.get('ram_gb')} GB (verlangt: {ram_min or '-'})")
        )
        befunde.append(("gpus", True, host.get("gpus", "")))

    # vLLM: richtiges Modell, Key-Schutz (Regel 8)
    url = daten.get("url")
    if url:
        code, roh = http_get(url + "/models", daten["api_key"])
        namen = [m.get("id") for m in json.loads(roh or b"{}").get("data", [])] if code == 200 else []
        befunde.append(("modell", profil.served_name in namen, f"angeboten: {namen}"))
        ohne_key = http_get(url + "/models")[0]
        befunde.append(("key_schutz", not (200 <= ohne_key < 300), f"ohne Key: HTTP {ohne_key}"))
    else:
        befunde.append(("vllm", False, "noch nicht bereit (python3 runpod/rp.py warten)"))

    for name, ok, detail in befunde:
        print(f"{'ok    ' if ok else 'FEHLER'} {name}: {detail}")
    ergebnis_ordner = REPO / "results" / profil.name / "pod-check"
    ergebnis_ordner.mkdir(parents=True, exist_ok=True)
    stempel = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (ergebnis_ordner / f"{stempel}.json").write_text(
        json.dumps(
            {
                "pod_id": daten["pod_id"],
                "kosten_pro_stunde": daten.get("kosten_pro_stunde"),
                "rechenzentrum": daten.get("rechenzentrum"),
                "kaltstart_min": daten.get("kaltstart_min"),
                "host": host,
                "befunde": [{"name": n, "ok": o, "detail": d} for n, o, d in befunde],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    if not all(ok for _, ok, _ in befunde):
        print("\nHost oder Server ungeeignet. Empfehlung: sofort löschen -> python3 runpod/rp.py down")
        return 1
    print("\nAlles in Ordnung.")
    return 0


def befehl_status(_args) -> int:
    pods = api("GET", "/pods")
    liste = pods.get("data", pods) if isinstance(pods, dict) else pods
    if not liste:
        print("Keine Pods.")
    for p in liste:
        print(
            f"{p.get('id')}  {p.get('name')}  {p.get('status')}  {p.get('cost')} $/h  "
            f"seit {p.get('startedAt') or p.get('createdAt')}"
        )
    return 0


def minuten_seit(iso: str | None, ersatz: float) -> float:
    if iso:
        try:
            return (datetime.now(UTC) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 60
        except ValueError:
            pass
    return (time.time() - ersatz) / 60


def terminiere(pod_id: str, grund: str, daten: dict | None) -> None:
    try:
        pod = api("GET", f"/pods/{pod_id}")
    except SystemExit:
        pod = {}
    api("DELETE", f"/pods/{pod_id}")
    daten = daten or {}
    preis = float(daten.get("kosten_pro_stunde") or pod.get("cost") or 0)
    minuten = minuten_seit(
        pod.get("createdAt") or daten.get("angelegt_utc"), daten.get("angelegt_monoton", time.time())
    )
    verbuche(
        {
            "datum_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "pod_id": pod_id,
            "profil": daten.get("profil", pod.get("name", "")),
            "cloud": daten.get("cloud", pod.get("cloud", "")),
            "gpu": daten.get("gpu", ""),
            "kosten_pro_stunde": f"{preis:.3f}",
            "minuten": f"{minuten:.1f}",
            "kosten_usd": f"{preis * minuten / 60:.3f}",
            "grund": grund,
        }
    )
    stoppe_watchdog(pod_id)
    print(
        f"Pod {pod_id} terminiert nach {minuten:.0f} min, ≈ {preis * minuten / 60:.2f} $ "
        "verbucht in results/kosten.csv."
    )


def befehl_down(args) -> int:
    daten = json.loads(POD_DATEI.read_text(encoding="utf-8")) if POD_DATEI.is_file() else None
    pod_id = args.pod or (daten or {}).get("pod_id")
    if not pod_id:
        raise SystemExit("Keine Pod-ID (--pod) und kein aktueller Pod.")
    terminiere(pod_id, args.grund, daten if daten and daten.get("pod_id") == pod_id else None)
    if daten and daten.get("pod_id") == pod_id:
        POD_DATEI.unlink()
    print("Unter RunPod → Billing kontrollieren, dass nichts mehr läuft (Erfahrung B300).")
    return 0


def befehl_down_alle(_args) -> int:
    pods = api("GET", "/pods")
    for p in pods.get("data", pods) if isinstance(pods, dict) else pods:
        if p.get("status") != "TERMINATED":
            terminiere(p["id"], "notbremse", None)
    if POD_DATEI.is_file():
        POD_DATEI.unlink()
    return 0


# ---------------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    befehle = ap.add_subparsers(dest="befehl", required=True)
    befehle.add_parser("gpus").set_defaults(func=befehl_gpus)
    befehle.add_parser("kosten").set_defaults(func=befehl_kosten)
    up = befehle.add_parser("up")
    up.add_argument("profil")
    up.add_argument("--stufe", choices=["schnell", "voll"], default="schnell")
    up.add_argument("--minuten", type=int, help="Watchdog-Zeit; Standard aus POD_MAX_MINUTES bzw. Stufe")
    up.add_argument("--cloud", choices=["COMMUNITY", "SECURE"])
    up.add_argument("--trocken", action="store_true", help="nur anzeigen, nichts anlegen")
    up.add_argument("--ja", action="store_true", help="ohne Rückfrage (nur wenn du sicher bist)")
    up.set_defaults(func=befehl_up)
    warten = befehle.add_parser("warten")
    warten.add_argument("--intervall", type=int, default=20)
    warten.set_defaults(func=befehl_warten)
    befehle.add_parser("check").set_defaults(func=befehl_check)
    befehle.add_parser("status").set_defaults(func=befehl_status)
    down = befehle.add_parser("down")
    down.add_argument("--pod")
    down.add_argument("--grund", default="manuell")
    down.set_defaults(func=befehl_down)
    befehle.add_parser("down-alle").set_defaults(func=befehl_down_alle)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
