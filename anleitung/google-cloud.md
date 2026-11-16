# GPU-Server: Google Cloud G4

Für Messungen, bei denen die **CPU zählt** – also für die Modelle, deren Experten teils im Arbeitsspeicher laufen (GLM-5.3 Q3, DeepSeek V4.1 Flash).

**Vorher erledigt:** [ANLEITUNG](../ANLEITUNG.md) Teil 1 (einschließlich vLLM-Key in 1.3) und Teil 2 (Profil pinnen).
**Maschine:** `g4-standard-96` – 2× RTX PRO 6000, 96 vCPU AMD Turin (EPYC 9005, dieselbe Generation wie der EPYC 9745 des Zielservers), 360 GB RAM.
**Kosten:** laut gcloud-compute.com (Stand 15.11.2026) in Europa ca. **4,10–4,60 $/h als Spot**, ca. 9,90 $/h regulär.

**Unterschiede zum Zielserver:** Google nutzt die RTX PRO 6000 Server Edition (600 W) statt Max-Q (300 W) – das Einlesen langer Prompts ist dort schneller als beim Zielserver. Die VM bekommt nur einen Teil der Speicherbandbreite des Hosts; der Host-Check misst sie. Für GLM-5.3 Q3 sind 360 GB RAM knapp.

> Diese Schritte sind nach der Google-Doku geschrieben, aber noch nicht selbst durchgespielt.

## 1. Einmalig einrichten [Web]

1. Projekt mit Abrechnung anlegen, Firmenkarte hinterlegen und unter *Abrechnung → Budgets und Benachrichtigungen* ein **Budget mit Warnung** setzen.
2. Unter *IAM → Kontingente* GPU-Kontingent für „NVIDIA RTX PRO 6000“ in einer Region beantragen (z. B. `europe-west4`). **Die Freigabe kann Tage dauern** – früh beantragen.

## 2. VM anlegen [Web] – ab hier kostet es

Konsole → *Compute Engine → VM erstellen*:
- Maschinentyp `g4-standard-96`, Bereitstellung **Spot**
- Image mit NVIDIA-Treiber, z. B. „Deep Learning VM“; Docker und NVIDIA Container Toolkit nachinstallieren, falls sie fehlen
- Bootlaufwerk 600 GB SSD
- **Maximale Laufzeit mit automatischem Löschen** setzen („Laufzeit der VM begrenzen“, auf der Kommandozeile `--max-run-duration=4h --instance-termination-action=DELETE`). Das ist hier der Auto-Stopp (Regel 5) – es gibt keinen Watchdog aus diesem Repo.
- Firewall: Port **8000** (vLLM) und **8001** (Status-Seite) nur für die IP deines Laptops freigeben

## 3. vLLM starten [Server] – per SSH aus der Konsole

```bash
git clone https://github.com/Kalavera1/SwarmLLM_Benchmark.git && cd SwarmLLM_Benchmark
cp benchmark.conf.example benchmark.conf
nano benchmark.conf                         # VLLM_API_KEY und HF_TOKEN – genau wie auf dem Laptop
server/lokal-starten.sh qwen38-27b
docker logs -f swarmllm-qwen38-27b          # warten bis "bereit"
```

**Was passiert:** `lokal-starten.sh` startet das gepinnte vLLM-Image per `docker run` mit dem gemeinsamen Startskript – Host-Check, Download, vLLM-Start wie bei RunPod. Die Gewichte landen im Docker-Volume `swarmllm-modelle` und bleiben beim Neustart des Containers erhalten.

Host-Daten ansehen: `curl -s localhost:8001/host.json` (CPU, RAM-Bandbreite, P2P, Power-Limit).

## 4. Laptop auf die VM zeigen lassen [Laptop]

In `benchmark.conf`:
```
BENCH_ZIEL_URL=http://<externe-IP-der-VM>:8000/v1
BENCH_KOSTEN_PRO_STUNDE=<Preis der VM in $>
```

Dann messen wie in [ANLEITUNG Teil 3](../ANLEITUNG.md#teil-3--messen-laptop).

## 5. Aufräumen [Web]

VM **löschen** – nicht nur anhalten, das Laufwerk kostet sonst weiter. Danach unter *Abrechnung* kontrollieren.

## Wenn etwas schiefgeht

| Problem | Lösung |
|---|---|
| VM lässt sich nicht anlegen: Kontingent | GPU-Kontingent aus Schritt 1 noch nicht freigegeben |
| Spot-VM wurde mitten im Lauf beendet | Bei Spot normal; neu anlegen. Bereits gespeicherte Blöcke bleiben in `results/` |
| Testsuite meldet HTTP 401 | `VLLM_API_KEY` auf Laptop und VM unterschiedlich |
| Keine Verbindung zu Port 8000 | Firewall-Regel und externe IP prüfen |
