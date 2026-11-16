#!/usr/bin/env bash
# Startet ein Modellprofil direkt IM laufenden Container – ohne docker run.
#
# Für Anbieter, bei denen man sich per SSH in den Container anmeldet, statt selbst
# Docker zu bedienen (z. B. Vast.ai im SSH-Modus mit dem vLLM-Image). Macht dasselbe
# wie server/lokal-starten.sh: Profil und benchmark.conf lesen, prüfen, dann das
# gemeinsame Startskript server/start-im-container.sh ausführen.
#
# Auf Vast.ai startet es zusätzlich den Auto-Stopp (Regel 5, server/vast-watchdog.sh)
# und zeigt die Adresse, die auf dem Laptop als BENCH_ZIEL_URL einzutragen ist.
#
# Aufruf (im Container, im Repo-Ordner):
#   server/im-container-starten.sh <profil> [--minuten N]
#     --minuten N   Auto-Stopp nach N Minuten (Standard: POD_MAX_MINUTES aus
#                   benchmark.conf, sonst 90)
# Fortschritt: tail -f /tmp/swarmllm-start.log  oder  http://<host>:<port für 8001>/status.json
set -euo pipefail
cd "$(dirname "$0")/.."

# ---------------------------------------------------------------------------
# Aufruf lesen: Profil, optional --minuten
# ---------------------------------------------------------------------------
PROFIL="${1:?Aufruf: server/im-container-starten.sh <profil> [--minuten N]}"
MINUTEN_ARG=""
if [[ "${2:-}" == "--minuten" ]]; then
  MINUTEN_ARG="${3:?--minuten braucht eine Zahl}"
fi
DATEI="profiles/${PROFIL}/profile.env"
[[ -f "$DATEI" ]] || { echo "FEHLER: $DATEI fehlt." >&2; exit 1; }

# ---------------------------------------------------------------------------
# Profil laden (im Repo reviewt) und eigene Werte aus benchmark.conf lesen.
# Aus benchmark.conf nur die benötigten Werte – kein blindes source.
# ---------------------------------------------------------------------------
# shellcheck disable=SC1090
source "$DATEI"
KONF=benchmark.conf
[[ -f "$KONF" ]] || KONF=.env
wert() { grep -E "^$1=" "$KONF" 2>/dev/null | tail -1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//"; }
HF_TOKEN="${HF_TOKEN:-$(wert HF_TOKEN)}"
VLLM_API_KEY="${VLLM_API_KEY:-$(wert VLLM_API_KEY)}"
MINUTEN="${MINUTEN_ARG:-$(wert POD_MAX_MINUTES)}"
MINUTEN="${MINUTEN:-90}"

# ---------------------------------------------------------------------------
# Prüfungen wie in lokal-starten.sh: kein Entwurf, gepinnt (Regel 4), Key (Regel 8).
# Das Image ist hier schon gestartet – geprüft wird nur die Modell-Revision.
# ---------------------------------------------------------------------------
[[ "${PROFIL_STATUS:-bereit}" == "bereit" ]] || { echo "FEHLER: Profil ist '${PROFIL_STATUS}'." >&2; exit 1; }
[[ "${MODEL_REVISION:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "FEHLER: Profil nicht gepinnt (profiles/pin.py $PROFIL)." >&2; exit 1; }
[[ -n "${VLLM_API_KEY:-}" ]] || { echo "FEHLER: VLLM_API_KEY fehlt in benchmark.conf." >&2; exit 1; }

# ---------------------------------------------------------------------------
# Vast.ai erkennen: Vast setzt CONTAINER_ID in jeder Instanz. In SSH-Sitzungen
# fehlt sie manchmal – dann aus der Umgebung des Container-Hauptprozesses lesen.
# ---------------------------------------------------------------------------
vast_wert() {
  local name="$1"
  if [[ -n "${!name:-}" ]]; then
    printf '%s' "${!name}"
  elif [[ -r /proc/1/environ ]]; then
    tr '\0' '\n' 2>/dev/null </proc/1/environ | grep -E "^${name}=" | head -1 | cut -d= -f2- || true
  fi
}
AUF_VAST=""
if [[ -n "$(vast_wert CONTAINER_ID)" ]]; then AUF_VAST=1; fi

# ---------------------------------------------------------------------------
# Auto-Stopp (Regel 5) vor dem Start: Auf Vast.ai löscht sich die Instanz nach
# Ablauf selbst. Anderswo gibt es von hier aus keinen – dann laut warnen.
# ---------------------------------------------------------------------------
if [[ -n "$AUF_VAST" ]]; then
  server/vast-watchdog.sh "$MINUTEN"
else
  echo "WARNUNG: Keine Vast.ai-Instanz erkannt – kein Auto-Stopp aus diesem Skript."
  echo "         Beim Anbieter eine maximale Laufzeit setzen (Regel 5)."
fi

# ---------------------------------------------------------------------------
# Werte für das Startskript bereitstellen und es im Hintergrund starten,
# damit es weiterläuft, wenn die SSH-Verbindung endet.
# ---------------------------------------------------------------------------
export VLLM_API_KEY HF_TOKEN MODEL_ID MODEL_REVISION SERVED_NAME
export SERVE_ARGS="${SERVE_ARGS:-}" SERVE_ENV="${SERVE_ENV:-}" SPEC_CONFIG="${SPEC_CONFIG:-}"
export KV_CPU_OFFLOAD_GB="${KV_CPU_OFFLOAD_GB:-}" P2P_PFLICHT="${P2P_PFLICHT:-1}"
export MODELL_ORDNER="${MODELL_ORDNER:-/workspace/modelle}"

nohup bash server/start-im-container.sh >/tmp/swarmllm-start.log 2>&1 &
echo "Gestartet (PID $!). Fortschritt: tail -f /tmp/swarmllm-start.log"

# ---------------------------------------------------------------------------
# Auf Vast.ai: Adresse für den Laptop anzeigen. Vast bildet Port 8000 auf einen
# äußeren Port ab und nennt ihn in VAST_TCP_PORT_8000, die IP in PUBLIC_IPADDR.
# ---------------------------------------------------------------------------
if [[ -n "$AUF_VAST" ]]; then
  IP="$(vast_wert PUBLIC_IPADDR)"
  PORT_API="$(vast_wert VAST_TCP_PORT_8000)"
  PORT_STATUS="$(vast_wert VAST_TCP_PORT_8001)"
  if [[ -n "$IP" && -n "$PORT_API" ]]; then
    echo
    echo "Auf dem Laptop in benchmark.conf eintragen:"
    echo "  BENCH_ZIEL_URL=http://${IP}:${PORT_API}/v1"
    if [[ -n "$PORT_STATUS" ]]; then echo "Status-Seite: http://${IP}:${PORT_STATUS}/status.json"; fi
  else
    echo "Port 8000 ist nicht nach außen freigegeben – Docker-Option -p 8000:8000 beim Anlegen vergessen?"
  fi
fi
