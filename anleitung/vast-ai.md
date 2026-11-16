# GPU-Server: Vast.ai

Marktplatz für GPU-Rechner. Vorteil: **RTX PRO 6000 Max-Q** wie im Zielserver ist mietbar, und das CPU-Modell steht vor dem Mieten im Angebot. Nachteil: Die Qualität der Hosts schwankt – deshalb eng filtern und den Host-Check ernst nehmen.

**Vorher erledigt:** [ANLEITUNG](../ANLEITUNG.md) Teil 1 (einschließlich vLLM-Key in 1.3) und Teil 2 (Profil pinnen).
**Wofür geeignet:** Modelle komplett im VRAM (Qwen, GLM-5.3-Flash) auf genau den Karten des Zielservers. Für GLM-5.3 Q3 und DeepSeek V4.1 Flash nur, wenn ein Host mit EPYC 9004/9005, DDR5 und genug RAM angeboten wird.
**Kosten:** 2× RTX PRO 6000 Max-Q laut Angeboten vom 16.11.2026 ca. 2,80–5,50 $/h.

> **Kein Auto-Stopp aus diesem Repo.** Die Instanz läuft, bis du sie löschst. Wecker stellen.
>
> Diese Schritte sind nach der Vast.ai-Oberfläche geschrieben, aber noch nicht selbst durchgespielt.

## 1. Einmalig einrichten [Web]

Konto anlegen, Guthaben aufladen (Vast.ai arbeitet mit Vorkasse – das Guthaben ist zugleich das Ausgabenlimit).

## 2. Angebot wählen [Web]

Unter *Search* filtern:
- **2×** RTX PRO 6000 (für den Zielserver-Vergleich: **Max-Q**)
- **verified** und möglichst **Datacenter**
- **Reliability ≥ 99 %**
- **PCIe 5.0 x16** – ohne NVLink läuft der Austausch zwischen den Karten über PCIe
- Disk ≥ `DISK_GB` aus dem Profil, RAM ≥ `HOST_RAM_MIN_GB`
- für GLM-5.3 Q3 / DeepSeek V4.1 Flash zusätzlich: CPU AMD EPYC 9xxx

## 3. Instanz anlegen [Web] – ab hier kostet es

Beim Mieten unter *Edit Image & Config*:
- **Image:** das gepinnte `VLLM_IMAGE` aus dem Profil (mit `@sha256:…`)
- **Start:** SSH-Modus
- **Docker-Optionen:** `-p 8000:8000 -p 8001:8001`

## 4. vLLM starten [Server] – per SSH

```bash
cd /workspace
python3 -c "import urllib.request,tarfile,io; tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen('https://codeload.github.com/Kalavera1/SwarmLLM_Benchmark/tar.gz/main').read())).extractall()"
cd SwarmLLM_Benchmark-main
cp benchmark.conf.example benchmark.conf
nano benchmark.conf                          # VLLM_API_KEY und HF_TOKEN – genau wie auf dem Laptop
server/im-container-starten.sh qwen38-27b
tail -f /tmp/swarmllm-start.log              # warten bis "bereit"
```

**Was passiert:** Das Repo wird ohne `git` heruntergeladen (das vLLM-Image hat oft keins). `im-container-starten.sh` liest Profil und `benchmark.conf`, prüft Pins und Key und startet das gemeinsame Startskript im Hintergrund – Host-Check, Download, vLLM-Start wie bei RunPod.

## 5. Laptop auf die Instanz zeigen lassen [Laptop]

Unter *Instances → IP & Port Info* steht, auf welchen **äußeren** Port 8000 abgebildet ist. In `benchmark.conf`:
```
BENCH_ZIEL_URL=http://<IP>:<äußerer Port für 8000>/v1
BENCH_KOSTEN_PRO_STUNDE=<Preis der Instanz in $>
```

Host-Daten: `http://<IP>:<äußerer Port für 8001>/host.json`. Fehlt P2P oder ist die RAM-Bandbreite schwach: Instanz löschen, anderes Angebot nehmen.

Dann messen wie in [ANLEITUNG Teil 3](../ANLEITUNG.md#teil-3--messen-laptop).

## 6. Aufräumen [Web]

Instanz **löschen** (*Destroy*), nicht nur stoppen – gestoppte Instanzen kosten weiter Speicher.

## Wenn etwas schiefgeht

| Problem | Lösung |
|---|---|
| Download sehr langsam | Host verwerfen; Angebote mit hoher Download-Rate wählen |
| Status `fehler: P2P …` | Host verwerfen, anderes Angebot |
| Instanz verschwindet mitten im Lauf | Bei Marktplatz-Hosts möglich; neu anlegen. Gespeicherte Blöcke bleiben in `results/` |
| Testsuite meldet HTTP 401 | `VLLM_API_KEY` auf Laptop und Instanz unterschiedlich |
