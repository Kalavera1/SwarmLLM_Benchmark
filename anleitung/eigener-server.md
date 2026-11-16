# GPU-Server: eigener Server

Die endgültige Messung auf der Zielhardware: 1× AMD EPYC 9745 und 2× RTX PRO 6000 Blackwell Max-Q (je 96 GB, 300 W). Kostet nichts außer Strom.

**Vorher erledigt:** [ANLEITUNG](../ANLEITUNG.md) Teil 1 (einschließlich vLLM-Key in 1.3) und Teil 2 (Profil pinnen).
**Voraussetzung auf dem Server:** Linux mit NVIDIA-Treiber, Docker und NVIDIA Container Toolkit; Internet für den Download der Gewichte. Für GLM-5.3 Q3 und DeepSeek V4.1 Flash: **≥ 384 GB RAM, alle 12 Speicherkanäle bestückt**.

## 1. Einmalig prüfen [Server]

```bash
nvidia-smi --query-gpu=name,power.limit,memory.total --format=csv   # 2 Karten?
docker run --rm --gpus all ubuntu nvidia-smi -L                      # Docker sieht die GPUs?
free -g                                                              # Arbeitsspeicher
```

## 2. vLLM starten [Server]

```bash
git clone https://github.com/Kalavera1/SwarmLLM_Benchmark.git && cd SwarmLLM_Benchmark
cp benchmark.conf.example benchmark.conf
nano benchmark.conf                         # VLLM_API_KEY und HF_TOKEN – genau wie auf dem Laptop
server/lokal-starten.sh qwen38-27b
docker logs -f swarmllm-qwen38-27b          # warten bis "bereit"
```

**Was passiert:** `lokal-starten.sh` startet das gepinnte vLLM-Image per `docker run` mit dem gemeinsamen Startskript – Host-Check, Download, vLLM-Start wie bei den gemieteten Servern. Die Gewichte landen im Docker-Volume `swarmllm-modelle` und werden beim nächsten Start nicht erneut geladen.

Host-Daten: `curl -s localhost:8001/host.json` (CPU, RAM-Bandbreite, P2P, Power-Limit).

## 3. Laptop auf den Server zeigen lassen [Laptop]

In `benchmark.conf`:
```
BENCH_ZIEL_URL=http://<IP-des-Servers>:8000/v1
BENCH_KOSTEN_PRO_STUNDE=
```

Dann messen wie in [ANLEITUNG Teil 3](../ANLEITUNG.md#teil-3--messen-laptop). Die Testsuite kann auch direkt auf dem Server laufen – dann ist `BENCH_ZIEL_URL=http://127.0.0.1:8000/v1`.

## 4. Stoppen [Server]

```bash
server/lokal-starten.sh qwen38-27b stopp
```

Die Gewichte bleiben im Volume `swarmllm-modelle`. Platz freigeben: `docker volume rm swarmllm-modelle`.

## Wenn etwas schiefgeht

| Problem | Lösung |
|---|---|
| `could not select device driver "" with capabilities: [[gpu]]` | NVIDIA Container Toolkit fehlt oder Docker nicht neu gestartet |
| Status `fehler: P2P …` | IOMMU/ACS im BIOS prüfen; zum Test `P2P_PFLICHT=0` im Profil (kostet Leistung) |
| Testsuite meldet HTTP 401 | `VLLM_API_KEY` auf Laptop und Server unterschiedlich |
| Keine Verbindung zu Port 8000 | Firewall des Servers prüfen |
