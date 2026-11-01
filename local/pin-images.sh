#!/usr/bin/env bash
# Lädt das LiteLLM-Image per Tag, liest den Digest aus und trägt die
# gepinnte Referenz in images.env ein (Regel 4: Alles gepinnt).
#
# Aufruf (auf dem Mediaserver):  ./pin-images.sh [TAG]
# Standard-Tag: v1.106.6 (siehe images.env)
set -euo pipefail
cd "$(dirname "$0")"

TAG="${1:-v1.106.6}"
REPO="ghcr.io/berriai/litellm"

echo "Lade ${REPO}:${TAG} ..."
docker pull "${REPO}:${TAG}" >/dev/null
DIGEST=$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "${REPO}:${TAG}" \
  | grep -m1 "^${REPO}@sha256:" | cut -d@ -f2)

if [[ ! "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "FEHLER: Kein gültiger Digest für ${REPO}:${TAG} gefunden." >&2
  exit 1
fi

PIN="${REPO}:${TAG}@${DIGEST}"
sed -i "s|^LITELLM_IMAGE=.*|LITELLM_IMAGE=${PIN}|" images.env
echo "Gepinnt in images.env:"
grep '^LITELLM_IMAGE=' images.env
echo
echo "Bitte diese Zeile per Pull Request ins Repo übernehmen (oder an Claude schicken)."
