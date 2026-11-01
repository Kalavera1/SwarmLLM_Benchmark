#!/usr/bin/env bash
# Integrationstest Phase 1: prüft die Kette  Client -> LiteLLM -> Mock.
#
# Aufruf:  ./smoke-test.sh [BASIS-URL]
#   Standard-URL: http://127.0.0.1:4000
#   Master-Key aus LITELLM_MASTER_KEY (Umgebung) oder ../.env
#
# Exit-Code 0 nur, wenn alle Prüfungen bestehen.
set -euo pipefail
cd "$(dirname "$0")"

BASIS="${1:-http://127.0.0.1:4000}"
if [[ -z "${LITELLM_MASTER_KEY:-}" && -f ../.env ]]; then
  LITELLM_MASTER_KEY=$(grep -E '^LITELLM_MASTER_KEY=' ../.env | cut -d= -f2- || true)
fi
[[ -n "${LITELLM_MASTER_KEY:-}" ]] || {
  echo "FEHLER: LITELLM_MASTER_KEY nicht gesetzt (Umgebung oder ../.env)." >&2
  exit 1
}

UA="SwarmLLM_Benchmark-smoke/1.0" # eigener User-Agent (Erfahrung aus dem B300-Test)
fehlschlaege=0

pruefe() {
  local name="$1" erwartet="$2" ist="$3"
  if [[ "$ist" == "$erwartet" ]]; then
    printf '  ok    %s\n' "$name"
  else
    printf '  FEHLER %s (erwartet: %s, bekommen: %s)\n' "$name" "$erwartet" "$ist"
    fehlschlaege=$((fehlschlaege + 1))
  fi
}

http_status() { curl -s -o /dev/null -w '%{http_code}' -A "$UA" "$@"; }
# LiteLLM ohne Datenbank weist ab, aber nicht immer mit 401: ohne Key kommt 500,
# mit falschem Key 400 ("No connected db"). Entscheidend ist: keine 2xx-Antwort.
abgewiesen() {
  local code
  code=$(http_status "$@")
  [[ "$code" -ge 400 ]] && echo ja || echo "nein (HTTP ${code})"
}
# --oauth2-bearer setzt den Header "Authorization: Bearer …", ohne dass der Key
# als Header-Literal im Skript steht (sonst schlägt der Secret-Scan an).
mit_key() { curl -sS -A "$UA" --oauth2-bearer "${LITELLM_MASTER_KEY}" -H 'Content-Type: application/json' "$@"; }

echo "Smoke-Test gegen ${BASIS}"

pruefe "Gesundheit (/health/liveliness)" 200 "$(http_status "${BASIS}/health/liveliness")"
pruefe "Ohne Key abgewiesen (Regel 8)" ja "$(abgewiesen "${BASIS}/v1/models")"
pruefe "Falscher Key abgewiesen" ja "$(abgewiesen --oauth2-bearer sk-falsch "${BASIS}/v1/models")"
pruefe "Chat ohne Key abgewiesen" ja "$(abgewiesen -H 'Content-Type: application/json' \
  -d '{"model":"mock","messages":[{"role":"user","content":"x"}]}' "${BASIS}/v1/chat/completions")"

modelle=$(mit_key "${BASIS}/v1/models")
pruefe "Modell 'mock' gelistet" ja "$(grep -q '"mock"' <<<"$modelle" && echo ja || echo nein)"

antwort=$(mit_key "${BASIS}/v1/chat/completions" \
  -d '{"model":"mock","messages":[{"role":"user","content":"Hallo"}],"max_tokens":16}')
pruefe "Chat ohne Streaming liefert Text" ja \
  "$(python3 -c 'import json,sys; d=json.load(sys.stdin); print("ja" if d["choices"][0]["message"]["content"] else "nein")' <<<"$antwort" 2>/dev/null || echo nein)"

stream=$(mit_key -N "${BASIS}/v1/chat/completions" \
  -d '{"model":"mock","stream":true,"messages":[{"role":"user","content":"Hallo"}],"max_tokens":8}')
pruefe "Chat mit Streaming endet mit [DONE]" ja "$(grep -q 'data: \[DONE\]' <<<"$stream" && echo ja || echo nein)"

tool=$(mit_key "${BASIS}/v1/chat/completions" -d '{"model":"mock","messages":[{"role":"user","content":"Bitte tool nutzen"}],
  "tools":[{"type":"function","function":{"name":"wetter","parameters":{"type":"object","properties":{}}}}]}')
pruefe "Tool-Call wird durchgereicht" wetter \
  "$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["choices"][0]["message"]["tool_calls"][0]["function"]["name"])' <<<"$tool" 2>/dev/null || echo fehlt)"

echo
if [[ "$fehlschlaege" -eq 0 ]]; then
  echo "Alle Prüfungen bestanden."
else
  echo "${fehlschlaege} Prüfung(en) fehlgeschlagen."
  exit 1
fi
