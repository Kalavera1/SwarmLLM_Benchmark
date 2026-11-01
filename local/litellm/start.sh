#!/bin/sh
# Startet LiteLLM im Container. Liest jede Docker-Secret-Datei und setzt sie als
# Umgebungsvariable mit großgeschriebenem Namen, z. B.
#   /run/secrets/litellm_master_key -> LITELLM_MASTER_KEY
# So stehen die Zugangsdaten nur im Arbeitsspeicher des Prozesses, nie in einer
# Datei im Repo oder in der Stack-Definition.
#
# SECRETS_DIR und LITELLM_CONFIG lassen sich für lokale Tests überschreiben.
set -eu

# ---------------------------------------------------------------------------
# Pfade: im Container die Swarm-Standardorte, für lokale Tests überschreibbar
# ---------------------------------------------------------------------------
SECRETS_DIR="${SECRETS_DIR:-/run/secrets}"
LITELLM_CONFIG="${LITELLM_CONFIG:-/etc/litellm/config.yaml}"

# ---------------------------------------------------------------------------
# Secrets laden: jede Datei wird eine Umgebungsvariable.
# Ausgegeben wird nur der Name, nie der Wert.
# ---------------------------------------------------------------------------
if [ -d "$SECRETS_DIR" ]; then
  for datei in "$SECRETS_DIR"/*; do
    [ -f "$datei" ] || continue
    name=$(basename "$datei" | tr '[:lower:]-' '[:upper:]_')
    wert=$(cat "$datei")
    export "$name=$wert"
    echo "Secret geladen: $name"
  done
fi

# ---------------------------------------------------------------------------
# Sicherheitsprüfung (Regel 8): ohne Master-Key gar nicht erst starten
# ---------------------------------------------------------------------------
if [ -z "${LITELLM_MASTER_KEY:-}" ]; then
  echo "FEHLER: Secret litellm_master_key fehlt – ohne Master-Key wäre das Gateway offen." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# LiteLLM starten. "exec" ersetzt dieses Skript durch LiteLLM, damit Swarm
# den Prozess direkt überwacht und Stopp-Signale ankommen.
# Im Image: der offizielle Startweg; lokal: das pip-installierte litellm.
# ---------------------------------------------------------------------------
if [ -x docker/prod_entrypoint.sh ]; then
  exec docker/prod_entrypoint.sh --config "$LITELLM_CONFIG" --port 4000 "$@"
fi
exec litellm --config "$LITELLM_CONFIG" --port 4000 "$@"
