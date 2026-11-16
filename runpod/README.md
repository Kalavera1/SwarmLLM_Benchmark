# runpod/ – technische Referenz zu `rp.py`

**Schritt-für-Schritt-Anleitung:** [anleitung/runpod.md](../anleitung/runpod.md). Hier steht nur, was `rp.py` im Einzelnen tut.

## Befehle

| Befehl | Was er tut |
|---|---|
| `python3 runpod/rp.py gpus` | GPU-Typen aus dem RunPod-Katalog; die `id` gehört als `RUNPOD_GPU_ID` in `benchmark.conf` |
| `python3 runpod/rp.py up <profil> [--stufe schnell\|voll] [--minuten N] [--cloud COMMUNITY\|SECURE] [--trocken] [--ja]` | Pod anlegen: prüft Profil und Pins, zeigt Kostenschätzung, fragt nach „ja“, erzeugt den vLLM-Key, startet den Watchdog |
| `python3 runpod/rp.py warten` | zeigt die Startphasen aus der Status-Seite, bis vLLM antwortet; misst die Kaltstartzeit |
| `python3 runpod/rp.py check` | P2P, CPU-Muster, RAM, geladenes Modell, Abweisung ohne Key; Ergebnis in `results/<profil>/pod-check/` |
| `python3 runpod/rp.py status` | alle eigenen Pods mit Stundenpreis |
| `python3 runpod/rp.py down [--pod ID]` | Pod **terminieren** (nicht nur stoppen), Kosten verbuchen, Watchdog beenden |
| `python3 runpod/rp.py down-alle` | Notbremse: alle eigenen Pods terminieren |
| `python3 runpod/rp.py kosten` | Summe aller verbuchten Pods aus `results/kosten.csv` |

## Werte aus `benchmark.conf`

| Wert | Bedeutung |
|---|---|
| `RUNPOD_API_KEY` | Zugang zur RunPod-API (nur für dieses Projekt angelegt) |
| `RUNPOD_GPU_ID` | GPU-Typ aus `rp.py gpus` |
| `RUNPOD_CLOUD` | `COMMUNITY` (günstiger, Standard) oder `SECURE` |
| `POD_MAX_MINUTES` | Watchdog-Zeit; leer = 90 Min. (`schnell`) bzw. 210 Min. (`voll`) |
| `HF_TOKEN` | wird an den Pod weitergegeben |

Die Ausgabengrenze steht als Limit im RunPod-Konto, nicht im Skript.

## Sicherheitsnetz

- **Watchdog (Regel 5):** `systemd-run --user` startet einen Timer, der nach Ablauf `rp.py down --grund watchdog` aufruft. Ohne systemd ein Hintergrundprozess – der überlebt keinen Neustart oder Ruhezustand des Steuerrechners. Damit der Timer auch ohne Anmeldung läuft: `loginctl enable-linger "$USER"`.
- **Key (Regel 8):** Pro Pod ein neuer `VLLM_API_KEY`, nur in `runpod/.aktueller-pod.json` (Rechte 600, in `.gitignore`). Die Testsuite liest Adresse und Key dort.
- **Kostenbuch:** Jeder Pod landet mit Preis und Laufzeit in `results/kosten.csv`.
- **Ports:** vLLM (8000) und Status-Seite (8001) über **direkte TCP-Ports**, nicht über den RunPod-HTTP-Proxy – der trennt stille Verbindungen nach ca. 2 Min. Der Verkehr ist unverschlüsselt; geschützt ist der Endpunkt durch den Key des Laufs.

## Was im Pod läuft

`rp.py` gibt das Startskript `server/start-im-container.sh` als Umgebungsvariable mit. Es prüft den Host (GPUs mit Power-Limit, P2P mit Datenvergleich, CPU, RAM-Bandbreite, `/dev/shm`, Disk), lädt die gepinnte Revision und startet vLLM. Status-Seite: `/status.json`, `/host.json`, `/topologie.txt` – keine Secrets.

API: RunPod REST v2 (`https://api.runpod.io/v2`), siehe [Entscheidungslog](../docs/entscheidungen.md).
