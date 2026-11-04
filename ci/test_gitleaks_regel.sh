#!/usr/bin/env bash
# Selbsttest der gitleaks-Projektregel "projekt-zugangsdaten" (.gitleaks.toml).
#
# Wie test_check_pins.py für die Pin-Prüfung: Die Regel wird mit künstlichen
# Dateien geprüft, deren richtiges Ergebnis feststeht. Erst wenn der Selbsttest
# grün ist, kann man dem Scan über das Repo trauen.
#
# Aufruf:  bash ci/test_gitleaks_regel.sh
#   GITLEAKS=<pfad>  wählt das gitleaks-Programm (Standard: gitleaks aus PATH)
#
# Exit-Code 0 nur, wenn alle Fälle das erwartete Ergebnis liefern.
set -euo pipefail
cd "$(dirname "$0")/.."

GITLEAKS="${GITLEAKS:-gitleaks}"
FALLE=$(mktemp -d)
trap 'rm -rf "$FALLE"' EXIT

zufall() { python3 -c "import secrets; print(secrets.token_hex($1))"; }

# ---------------------------------------------------------------------------
# Positive Fälle: echte Werte – die Projektregel MUSS anschlagen.
# Die Werte werden bei jedem Lauf zufällig erzeugt und nie gespeichert.
# ---------------------------------------------------------------------------
mkdir -p "$FALLE/positiv"
printf 'RUNPOD_API_KEY=%s\n' "$(zufall 20)" >"$FALLE/positiv/env_datei.env"
printf 'export VLLM_API_KEY="%s"\n' "$(zufall 24)" >"$FALLE/positiv/shell_export.sh"
printf 'HF_TOKEN: hf_%s\n' "$(zufall 17)" >"$FALLE/positiv/yaml_doppelpunkt.yml"
printf 'LITELLM_MASTER_KEY=sk-%s\r\n' "$(zufall 24)" >"$FALLE/positiv/windows_zeilenende.env"

# ---------------------------------------------------------------------------
# Negative Fälle: kein echter Wert – es darf GAR KEINE Regel anschlagen.
# Jeder Fall steht für ein Muster, das im Repo legitim vorkommt.
# ---------------------------------------------------------------------------
mkdir -p "$FALLE/negativ"
# shellcheck disable=SC2016 # ${VLLM_API_KEY} soll hier wörtlich in der Datei stehen
printf 'LITELLM_MASTER_KEY=\nVLLM_API_KEY=${VLLM_API_KEY}\n' >"$FALLE/negativ/leer_und_verweis.env"
# shellcheck disable=SC2016 # $(…) soll hier wörtlich in der Datei stehen
printf '%s\n' 'sed -i "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)|" .env' \
  >"$FALLE/negativ/sed_befehl.sh"
printf 'HF_TOKEN=changeme\n' >"$FALLE/negativ/platzhalter.env"
printf 'RUNPOD_API_KEY=  # kommt später\n' >"$FALLE/negativ/kommentar.env"
# shellcheck disable=SC2016
printf '%s\n' 'curl --oauth2-bearer "${LITELLM_MASTER_KEY}" http://127.0.0.1:4000/v1/models' \
  >"$FALLE/negativ/curl_bearer.sh"

# ---------------------------------------------------------------------------
# gitleaks auf beide Ordner anwenden und die Funde je Datei auswerten
# ---------------------------------------------------------------------------
funde() {
  "$GITLEAKS" dir --config .gitleaks.toml --no-banner --exit-code 0 \
    --report-format json --report-path "$FALLE/bericht-$1.json" "$FALLE/$1" >/dev/null 2>&1
  python3 - "$FALLE/bericht-$1.json" <<'PY'
import json, os, sys
for fund in json.load(open(sys.argv[1])):
    print(f"{os.path.basename(fund['File'])} {fund['RuleID']}")
PY
}

positiv=$(funde positiv)
negativ=$(funde negativ)
fehler=0

# ---------------------------------------------------------------------------
# Bewertung: jede positive Datei muss von der Projektregel erkannt werden,
# keine negative Datei darf irgendeinen Fund haben
# ---------------------------------------------------------------------------
for datei in "$FALLE"/positiv/*; do
  name=$(basename "$datei")
  if grep -qx "$name projekt-zugangsdaten" <<<"$positiv"; then
    echo "  ok     erkannt:       $name"
  else
    echo "  FEHLER nicht erkannt: $name"
    fehler=$((fehler + 1))
  fi
done

for datei in "$FALLE"/negativ/*; do
  name=$(basename "$datei")
  treffer=$(grep "^$name " <<<"$negativ" || true)
  if [[ -z "$treffer" ]]; then
    echo "  ok     kein Fund:     $name"
  else
    echo "  FEHLER Fehlalarm:     $treffer"
    fehler=$((fehler + 1))
  fi
done

echo
if [[ "$fehler" -eq 0 ]]; then
  echo "Selbsttest der Projektregel bestanden."
else
  echo "${fehler} Fall/Fälle mit falschem Ergebnis."
  exit 1
fi
