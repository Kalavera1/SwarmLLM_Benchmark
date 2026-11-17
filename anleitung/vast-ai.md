# GPU-Server: Vast.ai

Marktplatz für GPU-Rechner. Vorteil: **RTX PRO 6000 Max-Q** wie im Zielserver ist mietbar, und das CPU-Modell steht vor dem Mieten im Angebot. Nachteil: Die Qualität der Hosts schwankt – deshalb eng filtern und den Host-Check ernst nehmen.

**Vorher erledigt:** [ANLEITUNG](../ANLEITUNG.md) Teil 1 (einschließlich vLLM-Key in 1.3) und Teil 2 (Profil pinnen).
**Wofür geeignet:** Modelle komplett im VRAM (Qwen, GLM-5.3-Flash) auf genau den Karten des Zielservers. Für GLM-5.3 Q3 und DeepSeek V4.1 Flash nur, wenn ein Host mit EPYC 9004/9005, DDR5 und genug RAM angeboten wird.
**Kosten:** 2× RTX PRO 6000 Max-Q laut Angeboten vom 16.11.2026 ca. 2,80–5,50 $/h.

**Auto-Stopp (Regel 5):** `server/im-container-starten.sh` startet in der Instanz einen Watchdog, der sie nach 90 Min. (oder `--minuten N`) **selbst löscht** – über den Key, den Vast.ai jeder Instanz nur für sie selbst mitgibt. Er läuft auch, wenn der Laptop zugeklappt ist.

> Diese Schritte sind nach der Vast.ai-Doku geschrieben, aber noch nicht selbst durchgespielt – deshalb vor dem ersten echten Lauf den Watchdog einmal testen (Schritt 1).

## 1. Einmalig einrichten

1. **[Web]** Konto anlegen, Guthaben aufladen (Vast.ai arbeitet mit Vorkasse – das Guthaben ist zugleich das Ausgabenlimit).
2. **Watchdog einmal testen – Kosten wenige Cent:** **[Web]** die billigste Instanz mit irgendeiner GPU mieten (SSH-Modus), dann **[Server]** per SSH anmelden und:
   ```bash
   cd /tmp && python3 -c "import urllib.request,tarfile,io; tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen('https://codeload.github.com/Kalavera1/SwarmLLM_Benchmark/tar.gz/main').read())).extractall()"
   SwarmLLM_Benchmark-main/server/vast-watchdog.sh 2
   ```
   Nach 3 Minuten muss die Instanz in der Weboberfläche verschwunden sein. Wenn nicht: `cat /tmp/swarmllm-watchdog.log` lesen, Instanz von Hand löschen und den Fehler melden – dann bis zur Korrektur einen Wecker stellen.

## 2. Angebot wählen [Web]

Unter *Search* filtern:
- **2×** RTX PRO 6000 (für den Zielserver-Vergleich: **Max-Q**)
- **verified** und möglichst **Datacenter**
- **Reliability ≥ 99 %**
- **PCIe x16** pro Karte – ohne NVLink läuft der Austausch zwischen den Karten über PCIe. Der Zielserver hat PCIe 5.0; die Max-Q-Angebote vom 16.11.2026 hatten meist PCIe 4.0 (halbe Bandbreite). Das ist für Modelle im VRAM vertretbar, der Host-Check hält es fest
- Disk ≥ `DISK_GB` aus dem Profil, RAM ≥ `HOST_RAM_MIN_GB`
- für GLM-5.3 Q3 / DeepSeek V4.1 Flash zusätzlich: CPU AMD EPYC 9xxx

## 3. Instanz anlegen [Web] – ab hier kostet es

Beim Mieten unter *Edit Image & Config*:
- **Image:** das gepinnte `VLLM_IMAGE` aus dem Profil (mit `@sha256:…`)
- **Start:** SSH-Modus
- **Docker-Optionen:** `-p 8000:8000 -p 8001:8001`

## 4. vLLM starten [Server] – per SSH

```bash
mkdir -p /workspace && cd /workspace
python3 -c "import urllib.request,tarfile,io; tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen('https://codeload.github.com/Kalavera1/SwarmLLM_Benchmark/tar.gz/main').read())).extractall()"
cd SwarmLLM_Benchmark-main
umask 077                                    # benchmark.conf nur für dich lesbar
read -rsp "VLLM_API_KEY (wie auf dem Laptop): " K; echo; echo "VLLM_API_KEY=$K" > benchmark.conf
read -rsp "HF_TOKEN: " T; echo; echo "HF_TOKEN=$T" >> benchmark.conf; unset K T
server/im-container-starten.sh qwen38-27b
tail -f /tmp/swarmllm-start.log              # warten bis "bereit"
```

**Was passiert:**
- Das Repo wird ohne `git` heruntergeladen (das vLLM-Image hat oft keins).
- Die beiden `read`-Zeilen fragen Key und Token ab, ohne sie anzuzeigen, und schreiben sie in `benchmark.conf` – ohne Editor, denn auch den hat das Image oft nicht. Den Key auf dem Laptop zeigen: `grep VLLM_API_KEY benchmark.conf`.
- `im-container-starten.sh` liest Profil und `benchmark.conf` und prüft Pins und Key.
- Es startet den **Watchdog**: Die Instanz löscht sich nach 90 Min. selbst (andere Zeit: `--minuten N` anhängen, z. B. `server/im-container-starten.sh qwen38-27b --minuten 150`).
- Es startet das gemeinsame Startskript im Hintergrund – Host-Check, Download, vLLM-Start wie bei RunPod.
- Zum Schluss zeigt es die Zeile `BENCH_ZIEL_URL=…` für den Laptop.

Watchdog prüfen oder verlängern (rechnet ab jetzt neu):
```bash
server/vast-watchdog.sh status
server/vast-watchdog.sh 60                   # löscht in 60 Min.
```

## 5. Laptop auf die Instanz zeigen lassen [Laptop]

Die Zeile `BENCH_ZIEL_URL=…` aus Schritt 4 und den Preis in `benchmark.conf` eintragen:
```
BENCH_ZIEL_URL=http://<IP>:<äußerer Port für 8000>/v1
BENCH_KOSTEN_PRO_STUNDE=<Preis der Instanz in $>
```
Vast.ai bildet Port 8000 auf einen anderen **äußeren** Port ab; das Skript liest ihn aus der Instanz. Fehlt die Zeile, steht beides unter *Instances → IP & Port Info*.

Host-Daten: `http://<IP>:<äußerer Port für 8001>/host.json`, Löschzeitpunkt: `…/watchdog.json`. Fehlt P2P oder ist die RAM-Bandbreite schwach: Instanz löschen, anderes Angebot nehmen.

Dann messen wie in [ANLEITUNG Teil 3](../ANLEITUNG.md#teil-3--messen-laptop).

## 6. Aufräumen [Web]

Instanz **löschen** (*Destroy*), sobald die Messung fertig ist – nicht nur stoppen, gestoppte Instanzen kosten weiter Speicher. Der Watchdog ist nur das Sicherheitsnetz.

## Wenn etwas schiefgeht

| Problem | Lösung |
|---|---|
| Download sehr langsam | Host verwerfen; Angebote mit hoher Download-Rate wählen |
| Status `fehler: P2P …` | Host verwerfen, anderes Angebot |
| Instanz verschwindet mitten im Lauf | Watchdog abgelaufen (nächstes Mal `--minuten` höher) oder Host ausgefallen; neu anlegen. Gespeicherte Blöcke bleiben in `results/` |
| Testsuite meldet HTTP 401 | `VLLM_API_KEY` auf Laptop und Instanz unterschiedlich |
| `Keine Vast.ai-Instanz erkannt` oder `CONTAINER_ID oder CONTAINER_API_KEY fehlt` | Die Vast-Variablen sind nicht sichtbar; `env \| grep CONTAINER_` prüfen. **Ohne Watchdog nicht messen** – Instanz löschen |
| `Port 8000 ist nicht nach außen freigegeben` | Instanz löschen und mit Docker-Option `-p 8000:8000 -p 8001:8001` neu anlegen |
