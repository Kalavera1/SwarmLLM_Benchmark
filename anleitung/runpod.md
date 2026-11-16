# GPU-Server: RunPod

Automatischer Weg: `runpod/rp.py` legt den Pod über die RunPod-API an, wartet, prüft und löscht ihn wieder. In der RunPod-Weboberfläche legst du **keinen Pod von Hand** an.

**Vorher erledigt:** [ANLEITUNG](../ANLEITUNG.md) Teil 1 (einrichten) und Teil 2 (Profil pinnen).
**Wofür geeignet:** Modelle, die komplett in 2× 96 GB VRAM passen (Qwen, GLM-5.3-Flash). Das CPU-Modell des Hosts lässt sich bei RunPod nicht wählen.
**Kosten:** 2× RTX PRO 6000 ca. 3,30 $/h (Community) bzw. 5,40 $/h (Secure), Stand 15.11.2026.

## 1. Einmalig einrichten

1. **[Web]** RunPod-Konto anlegen, Firmenkarte hinterlegen und **ein Ausgabenlimit setzen**. Das Limit ist die einzige Kostenbremse über alle Läufe; die Skripte zeigen Kosten nur an.
2. **[Web]** Unter **Settings → API Keys** einen Key nur für dieses Projekt anlegen und als `RUNPOD_API_KEY` in `benchmark.conf` eintragen.
3. **[Laptop]** GPU-Typ ermitteln:
   ```bash
   python3 runpod/rp.py gpus
   ```
   **Was passiert:** Das Skript fragt bei der RunPod-API die GPU-Typen ab und zeigt die RTX PRO 6000. Die angezeigte `id` als `RUNPOD_GPU_ID` in `benchmark.conf` eintragen.

Einen vLLM-Key brauchst du für RunPod **nicht** – `rp.py` erzeugt pro Pod einen eigenen.

## 2. Probelauf [Laptop] – kostenlos

```bash
python3 runpod/rp.py up qwen38-27b --trocken
```

**Was passiert:** Zeigt die komplette Anfrage an RunPod – Image, GPUs, Disk, Ports, alle Umgebungsvariablen – und die geschätzten Kosten. Legt nichts an. Fehlt etwas (Profil nicht gepinnt, `RUNPOD_GPU_ID` leer), steht es hier.

## 3. Pod anlegen [Laptop] – ab hier kostet es

```bash
python3 runpod/rp.py up qwen38-27b         # mit "ja" bestätigen
```

**Was passiert – auf dem Laptop:**
- erzeugt einen **neuen vLLM-Key nur für diesen Pod**
- schickt die Anfrage an RunPod. Die Umgebungsvariablen setzt das Skript selbst – in der Weboberfläche ist nichts einzutragen:

  | Variable im Pod | kommt aus |
  |---|---|
  | `VLLM_API_KEY` | neu erzeugt |
  | `HF_TOKEN` | `benchmark.conf` |
  | `MODEL_ID`, `MODEL_REVISION`, `SERVED_NAME` | Profil |
  | `SERVE_ARGS`, `SPEC_CONFIG`, `SERVE_ENV` | Profil (vLLM-Parameter, MTP, Sondervariablen) |
  | `START_SKRIPT_B64` | `server/start-im-container.sh` |

- speichert Pod-ID, Key und Stundenpreis in `runpod/.aktueller-pod.json` (nicht im Repo)
- startet den **Watchdog**: Er löscht den Pod nach 90 Min. (Stufe `voll`: 210 Min.)

**Was passiert – bei RunPod:** freien Host suchen, vLLM-Image laden, Container starten.

> **Laptop jetzt nicht zuklappen.** Der Watchdog läuft auf dem Laptop. Ist er aus, bleibt der Pod stehen – dann im RunPod-Dashboard von Hand löschen.

## 4. Warten, bis vLLM bereit ist [Laptop] – 10–30 Min.

```bash
python3 runpod/rp.py warten
```

**Was passiert – auf dem [Server], von selbst:**
1. Status-Seite auf Port 8001 startet
2. **Host-Check:** GPUs mit Power-Limit, P2P zwischen den Karten (mit Datenvergleich), CPU, RAM-Bandbreite, Disk – fehlt P2P, stoppt der Pod hier mit „fehler“
3. **Download** der gepinnten Modell-Revision
4. **vLLM startet:** Gewichte laden, CUDA-Graphen bauen → „bereit“

Auf dem Laptop siehst du diese Phasen mit Uhrzeit; am Ende die Kaltstartzeit.

## 5. Prüfen [Laptop] – 1 Min.

```bash
python3 runpod/rp.py check
```

**Was passiert:** prüft P2P, CPU, RAM, das geladene Modell und dass eine Anfrage **ohne Key abgewiesen** wird (Regel 8). Ergebnis landet in `results/<profil>/pod-check/`.

Schlägt etwas fehl: **sofort** `python3 runpod/rp.py down` und mit Schritt 3 neu anlegen – meist landet der neue Pod auf einem anderen Host.

## 6. Messen [Laptop]

Wie in [ANLEITUNG Teil 3](../ANLEITUNG.md#teil-3--messen-laptop). Adresse und Key des Pods findet die Testsuite selbst – in `benchmark.conf` ist dafür nichts einzutragen.

## 7. Aufräumen [Laptop] + [Web]

```bash
python3 runpod/rp.py down          # Pod terminieren, Kosten verbuchen, Watchdog beenden
python3 runpod/rp.py kosten        # Summe aller verbuchten Pods
```

Danach **[Web]** im RunPod-Dashboard unter *Pods* und *Billing* kontrollieren, dass nichts mehr läuft.

## Wenn etwas schiefgeht

| Problem | Lösung |
|---|---|
| `RUNPOD_API_KEY fehlt` / `RUNPOD_GPU_ID fehlt` | Schritt 1 |
| `rp.py warten` zeigt `fehler: P2P …` | Host verwerfen: `rp.py down`, neu anlegen |
| `Es läuft schon ein Pod` | Erst `python3 runpod/rp.py down`; im Notfall `python3 runpod/rp.py down-alle` |
| Laptop war zugeklappt | `python3 runpod/rp.py status` bzw. RunPod-Dashboard: noch laufende Pods löschen |

Technische Details zu `rp.py` (alle Befehle, Watchdog, Kostenbuch): [runpod/README.md](../runpod/README.md).
