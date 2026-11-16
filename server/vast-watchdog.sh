#!/usr/bin/env bash
# Auto-Stopp für Vast.ai (Regel 5): Die Instanz löscht sich nach N Minuten selbst.
#
# Warum im Container: Bei Vast.ai legt man die Instanz in der Weboberfläche an, es
# gibt also keinen Watchdog auf dem Laptop wie bei RunPod. Vast.ai gibt jeder
# Instanz CONTAINER_ID und CONTAINER_API_KEY mit – einen Key nur für diese Instanz,
# mit dem sie sich laut Vast-Doku von innen selbst stoppen oder löschen darf.
# Der Watchdog läuft dadurch weiter, auch wenn der Laptop zugeklappt ist.
#
# Quellen (abgerufen 17.11.2026):
#   https://docs.vast.ai/guides/instances/docker-environment   Variablen, Löschen von innen
#   https://docs.vast.ai/destroy-an-instance                   DELETE /api/v0/instances/{id}
#   https://docs.vast.ai/api-reference/hello-world             Key als "Authorization: Bearer"
#
# Aufruf (in der Instanz, im Repo-Ordner):
#   server/vast-watchdog.sh <minuten>    starten oder neu stellen (verlängern, verkürzen)
#   server/vast-watchdog.sh status       zeigen, wann gelöscht wird
#
# Ein "aus" gibt es bewusst nicht (Regel 5). Zum Verlängern neu stellen.
set -euo pipefail

PID_DATEI=/tmp/swarmllm-watchdog.pid
LOG=/tmp/swarmllm-watchdog.log
# Liegt im Ordner der Status-Seite, damit der Laptop den Zeitpunkt unter
# http://<ip>:<port für 8001>/watchdog.json sieht. Enthält keine Secrets.
INFO_DATEI=/tmp/status/watchdog.json
# Nur für die Unit-Tests überschreibbar: Adresse der API und Sekunden pro Minute.
VAST_API="${VAST_API:-https://console.vast.ai/api/v0}"
TAKT_S="${WATCHDOG_TAKT_S:-60}"

# ---------------------------------------------------------------------------
# Vast-Werte lesen: aus der Umgebung, sonst aus der Umgebung des Container-
# Hauptprozesses. In SSH-Sitzungen fehlen die Container-Variablen manchmal.
# ---------------------------------------------------------------------------
vast_wert() {
  local name="$1"
  if [[ -n "${!name:-}" ]]; then
    printf '%s' "${!name}"
  elif [[ -r /proc/1/environ ]]; then
    tr '\0' '\n' 2>/dev/null </proc/1/environ | grep -E "^${name}=" | head -1 | cut -d= -f2- || true
  fi
}

laeuft() { [[ -f "$PID_DATEI" ]] && kill -0 "$(cat "$PID_DATEI")" 2>/dev/null; }

# ---------------------------------------------------------------------------
# status: Zeitpunkt der Löschung anzeigen
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "status" ]]; then
  if laeuft; then
    cat "$INFO_DATEI"
    echo
  else
    echo "Kein Watchdog aktiv. Starten: server/vast-watchdog.sh <minuten>"
    exit 1
  fi
  exit 0
fi

# ---------------------------------------------------------------------------
# Eingaben prüfen: Minuten als Zahl, und wir sind wirklich auf einer Vast-Instanz
# ---------------------------------------------------------------------------
MINUTEN="${1:?Aufruf: server/vast-watchdog.sh <minuten> | status}"
[[ "$MINUTEN" =~ ^[0-9]+$ && "$MINUTEN" -ge 1 ]] || { echo "FEHLER: Minuten als ganze Zahl ≥ 1 angeben." >&2; exit 1; }
CONTAINER_ID="$(vast_wert CONTAINER_ID)"
CONTAINER_API_KEY="$(vast_wert CONTAINER_API_KEY)"
[[ -n "$CONTAINER_ID" && -n "$CONTAINER_API_KEY" ]] || {
  echo "FEHLER: CONTAINER_ID oder CONTAINER_API_KEY fehlt – läuft das auf einer Vast.ai-Instanz?" >&2
  echo "        Prüfen mit: env | grep CONTAINER_" >&2
  exit 1
}
export CONTAINER_ID CONTAINER_API_KEY VAST_API

# ---------------------------------------------------------------------------
# Neu stellen: einen schon laufenden Watchdog beenden, dann neuen starten
# ---------------------------------------------------------------------------
if laeuft; then
  kill "$(cat "$PID_DATEI")"
  echo "Bisherigen Watchdog beendet."
fi

ENDE=$(($(date +%s) + MINUTEN * TAKT_S))
mkdir -p "$(dirname "$INFO_DATEI")"
python3 - "$ENDE" "$MINUTEN" "$INFO_DATEI" <<'PY'
import json, sys, time
ende, minuten, datei = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
json.dump({"loescht_um_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(ende)),
           "ende_unix": ende, "minuten": minuten}, open(datei, "w"))
PY

# ---------------------------------------------------------------------------
# Der Watchdog selbst: ein Python-Prozess im Hintergrund (nohup, damit er das
# Ende der SSH-Sitzung übersteht). Der Key kommt über die Umgebung, nicht über
# die Kommandozeile – so taucht er nicht in "ps" auf.
# Nach Ablauf: DELETE an die Vast-API, bei Fehlern bis zu 10 Versuche im
# Minutenabstand. Erfolgreich heißt: Vast löscht die Instanz samt Daten.
# ---------------------------------------------------------------------------
nohup python3 - "$ENDE" >>"$LOG" 2>&1 <<'PY' &
import os, sys, time, urllib.error, urllib.request

ende = int(sys.argv[1])
cid, key, api = os.environ["CONTAINER_ID"], os.environ["CONTAINER_API_KEY"], os.environ["VAST_API"]
log = lambda text: print(time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), text, flush=True)

log(f"Watchdog aktiv, löscht Instanz {cid} um {time.strftime('%H:%M UTC', time.gmtime(ende))}")
time.sleep(max(0, ende - time.time()))

# Die Doku nennt den Pfad ohne Schrägstrich am Ende; manche Server verlangen ihn – beide versuchen.
urls = [f"{api}/instances/{cid}", f"{api}/instances/{cid}/"]
for versuch in range(1, 11):
    for url in urls:
        anfrage = urllib.request.Request(url, method="DELETE", headers={"Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(anfrage, timeout=30) as antwort:
                log(f"Löschung angefordert: HTTP {antwort.status} {antwort.read(200)!r}")
                sys.exit(0)
        except urllib.error.HTTPError as fehler:
            log(f"Versuch {versuch}: HTTP {fehler.code} bei {url}")
        except OSError as fehler:
            log(f"Versuch {versuch}: {fehler}")
    time.sleep(60)
log("FEHLER: Instanz konnte nicht gelöscht werden – in der Vast-Weboberfläche löschen!")
PY
echo $! >"$PID_DATEI"

echo "Watchdog aktiv: Instanz $CONTAINER_ID wird in $MINUTEN Min. gelöscht ($(date -u -d "@$ENDE" '+%H:%M UTC'))."
echo "Prüfen: server/vast-watchdog.sh status   Protokoll: $LOG"
