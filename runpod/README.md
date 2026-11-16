# Phase 3: GPU-Server starten – RunPod oder eigener Server

Zwei Wege, gleiches Startskript (`server/start-im-container.sh`), damit Messungen vergleichbar sind:

| Weg | Wofür | Befehl |
|---|---|---|
| **RunPod** (automatisch) | Qwen, GLM – Modelle komplett im VRAM | `python3 runpod/rp.py …` |
| **Eigener Server / Vast.ai** (`docker run`) | DeepSeek V4.1 Flash, Messungen auf der Zielhardware | `server/lokal-starten.sh <profil>` |

Das Startskript im Container prüft zuerst den Host (GPUs mit Power-Limit, P2P mit Datenvergleich, CPU-Modell, RAM, `/dev/shm`, Disk), lädt dann genau die gepinnte Revision und startet vLLM. Den Fortschritt zeigt eine Status-Seite auf Port 8001 (`/status.json`, `/host.json`, `/topologie.txt` – keine Secrets).

## RunPod: einmalig einrichten

In `benchmark.conf` (Vorlage: `benchmark.conf.example`):

```bash
RUNPOD_API_KEY=…            # nur für dieses Projekt angelegt
RUNPOD_BUDGET_USD=100
RUNPOD_CLOUD=COMMUNITY      # geldschonend; SECURE nur bei Bedarf
POD_MAX_MINUTES=90          # Watchdog
```

Dann die GPU-ID aus dem Katalog holen und eintragen:

```bash
python3 runpod/rp.py gpus          # 'id' der RTX PRO 6000 als RUNPOD_GPU_ID in benchmark.conf
loginctl enable-linger "$USER"     # damit der Watchdog-Timer auch ohne Anmeldung läuft
```

## RunPod: ein Messlauf

```bash
python3 profiles/pin.py qwen38-27b                 # einmalig pro Profil
python3 runpod/rp.py up qwen38-27b --trocken       # zeigt Anfrage und Kosten, legt nichts an
python3 runpod/rp.py up qwen38-27b                 # fragt nach "ja", startet Watchdog
python3 runpod/rp.py warten                        # Download, Laden; misst die Kaltstartzeit
python3 runpod/rp.py check                         # P2P, CPU, RAM, Modellname, Key-Schutz
python3 -m bench run alle --profil qwen38-27b      # Testsuite, Stufe schnell
python3 runpod/rp.py down                          # terminieren, Kosten verbuchen
```

- Schlägt `check` fehl (kein P2P, falsche CPU, zu wenig RAM), **sofort** `down` – ein neuer Pod landet meist auf einem anderen Host.
- `python3 runpod/rp.py status` zeigt alle eigenen Pods, `down-alle` ist die Notbremse.
- Jeder Pod landet in `results/kosten.csv`; `python3 runpod/rp.py budget` zeigt den Rest.
- Pro Pod wird ein neuer API-Key erzeugt. Er steht nur in `runpod/.aktueller-pod.json` (Rechte 600, nicht im Repo); die Testsuite liest ihn dort.
- vLLM ist über einen **direkten TCP-Port** erreichbar, nicht über den RunPod-HTTP-Proxy (der trennt nach ca. 2 Min.). Der Datenverkehr ist dabei unverschlüsselt; geschützt ist der Endpunkt durch den Key des Laufs.

## Eigener Server oder Vast.ai

Auf einem Server mit Docker und NVIDIA Container Toolkit, im Repo-Ordner:

```bash
python3 profiles/pin.py qwen38-27b
server/lokal-starten.sh qwen38-27b                 # VLLM_API_KEY muss in benchmark.conf stehen
docker logs -f swarmllm-qwen38-27b                 # oder http://<server>:8001/status.json
```

Gemessen wird vom Steuerrechner aus mit `BENCH_ZIEL_URL=http://<server>:8000/v1` und demselben `VLLM_API_KEY` in dessen `benchmark.conf`.

Bei **Vast.ai** läuft kein `docker run` auf dem Host; dort das gepinnte vLLM-Image als Image wählen, die Profilwerte als Umgebungsvariablen setzen und als Startbefehl dasselbe Startskript verwenden. Vorteil von Vast.ai: Das CPU-Modell des Hosts ist vor dem Mieten sichtbar.

## Zielhardware beachten

Der eigene Server hat RTX PRO 6000 mit **300 W** Power-Limit (Max-Q). Cloud-Karten (Server/Workstation Edition) laufen mit 600 W und sind beim Prefill schneller. Der Host-Check speichert das Power-Limit in jedem Pod-Check, damit Cloud- und eigene Messungen nicht verwechselt werden.
