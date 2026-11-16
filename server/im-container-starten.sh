#!/usr/bin/env bash
# Startet ein Modellprofil direkt IM laufenden Container – ohne docker run.
#
# Für Anbieter, bei denen man sich per SSH in den Container anmeldet, statt selbst
# Docker zu bedienen (z. B. Vast.ai im SSH-Modus mit dem vLLM-Image). Macht dasselbe
# wie server/lokal-starten.sh: Profil und benchmark.conf lesen, prüfen, dann das
# gemeinsame Startskript server/start-im-container.sh ausführen.
#
# Aufruf (im Container, im Repo-Ordner):
#   server/im-container-starten.sh <profil>
# Fortschritt: tail -f /tmp/swarmllm-start.log  oder  http://<host>:<port für 8001>/status.json
set -euo pipefail
cd "$(dirname "$0")/.."

PROFIL="${1:?Aufruf: server/im-container-starten.sh <profil>}"
DATEI="profiles/${PROFIL}/profile.env"
[[ -f "$DATEI" ]] || { echo "FEHLER: $DATEI fehlt." >&2; exit 1; }

# ---------------------------------------------------------------------------
# Profil laden (im Repo reviewt) und eigene Werte aus benchmark.conf lesen.
# Aus benchmark.conf nur die zwei benötigten Werte – kein blindes source.
# ---------------------------------------------------------------------------
# shellcheck disable=SC1090
source "$DATEI"
KONF=benchmark.conf
[[ -f "$KONF" ]] || KONF=.env
wert() { grep -E "^$1=" "$KONF" 2>/dev/null | tail -1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//"; }
HF_TOKEN="${HF_TOKEN:-$(wert HF_TOKEN)}"
VLLM_API_KEY="${VLLM_API_KEY:-$(wert VLLM_API_KEY)}"

# ---------------------------------------------------------------------------
# Prüfungen wie in lokal-starten.sh: kein Entwurf, gepinnt (Regel 4), Key (Regel 8).
# Das Image ist hier schon gestartet – geprüft wird nur die Modell-Revision.
# ---------------------------------------------------------------------------
[[ "${PROFIL_STATUS:-bereit}" == "bereit" ]] || { echo "FEHLER: Profil ist '${PROFIL_STATUS}'." >&2; exit 1; }
[[ "${MODEL_REVISION:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "FEHLER: Profil nicht gepinnt (profiles/pin.py $PROFIL)." >&2; exit 1; }
[[ -n "${VLLM_API_KEY:-}" ]] || { echo "FEHLER: VLLM_API_KEY fehlt in benchmark.conf." >&2; exit 1; }

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
