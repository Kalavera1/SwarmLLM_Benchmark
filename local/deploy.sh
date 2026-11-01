#!/usr/bin/env bash
# Deployt den Swarm-Stack "llm" auf dem Mediaserver.
#
# Was das Skript prüft und erledigt:
#   1. Swarm ist aktiv (sonst Hinweis auf `docker swarm init`)
#   2. LITELLM_IMAGE in images.env ist per Digest gepinnt (Regel 4)
#   3. Secrets existieren; fehlende werden angelegt:
#        litellm_master_key  aus LITELLM_MASTER_KEY in ../.env
#        mock_api_key        zufällig (niemand muss ihn kennen)
#   4. Config-Namen enthalten einen Hash des Inhalts, damit Änderungen an
#      config.yaml, start.sh oder mock_openai.py beim Deploy ankommen
#   5. Wartet, bis beide Services gesund laufen
#
# Aufruf:  ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

STACK=llm

fehler() {
  echo "FEHLER: $*" >&2
  exit 1
}

# 1. Swarm aktiv?
[[ "$(docker info --format '{{.Swarm.LocalNodeState}}')" == "active" ]] \
  || fehler "Swarm ist nicht aktiv. Einmalig ausführen: docker swarm init --advertise-addr <LAN-IP des Mediaservers>"

# 2. Gepinntes Image
set -a
# shellcheck source=local/images.env
source ./images.env
set +a
[[ "${LITELLM_IMAGE:-}" =~ @sha256:[0-9a-f]{64}$ ]] \
  || fehler "LITELLM_IMAGE in images.env ist nicht per Digest gepinnt. Zuerst ./pin-images.sh ausführen."

# 3. Secrets
secret_fehlt() { ! docker secret inspect "$1" >/dev/null 2>&1; }

if secret_fehlt litellm_master_key; then
  [[ -f ../.env ]] || fehler "../.env fehlt. Vorlage: cp ../.env.example ../.env, dann LITELLM_MASTER_KEY setzen."
  MASTER_KEY=$(grep -E '^LITELLM_MASTER_KEY=' ../.env | cut -d= -f2- || true)
  [[ ${#MASTER_KEY} -ge 24 ]] \
    || fehler "LITELLM_MASTER_KEY in ../.env fehlt oder ist kürzer als 24 Zeichen. Erzeugen mit: echo \"sk-\$(openssl rand -hex 24)\""
  printf '%s' "$MASTER_KEY" | docker secret create litellm_master_key - >/dev/null
  echo "Secret litellm_master_key angelegt (aus ../.env)."
fi

if secret_fehlt mock_api_key; then
  openssl rand -hex 24 | tr -d '\n' | docker secret create mock_api_key - >/dev/null
  echo "Secret mock_api_key angelegt (zufällig)."
fi

# 4. Config-Hashes
hash12() { sha256sum "$1" | cut -c1-12; }
LITELLM_CONFIG_HASH=$(hash12 litellm/config.yaml)
LITELLM_START_HASH=$(hash12 litellm/start.sh)
MOCK_SCRIPT_HASH=$(hash12 mock/mock_openai.py)
export LITELLM_CONFIG_HASH LITELLM_START_HASH MOCK_SCRIPT_HASH

# 5. Deploy und warten
docker stack deploy --prune -c stack.yml "$STACK"

echo "Warte, bis die Services gesund sind (max. 5 Min.) ..."
for _ in $(seq 1 60); do
  gesund=$(docker ps --filter "label=com.docker.stack.namespace=${STACK}" --filter health=healthy -q | wc -l)
  if [[ "$gesund" -ge 2 ]]; then
    docker service ls --filter "label=com.docker.stack.namespace=${STACK}"
    echo "Stack ${STACK} läuft. Nächster Schritt: ./smoke-test.sh"
    exit 0
  fi
  sleep 5
done

docker service ps "${STACK}_litellm" "${STACK}_mock" --no-trunc | head -20
fehler "Services nicht rechtzeitig gesund. Logs: docker service logs ${STACK}_litellm"
