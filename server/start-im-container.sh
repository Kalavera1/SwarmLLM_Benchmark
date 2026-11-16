#!/usr/bin/env bash
# Startskript, das IM vLLM-Container läuft – egal ob RunPod, Vast.ai oder eigener Server.
#
# Ablauf:
#   1. Status-Seite auf Port 8001 starten (nur Hostdaten und Phase, keine Secrets)
#   2. Host prüfen: GPUs, P2P zwischen den Karten (inkl. Datenvergleich), CPU, RAM, /dev/shm, Disk
#   3. Gepinnte Modell-Revision herunterladen (überspringt, wenn schon vorhanden)
#   4. vLLM starten, warten bis gesund, Phase "bereit"
#   5. Endet vLLM unerwartet: Phase "fehler", Container bleibt stehen (kein Neustart-
#      Kreislauf mit erneutem Download, der Geld kostet). Gelöscht wird von außen.
#
# Erwartete Umgebungsvariablen (setzt runpod/rp.py bzw. server/lokal-starten.sh):
#   VLLM_API_KEY      Pflicht (Regel 8); vLLM liest ihn selbst aus der Umgebung
#   MODEL_ID, MODEL_REVISION, SERVED_NAME, SERVE_ARGS
#   optional: SERVE_ENV, SPEC_CONFIG, HF_TOKEN, KV_CPU_OFFLOAD_GB, P2P_PFLICHT (Standard 1),
#             MODELL_ORDNER (Standard /modelle), STATUS_PORT (Standard 8001)
set -uo pipefail

STATUS_ORDNER=/tmp/status
STATUS_PORT="${STATUS_PORT:-8001}"
MODELL_ORDNER="${MODELL_ORDNER:-/modelle}"
mkdir -p "$STATUS_ORDNER" "$MODELL_ORDNER"

# ---------------------------------------------------------------------------
# Status schreiben: Phase und Detail als JSON, lesbar über http://<host>:8001/status.json
# ---------------------------------------------------------------------------
status() {
  python3 - "$1" "${2:-}" <<'PY'
import json, sys, time
json.dump({"phase": sys.argv[1], "detail": sys.argv[2], "zeit": time.time()}, open("/tmp/status/status.json", "w"))
PY
  echo "[start] $(date -u +%H:%M:%S) $1 ${2:-}"
}

fehler_und_warten() {
  status "fehler" "$1"
  echo "[start] Container bleibt stehen, damit der Status lesbar ist. Pod/Container von außen löschen."
  sleep infinity
}

# ---------------------------------------------------------------------------
# Schritt 1: Status-Seite. Python ist im vLLM-Image immer vorhanden.
# ---------------------------------------------------------------------------
python3 -m http.server "$STATUS_PORT" --directory "$STATUS_ORDNER" >/dev/null 2>&1 &
status "start" "Container läuft"

# Pflichtwerte prüfen, bevor irgendetwas Zeit kostet
[[ -n "${VLLM_API_KEY:-}" ]] || fehler_und_warten "VLLM_API_KEY fehlt (Regel 8)"
for name in MODEL_ID MODEL_REVISION SERVED_NAME; do
  [[ -n "${!name:-}" ]] || fehler_und_warten "$name fehlt"
done

# ---------------------------------------------------------------------------
# Schritt 2: Host prüfen und als host.json ablegen
# P2P-Test: Kann jede Karte direkt auf jede andere zugreifen, und kommen die
# Daten unverfälscht an? (Manche Boards korrumpieren P2P still.)
# ---------------------------------------------------------------------------
status "hostcheck" "prüfe GPUs, P2P, CPU, RAM"
nvidia-smi topo -m >"$STATUS_ORDNER/topologie.txt" 2>&1 || true
python3 - <<'PY'
import json, os, re, shutil, subprocess

def befehl(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as fehler:
        return f"Fehler: {fehler}"

ergebnis = {}
ergebnis["gpus"] = befehl("nvidia-smi", "--query-gpu=name,memory.total,power.limit,driver_version,pcie.link.gen.current,pcie.link.width.current", "--format=csv,noheader")
cpu = befehl("lscpu")
ergebnis["cpu_modell"] = next((z.split(":", 1)[1].strip() for z in cpu.splitlines() if z.startswith("Model name")), "unbekannt")
ergebnis["cpu_kerne_sichtbar"] = os.cpu_count()
meminfo = open("/proc/meminfo").read()
ergebnis["ram_gb"] = round(int(re.search(r"MemTotal:\s+(\d+)", meminfo).group(1)) / 1024 / 1024, 1)
ergebnis["shm_gb"] = round(shutil.disk_usage("/dev/shm").total / 1e9, 1)
ergebnis["disk_frei_gb"] = round(shutil.disk_usage(os.environ.get("MODELL_ORDNER", "/modelle")).free / 1e9, 1)
ergebnis["blockgeraete"] = befehl("lsblk", "-d", "-o", "NAME,ROTA,SIZE,MODEL")

# RAM-Bandbreite grob messen: 4 GB im Arbeitsspeicher kopieren (lesen + schreiben),
# mit allen sichtbaren Kernen. Wichtig für Modelle mit CPU-Experten (DeepSeek V4.1
# Flash): Ihr Tempo hängt fast direkt an diesem Wert. Zum Vergleich: EPYC 9745 mit
# 12 Kanälen DDR5 hat laut Händler bis 576 GB/s (theoretisch).
try:
    import time
    import torch
    torch.set_num_threads(os.cpu_count() or 1)
    quelle = torch.empty(4 * 1024**3, dtype=torch.uint8)
    ziel = torch.empty_like(quelle)
    ziel.copy_(quelle)  # erster Durchlauf zählt nicht (Seiten anlegen)
    messungen = []
    for _ in range(3):
        start = time.perf_counter()
        ziel.copy_(quelle)
        messungen.append(2 * quelle.numel() / (time.perf_counter() - start) / 1e9)
    ergebnis["ram_bandbreite_gb_s"] = round(max(messungen), 1)
    del quelle, ziel
except Exception as fehler:
    ergebnis["ram_bandbreite_gb_s"] = f"Fehler: {fehler}"

try:
    import torch
    n = torch.cuda.device_count()
    paare = {}
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            zugriff = torch.cuda.can_device_access_peer(a, b)
            daten = torch.randn(64 * 1024 * 1024 // 4, device=f"cuda:{a}")
            kopie = daten.to(f"cuda:{b}").to(f"cuda:{a}")
            paare[f"{a}->{b}"] = {"zugriff": zugriff, "daten_gleich": bool(torch.equal(daten, kopie))}
    ergebnis["p2p"] = paare
    ergebnis["p2p_ok"] = bool(paare) and all(p["zugriff"] and p["daten_gleich"] for p in paare.values())
except Exception as fehler:
    ergebnis["p2p"] = f"Fehler: {fehler}"
    ergebnis["p2p_ok"] = False

json.dump(ergebnis, open("/tmp/status/host.json", "w"), indent=2)
print(json.dumps(ergebnis, indent=2))
PY

if [[ "${P2P_PFLICHT:-1}" == "1" ]] && ! grep -q '"p2p_ok": true' "$STATUS_ORDNER/host.json"; then
  fehler_und_warten "P2P zwischen den Karten fehlt oder ist fehlerhaft – Host verwerfen"
fi

# ---------------------------------------------------------------------------
# Schritt 3: Modell herunterladen (genau die gepinnte Revision, Regel 4)
# Fortschritt: Größe des Ordners, alle 15 s in den Status geschrieben.
# ---------------------------------------------------------------------------
ZIEL="$MODELL_ORDNER/${MODEL_ID//\//__}@${MODEL_REVISION:0:12}"
if [[ -f "$ZIEL/.vollstaendig" ]]; then
  status "download" "bereits vorhanden: $ZIEL"
else
  status "download" "$MODEL_ID@$MODEL_REVISION"
  (
    while sleep 15; do
      status "download" "$(du -sh "$ZIEL" 2>/dev/null | cut -f1) geladen"
    done
  ) &
  FORTSCHRITT=$!
  if ! python3 - "$MODEL_ID" "$MODEL_REVISION" "$ZIEL" <<'PY'; then
import os, sys
from huggingface_hub import snapshot_download
snapshot_download(repo_id=sys.argv[1], revision=sys.argv[2], local_dir=sys.argv[3],
                  token=os.environ.get("HF_TOKEN") or None, max_workers=16)
PY
    kill "$FORTSCHRITT" 2>/dev/null
    fehler_und_warten "Download fehlgeschlagen"
  fi
  kill "$FORTSCHRITT" 2>/dev/null
  touch "$ZIEL/.vollstaendig"
fi

# ---------------------------------------------------------------------------
# Schritt 4: vLLM starten
#   SERVE_ARGS    einfache Argumente, durch Leerzeichen getrennt (ohne JSON)
#   SPEC_CONFIG   JSON für --speculative-config, eigene Variable, damit keine
#                 Anführungszeichen verschachtelt werden müssen
#   SERVE_ENV     Umgebungsvariablen NAME=WERT, durch Leerzeichen getrennt
# Den Key liest vLLM aus VLLM_API_KEY – nicht als Argument, sonst stünde er im Log.
# ---------------------------------------------------------------------------
read -ra ARGUMENTE <<<"${SERVE_ARGS:-}"
if [[ -n "${SPEC_CONFIG:-}" ]]; then
  ARGUMENTE+=(--speculative-config "$SPEC_CONFIG")
fi
if [[ -n "${KV_CPU_OFFLOAD_GB:-}" ]]; then
  # KV-Cache zusätzlich im Arbeitsspeicher halten (Prefix-Cache auf der CPU)
  ARGUMENTE+=(--kv-offloading-size "$KV_CPU_OFFLOAD_GB")
fi
export VLLM_ENGINE_READY_TIMEOUT_S="${VLLM_ENGINE_READY_TIMEOUT_S:-3600}" # Erfahrung B300
read -ra UMGEBUNG <<<"${SERVE_ENV:-}"
for paar in "${UMGEBUNG[@]}"; do
  export "${paar?}"
done

status "laden" "vLLM startet"
vllm serve "$ZIEL" --served-model-name "$SERVED_NAME" --host 0.0.0.0 --port 8000 \
  --enable-prefix-caching "${ARGUMENTE[@]}" &
VLLM_PID=$!

# /health braucht keinen Key; Python statt curl, weil curl nicht in jedem Image ist
until python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" 2>/dev/null; do
  kill -0 "$VLLM_PID" 2>/dev/null || fehler_und_warten "vLLM beim Laden beendet (Log prüfen)"
  sleep 10
done
status "bereit" "$SERVED_NAME"

# ---------------------------------------------------------------------------
# Schritt 5: Läuft vLLM nicht mehr, Fehler melden und stehen bleiben
# ---------------------------------------------------------------------------
wait "$VLLM_PID"
fehler_und_warten "vLLM beendet mit Code $?"
