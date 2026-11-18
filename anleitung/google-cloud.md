# GPU-Server: Google Cloud G4 (Hauptweg)

**Der Hauptweg für alle Messungen** (Entscheidung vom 18.11.2026): dieselbe Kartengeneration und dieselbe CPU-Generation wie der Zielserver, und die Firma kann direkt bei Google abrechnen.

**Vorher erledigt:** [ANLEITUNG](../ANLEITUNG.md) Teil 1 (einschließlich vLLM-Key in 1.3) und Teil 2 (Profil pinnen).
**Maschine:** `g4-standard-96` – 2× RTX PRO 6000 (je 96 GB), 96 vCPU AMD EPYC Turin (5. Generation, wie der EPYC 9745 des Zielservers), 360 GB RAM.
**Bezugsmodell:** **Flex-Start** – wartet bis zu 2 Stunden auf freie Karten, läuft dann ohne Unterbrechung und wird nach der festgelegten Zeit gelöscht. Spot ist etwas billiger, kann aber jederzeit abgebrochen werden.
**Kosten je Stunde:** Flex-Start 4,50 $ laut Google-Preisliste (Region nicht angegeben, für Europa mit 4,95 $ gerechnet); Spot in `europe-west4` 4,10 $, regulär 9,90 $ (gcloud-compute.com, Stand 15.11.2026). Quellen im [Entscheidungslog](../docs/entscheidungen.md).

**Unterschiede zum Zielserver:** Google nutzt die RTX PRO 6000 Server Edition (600 W) statt Max-Q (300 W) – das Einlesen langer Prompts ist dort schneller als beim Zielserver. Die VM bekommt nur einen Teil der Speicherbandbreite des Hosts; der Host-Check misst sie. Für GLM-5.3 Q3 sind 360 GB RAM knapp.

> Diese Schritte sind nach der Google-Doku geschrieben, aber noch nicht selbst durchgespielt.

## 1. Einmalig einrichten [Web]

Was der Einkauf dafür bestellt, steht im Dokument „Google Cloud G4: Bestellung und erste Schritte“ (claude.ai). Kurz: ein Rechnungskonto der Firma, kein kostenloses Testkonto (dort gibt es keine GPUs).

1. **Projekt** `swarmllm-benchmark` an das Rechnungskonto hängen und die *Compute Engine API* aktivieren.
2. **Budget** über 500 € mit Warnungen bei 50, 90 und 100 % (*Abrechnung → Budgets und Benachrichtigungen*). Ein Budget **warnt nur**, es stoppt nichts – die harte Grenze ist das Kartenlimit.
3. **GPU-Kontingent** beantragen (*IAM und Verwaltung → Kontingente*), Region `europe-west4`: „Preemptible NVIDIA RTX PRO 6000 GPUs“ (`PREEMPTIBLE_NVIDIA_RTX_PRO_6000_GPUS`) auf **2**. Daraus zählen Flex-Start und Spot. **Kann Tage dauern** – früh beantragen. Scheitert das Anlegen später an `GPUS_ALL_REGIONS`, auch „GPUs (all regions)“ auf 2.
4. **Firewall** in der *Cloud Shell* (Symbol `>_` oben rechts in der Konsole – dort ist `gcloud` schon angemeldet). Die IP deines Laptops zeigt `curl -s https://ifconfig.me` **auf dem Laptop**:
   ```bash
   gcloud config set project swarmllm-benchmark
   gcloud compute firewall-rules create swarmllm-bench \
     --allow=tcp:8000,tcp:8001 --source-ranges=<IP-des-Laptops>/32 --target-tags=swarmllm
   ```
   Nur dein Laptop erreicht vLLM (8000) und die Status-Seite (8001). Ändert sich die IP: `gcloud compute firewall-rules update swarmllm-bench --source-ranges=<neue-IP>/32`.

**Region:** `europe-west4` (Niederlande) ist im Spot-Preis die günstigste EU-Region mit G4 und hat drei Zonen dafür (`-a`, `-b`, `-c`). Ausweichen: `europe-north1` (Finnland), `europe-west10` (Berlin, nur Zone `-b`). Das Kontingent gilt je Region.

## 2. VM anlegen [Web] – ab hier kostet es

In der Cloud Shell:

```bash
ZONE=europe-west4-a
gcloud compute instances create swarmllm-g4 \
  --zone=$ZONE \
  --machine-type=g4-standard-96 \
  --provisioning-model=FLEX_START \
  --request-valid-for-duration=2h \
  --max-run-duration=4h \
  --instance-termination-action=DELETE \
  --maintenance-policy=TERMINATE \
  --image-family=common-cu129-ubuntu-2404-nvidia-580 \
  --image-project=deeplearning-platform-release \
  --metadata=install-nvidia-driver=True \
  --boot-disk-type=hyperdisk-balanced \
  --boot-disk-size=600GB \
  --tags=swarmllm
```

**Was die Zeilen bedeuten:**
- `FLEX_START` + `--request-valid-for-duration=2h`: höchstens 2 Stunden auf freie Karten warten. Status: `gcloud compute instances list`.
- `--max-run-duration=4h` + `DELETE`: **Auto-Stopp (Regel 5)** – die VM samt Laufwerk wird nach 4 Stunden gelöscht. Für DeepSeek V4.1 Flash und GLM-5.3 Q3 (großer Download, langsame Läufe) auf `10h` setzen; Flex-Start erlaubt bis 7 Tage.
- Image „Deep Learning VM“ mit NVIDIA-Treiber 580; `install-nvidia-driver=True` richtet ihn beim ersten Start ein (3–5 Minuten, ein Neustart).
- `hyperdisk-balanced`: G4 kann kein normales Persistent Disk. 600 GB reichen für das größte Modell (GLM-5.3 Q3, 343 GB) samt Image.
- `--tags=swarmllm`: Damit greift die Firewall-Regel aus Schritt 1.4.

**Spot statt Flex-Start** (etwas billiger, kann jederzeit abbrechen): die beiden Flex-Zeilen ersetzen durch `--provisioning-model=SPOT --no-restart-on-failure`.

## 3. vLLM starten [Server] – per SSH

Aus der Cloud Shell: `gcloud compute ssh swarmllm-g4 --zone=$ZONE`. Dann auf der VM:

```bash
nvidia-smi -L                                # 2× RTX PRO 6000? Sonst 5 Minuten warten (Treiber)
docker run --rm --gpus all ubuntu nvidia-smi -L   # sieht Docker die Karten?
git clone https://github.com/Kalavera1/SwarmLLM_Benchmark.git && cd SwarmLLM_Benchmark
cp benchmark.conf.example benchmark.conf
nano benchmark.conf                          # VLLM_API_KEY und HF_TOKEN – genau wie auf dem Laptop
server/lokal-starten.sh qwen38-27b
docker logs -f swarmllm-qwen38-27b           # warten bis "bereit"
```

**Was passiert:** `lokal-starten.sh` startet das gepinnte vLLM-Image per `docker run` mit dem gemeinsamen Startskript – Host-Check, Download, vLLM-Start wie bei RunPod. Die Gewichte landen im Docker-Volume `swarmllm-modelle` auf dem VM-Laufwerk und verschwinden mit der VM.

Fehlt Docker oder sieht Docker die Karten nicht: Docker und das [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) nach NVIDIA-Anleitung installieren.

Host-Daten: `curl -s localhost:8001/host.json` (CPU, RAM-Bandbreite, P2P, Power-Limit).

## 4. Laptop auf die VM zeigen lassen [Laptop]

Externe IP der VM (in der Cloud Shell):
```bash
gcloud compute instances describe swarmllm-g4 --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

In `benchmark.conf` auf dem Laptop:
```
BENCH_ZIEL_URL=http://<externe-IP-der-VM>:8000/v1
BENCH_KOSTEN_PRO_STUNDE=4.95
```

Dann messen wie in [ANLEITUNG Teil 3](../ANLEITUNG.md#teil-3--messen-laptop).

## 5. Aufräumen [Web]

Sobald die Messung fertig ist, in der Cloud Shell:
```bash
gcloud compute instances delete swarmllm-g4 --zone=$ZONE --quiet
```
Die 4-Stunden-Grenze ist nur das Sicherheitsnetz. Danach unter *Abrechnung* kontrollieren. Die Firewall-Regel kostet nichts und bleibt für den nächsten Lauf.

## Wenn etwas schiefgeht

| Problem | Lösung |
|---|---|
| `Quota 'PREEMPTIBLE_NVIDIA_RTX_PRO_6000_GPUS' exceeded` | Kontingent aus Schritt 1.3 noch nicht freigegeben, oder für eine andere Region beantragt |
| Flex-Start findet nach 2 Stunden keine Karten | Andere Zone (`-b`, `-c`) oder Region versuchen |
| `nvidia-smi` findet keine Karten | Treiberinstallation läuft noch (3–5 Minuten, ein Neustart); dann erneut per SSH anmelden |
| Spot-VM wurde mitten im Lauf beendet | Bei Spot normal; neu anlegen. Gespeicherte Blöcke bleiben in `results/` |
| Testsuite meldet HTTP 401 | `VLLM_API_KEY` auf Laptop und VM unterschiedlich |
| Keine Verbindung zu Port 8000 | Firewall-Regel (IP des Laptops?), `--tags=swarmllm` und externe IP prüfen |
