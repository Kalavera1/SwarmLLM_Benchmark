#!/usr/bin/env bash
# Startet ein Modellprofil per docker run auf einem Server mit Docker und GPUs –
# z. B. dem eigenen GPU-Server. Gleiches Startskript wie im RunPod-Pod, damit die
# Messungen vergleichbar sind.
#
# Aufruf (auf dem GPU-Server, im Repo-Ordner):
#   server/lokal-starten.sh <profil>          starten
#   server/lokal-starten.sh <profil> stopp    Container beenden und entfernen
#
# Danach auf dem Rechner, der misst:
#   BENCH_ZIEL_URL=http://<server>:8000/v1 python3 -m bench run alle --profil <profil>
# Status während des Starts: http://<server>:8001/status.json
set -euo pipefail
cd "$(dirname "$0")/.."

PROFIL="${1:?Aufruf: server/lokal-starten.sh <profil> [stopp]}"
AKTION="${2:-start}"
NAME="swarmllm-${PROFIL}"
DATEI="profiles/${PROFIL}/profile.env"
[[ -f "$DATEI" ]] || { echo "FEHLER: $DATEI fehlt." >&2; exit 1; }

# ---------------------------------------------------------------------------
# Stopp: Container entfernen; die heruntergeladenen Gewichte bleiben im Volume
# ---------------------------------------------------------------------------
if [[ "$AKTION" == "stopp" ]]; then
  docker rm -f "$NAME"
  exit 0
fi

# ---------------------------------------------------------------------------
# Profil und Zugangsdaten laden
# ---------------------------------------------------------------------------
# shellcheck disable=SC1090
source "$DATEI"
if [[ -f .env ]]; then
  # nur die Werte, die hier gebraucht werden (kein blindes source der .env)
  HF_TOKEN=$(grep -E '^HF_TOKEN=' .env | cut -d= -f2- || true)
  VLLM_API_KEY=$(grep -E '^VLLM_API_KEY=' .env | cut -d= -f2- || true)
fi

# Entwürfe (z. B. noch offener Weg) nicht starten
[[ "${PROFIL_STATUS:-bereit}" == "bereit" ]] || { echo "FEHLER: Profil ist '${PROFIL_STATUS}' – siehe Kommentar im Profil." >&2; exit 1; }

# Regel 4: nur gepinnte Profile starten
[[ "${MODEL_REVISION:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "FEHLER: Profil nicht gepinnt (profiles/pin.py $PROFIL)." >&2; exit 1; }
[[ "${VLLM_IMAGE:-}" == *@sha256:* ]] || { echo "FEHLER: VLLM_IMAGE ohne Digest (profiles/pin.py $PROFIL)." >&2; exit 1; }

# Regel 8: ohne Key kein Start. Derselbe Key steht in der .env des messenden Rechners.
[[ -n "${VLLM_API_KEY:-}" ]] || {
  echo "FEHLER: VLLM_API_KEY fehlt in .env. Erzeugen mit: openssl rand -hex 24" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Container starten
#   --ipc host / --shm-size   vLLM braucht viel Shared Memory für mehrere GPUs
#   --ulimit memlock=-1       gepinnter Host-Speicher (KV- und N-gram-Offloading)
#   Volume swarmllm-modelle   Gewichte überleben einen Neustart des Containers
# ---------------------------------------------------------------------------
docker run -d --name "$NAME" --gpus all --ipc host --shm-size 32g --ulimit memlock=-1 \
  -p 8000:8000 -p 8001:8001 \
  -v swarmllm-modelle:/modelle \
  -v "$PWD/server/start-im-container.sh:/start.sh:ro" \
  -e VLLM_API_KEY="$VLLM_API_KEY" -e HF_TOKEN="${HF_TOKEN:-}" \
  -e MODEL_ID="$MODEL_ID" -e MODEL_REVISION="$MODEL_REVISION" -e SERVED_NAME="$SERVED_NAME" \
  -e SERVE_ARGS="${SERVE_ARGS:-}" -e SERVE_ENV="${SERVE_ENV:-}" -e SPEC_CONFIG="${SPEC_CONFIG:-}" \
  -e KV_CPU_OFFLOAD_GB="${KV_CPU_OFFLOAD_GB:-}" -e P2P_PFLICHT="${P2P_PFLICHT:-1}" \
  --entrypoint /bin/bash "$VLLM_IMAGE" /start.sh

echo "Gestartet: $NAME. Fortschritt: docker logs -f $NAME  oder  http://<server>:8001/status.json"
