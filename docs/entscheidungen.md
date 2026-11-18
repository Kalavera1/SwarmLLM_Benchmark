# Entscheidungslog

Kurz festgehalten: was entschieden wurde, warum, und wo es herkommt. Neue Einträge oben.

---

## 2026-11-18 – Google Cloud G4 ist der Hauptweg; Flex-Start statt Spot

**Entscheidung:**
- **Alle Messungen laufen auf Google Cloud G4** (`g4-standard-96`: 2× RTX PRO 6000, 96 vCPU AMD EPYC Turin, 360 GB RAM), Region `europe-west4`. RunPod und Vast.ai bleiben Ausweichwege, der eigene Server ist für die Endmessung.
- **Bezugsmodell Flex-Start:** wartet höchstens 2 Stunden auf Karten, wird während der Laufzeit nicht unterbrochen und endet nach `--max-run-duration` mit Löschen. Das erfüllt Regel 5 ohne eigenen Watchdog. Standard 4 Stunden, für DeepSeek V4.1 Flash und GLM-5.3 Q3 10 Stunden.
- **VM per `gcloud` in der Cloud Shell:**
  - Image „Deep Learning VM“ `common-cu129-ubuntu-2404-nvidia-580` mit `install-nvidia-driver=True`
  - Bootlaufwerk Hyperdisk Balanced, 600 GB (G4 kann kein Persistent Disk)
  - Firewall für 8000/8001 nur von der IP des Laptops
- **Kostenrahmen:** 30–55 Stunden × 4,95 $ ≈ 150–275 $; Freigabe beim Einkauf 500 €. Die Stunden sind eigene Schätzung (Tabelle in der Roadmap plus 50 % Puffer). 4,95 $ = Flex-Start-Listenpreis 4,50 $ plus 10 %, weil der reguläre Preis in `europe-west4` 10 % über dem US-Preis liegt (9,90 statt 9,00 $).

**Warum:** Entscheidung des Nutzers. Flex-Start statt Spot: Spot kann laut Google jederzeit abgebrochen werden, dann ist ein Messlauf halb verloren; der Preisunterschied ist klein (Spot `europe-west4` 4,10 $/h). `europe-west4` ist im Spot-Preis die günstigste EU-Region mit G4 und hat drei Zonen dafür.

**Noch nicht geprüft:**
- Die G4-Schritte sind nicht selbst durchgespielt.
- Ob das Deep-Learning-Image Docker und das NVIDIA Container Toolkit mitbringt, steht nicht in der gelesenen Doku. Die Anleitung prüft es mit `docker run --gpus all … nvidia-smi`.
- Einen Flex-Start-Preis für Europa nennt Google nicht; laut Google werden die Flex-Start-Preise im November 2026 aktualisiert.
- Ob G4 auch das globale Kontingent `GPUS_ALL_REGIONS` braucht, sagt die gelesene Doku nicht.
- Ganz neue Konten bekommen GPU-Kontingent nicht immer; deshalb lieber ein vorhandenes Firmenkonto nutzen.

**Quellen (abgerufen 18.11.2026):**
- Preise: [gcloud-compute.com: g4-standard-96 je Region, Stand 15.11.2026](https://gcloud-compute.com/g4-standard-96.html), [Google: beschleunigungsoptimierte VMs](https://cloud.google.com/products/compute/pricing/accelerator-optimized?hl=en), [Google: Flex-Start-Preise](https://cloud.google.com/products/dws/pricing?hl=de)
- Bezugsmodelle: [Google: Flex-Start bis 7 Tage, nicht unterbrechbar; Spot jederzeit](https://docs.cloud.google.com/ai-hypercomputer/docs/consumption-models?hl=en), [Google: Laufzeit begrenzen](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime)
- VM: [Google: G4-VM anlegen – Hyperdisk, kein Persistent Disk, Flex-Start-Befehl](https://docs.cloud.google.com/ai-hypercomputer/docs/create/create-vm-g4), [Google: Deep-Learning-Images mit Treiber 580](https://docs.cloud.google.com/deep-learning-vm/docs/images), [Google: `install-nvidia-driver=True`](https://docs.cloud.google.com/deep-learning-vm/docs/cli)
- Standorte und Kontingent: [Google: GPU-Standorte, Stand 28.10.2026](https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones?hl=de), [Google: Kontingente für RTX PRO 6000](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/gpu-quota-requirement)
- Abrechnung: [Google: Vertragspartner je Land](https://cloud.google.com/terms/google-entity?hl=fr), [Google-Blog: Budgets warnen, begrenzen nicht](https://cloud.google.com/blog/topics/developers-practitioners/protect-your-google-cloud-spending-budgets)
- Erfahrungsberichte: [keine GPUs im Testkonto](https://discuss.google.dev/t/cant-access-gpus-on-a-compute-engine-with-a-personal-account/145823/2), [GPU-Kontingent bei neuem Konto abgelehnt](https://discuss.google.dev/t/cloud-run-l4-gpu-quota-stays-0-on-a-paid-account-auto-grant-never-fires-even-in-a-brand-new-project/393926)

## 2026-11-17 – Neue Modelle aufnehmen: `neu.py` und Modell-Wache; Qwen4 auf 2 Karten

**Entscheidung:**
- **`profiles/neu.py`** legt ein neues Modell als Profil-Entwurf an. Vorher fragt es Hugging Face nach Größe, Bildfähigkeit und Kontext und rechnet grob, ob die Gewichte in 2× 96 GB passen: gut (≤ 75 %, Rest für KV-Cache), knapp (≤ 95 %) oder nur mit Teilen im Arbeitsspeicher (dann geschätzter RAM-Bedarf). Mit `--wie <profil>` übernimmt es die Startparameter eines ähnlichen Modells.
- **Modell-Wache:** `profiles/beobachten.txt` listet Modelle, auf die wir warten. Die GitHub Action `modell-wache.yml` sucht täglich mit `profiles/wache.py` auf Hugging Face und legt für neue Repos ein Issue an. Schon gemeldete Repos und Repos aus Profilen kommen nicht noch einmal.
- **Qwen4** steht als Phase 5b fest im Plan und als erster Eintrag auf der Beobachtungsliste (Autoren `Qwen` und `nvidia`).

**Warum:** Vorgabe des Nutzers: Qwen4 aufnehmen, sobald es da ist, und generell neue Modelle einfach in den Test aufnehmen können. Die Wache braucht keine Zugangsdaten außer dem automatischen Token des Laufs. Sie läuft auf GitHub und nicht im Container dieser Sitzung, denn der erreicht Hugging Face nicht. Im öffentlichen Repo kostet sie nichts; in einem privaten Repo verbraucht sie etwa eine Actions-Minute am Tag.

**Qwen4 auf 2× RTX PRO 6000 – Einschätzung (Stand 17.11.2026):**

| Modell | Stand | Passt auf 2 Karten? | Weg |
|---|---|---|---|
| Qwen4-27B | als offenes Modell angekündigt, nicht erschienen; Architektur offiziell offen (Kernel-Code nennt es „dense“, unbestätigt) | ja, falls dicht: 27 Mrd. Parameter ≈ 54 GB in BF16, ≈ 27 GB in FP8 (2 bzw. 1 Byte je Parameter, eigene Rechnung) – passt sogar auf eine Karte | wie Qwen3.8-27B (vLLM, Data-Parallel 2) |
| Qwen4-Flash | genannt; Größe und Lizenz offen | offen. Der Vorläufer Qwen3.8-Flash-Next (125B + 51B N-gram-Tabelle) läuft in FP8 auf 2 Karten, mit der Tabelle im Arbeitsspeicher | wie Qwen3.8-Flash-Next |
| Qwen4-Plus | genannt; bisher bei Qwen nur per API | voraussichtlich keine Gewichte | – |
| Qwen4-Max | API-Vorschau seit 11.11.2026; 2,4 Billionen Parameter, 71 Mrd. aktiv; Gewichte geschlossen | nein: selbst mit 4 Bit ≈ 1,2 TB (eigene Rechnung) | – |

**Software:** Qwen3.8-Flash-Next ist laut vLLM-Recipe die Vorschau auf die Qwen4-Architektur. Diese Architektur heißt „Qwen4Exp“ (Hugging-Face-Konfiguration `Qwen4ExpTextConfig`); vLLM betreibt sie laut Recipe, llama.cpp seit Ende August. Bauen die offenen Qwen4-Modelle darauf auf, laufen sie zum Start wahrscheinlich schon – bestätigt ist das nicht. Die Messung von Qwen3.8-Flash-Next in Phase 5 zeigt vorab, wie diese Architektur auf unseren Karten läuft.

**Quellen (abgerufen 17.11.2026):** [Ultrathink, 16.11.2026: Qwen4-Max](https://ultrathink.ai/news/alibaba-qwen4-max-2-4t-closed-weights), [Stealthmodels, Stand 11.11.2026: Status je Qwen4-Modell, „Qwen4-27B dense“ im Kernel-Code](https://stealthmodels.com/qwen-4), [Newszest, 03.11.2026: vier Modelle genannt, keine Gewichte](https://www.newszest.in/2026/11/qwen4-4-models-named-0-open-weights.html), [Yotta Labs, 16.11.2026: Qwen4-27B angekündigt, nicht erschienen](https://www.yottalabs.ai/post/qwen-4-27b-release-date-specs-hardware-what-is-known-2026), [vLLM Recipe: Qwen3.8-Flash-Next – „Qwen4 architecture preview“](https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next), [vLLM PR #61607: Qwen4Exp (Qwen3.8-Flash-Next)](https://github.com/vllm-project/vllm/pull/61607), [Startup Fortune, 24.10.2026: llama.cpp PR #27742 „qwen4exp“ gemergt](https://startupfortune.com/github-pull-requests-point-to-alibabas-next-open-qwen-model-nearing-release/)

## 2026-11-17 – GLM-5.3 Q3 ohne Bilder; Qwen4 noch nicht testbar

**Entscheidung:**
- **GLM-5.3 Q3 wird ohne Bilder gemessen** (`VISION=0`, Block `bilder` entfällt).
- **Qwen4 kommt dazu, sobald es offene Gewichte gibt.** Bis dahin bleibt Qwen3.8-Flash-Next auf Rang 4 – laut vLLM-Recipe ist es die Vorschau auf die Qwen4-Architektur.

**Warum:** Vorgabe des Nutzers: GLM-5.3 ohne Bilder testen, falls es keine kann, und Hinweis, dass Qwen 4 erschienen ist. Laut Z.ai nimmt GLM-5.3 nur Text an; bildfähig in der GLM-Reihe ist GLM-5.3-Flash (Rang 3). Von Qwen4 gibt es Stand 17.11.2026 nur **Qwen4-Max** als API-Vorschau (seit 11.11.2026): 2,4 Billionen Parameter, 71 Mrd. aktiv, Bilder, Gewichte nicht veröffentlicht – auf 2 Karten nicht lauffähig. Kleinere Modelle mit offenen Gewichten hat Alibaba nur „bald“ angekündigt, ohne Datum; genannt wurden Qwen4-27B, -Flash und -Plus, ohne Angaben zu Größe oder Lizenz.

**Korrektur:** Eine erste Fassung dieses Eintrags (PR #20) hatte Qwen3.8-Flash-Next gestrichen – „Qwen 4 ist auch raus“ war als „fliegt raus“ gelesen statt als „ist erschienen“. Mit PR #21 zurückgenommen; Profil und Rang 4 sind wieder da.

**Folge für den Betrieb:** Die Anforderung „Bilder“ erfüllt GLM-5.3 Q3 allein nicht. Wird es das Hauptmodell, braucht es für Bilder ein zweites Modell (z. B. GLM-5.3-Flash oder Qwen3.8-27B) – das ist eine Frage der Auswertung (Phase 10), nicht der Messung.

**Nebenbei aus der Unsloth-Doku:** Bei GLM-5.3 lässt sich das Denken nicht abschalten, nur abstufen (`reasoning_effort` low/high/max). Das betrifft `DENKSTUFEN` im Profil.

**Quellen (abgerufen 17.11.2026):**
- GLM-5.3: [Z.ai: GLM-5.3 – „currently supports text-only inputs“](https://docs.z.ai/guides/llm/glm-5.3), [Hugging Face: zai-org/GLM-5.3 – Pipeline „text-generation“](https://huggingface.co/zai-org/GLM-5.3), [Unsloth: GLM-5.3 – Denken, UD-Q3_K_XL 343 GB](https://unsloth.ai/docs/models/glm-5.3), [Apidog: GLM-5.3-Flash als erstes nativ multimodales Modell der GLM-5-Reihe](https://apidog.com/blog/glm-5-3-flash-what-is/)
- Qwen4: [Ultrathink, 16.11.2026: Qwen4-Max, 2,4T MoE, Gewichte geschlossen](https://ultrathink.ai/news/alibaba-qwen4-max-2-4t-closed-weights), [Stealthmodels, Stand 11.11.2026: Status je Qwen4-Modell](https://stealthmodels.com/qwen-4), [vLLM Recipe: Qwen3.8-Flash-Next – „Qwen4 architecture preview“](https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next)

## 2026-11-17 – Auto-Stopp auf Vast.ai: Die Instanz löscht sich selbst

**Entscheidung:** `server/im-container-starten.sh` startet auf Vast.ai einen Watchdog (`server/vast-watchdog.sh`), der die Instanz nach 90 Min. (oder `--minuten N`) über die Vast-API löscht. Er läuft in der Instanz selbst und nutzt den Key, den Vast.ai jeder Instanz nur für sie mitgibt (`CONTAINER_API_KEY`). Zeitpunkt sichtbar unter `:8001/watchdog.json`; verlängern durch neu Stellen, ein „aus“ gibt es nicht.

**Warum:** Regel 5 – kein GPU-Lauf ohne Auto-Stopp. Bei Vast.ai legt man die Instanz in der Weboberfläche an; ein Watchdog auf dem Laptop wie bei RunPod würde einen Vast-Key für das ganze Konto auf dem Laptop brauchen und endet, wenn der Laptop zuklappt. Der Key der Instanz verlässt die Instanz nie. In der Vast-Doku fand sich keine maximale Laufzeit mit Löschen; das Ende der Mietdauer **stoppt** die Instanz nur.

**Noch nicht selbst geprüft:** Getestet ist der Ablauf gegen eine nachgebaute API (DELETE mit Bearer-Key kommt an). Ob die echte API den Instanz-Key per REST für DELETE annimmt, steht so nur mittelbar in der Doku (dort per CLI). Deshalb steht in [anleitung/vast-ai.md](../anleitung/vast-ai.md) ein einmaliger Test mit einer billigen Instanz.

**Quellen (abgerufen 17.11.2026):** [Vast.ai: Docker-Umgebung – CONTAINER_ID, CONTAINER_API_KEY, Löschen von innen](https://docs.vast.ai/guides/instances/docker-environment), [Vast.ai: Instanz löschen – DELETE /api/v0/instances/{id}](https://docs.vast.ai/destroy-an-instance), [Vast.ai: API mit Bearer-Key](https://docs.vast.ai/api-reference/hello-world), [Vast.ai FAQ: Mietende stoppt die Instanz](https://docs.vast.ai/guides/reference/faq/instances)

## 2026-11-17 – Anleitung je GPU-Server getrennt

**Entscheidung:** `ANLEITUNG.md` enthält nur noch, was für jeden GPU-Server gleich ist: einrichten, pinnen, messen, Ergebnisse. Starten, Prüfen und Abbauen des GPU-Servers steht je Anbieter in `anleitung/` (RunPod, Google Cloud, Vast.ai, eigener Server). Für Vast.ai kommt `server/im-container-starten.sh` dazu: startet das gemeinsame Startskript im schon laufenden Container, ohne `docker run`.

**Warum:** RunPod-Schritte wie `rp.py gpus` standen unter den allgemeinen Schritten und wirkten wie Pflicht für jeden Weg (Hinweis des Nutzers). Getrennte Dokumente zeigen pro Anbieter nur, was dort wirklich zu tun ist.

## 2026-11-17 – Nur 2 Karten; GLM-5.3 Q3 ist das wichtigste Modell

**Entscheidung:**
- Getestet wird **ausschließlich mit 2× RTX PRO 6000**. Der Weg über 4 Karten (Karmic Kraken `ds41-flash` für DeepSeek V4.1 Flash) entfällt.
- Rangfolge nach Wichtigkeit: **1. GLM-5.3 in Q3**, 2. DeepSeek V4.1 Flash, 3. GLM-5.3-Flash, 4. Qwen3.8-Flash-Next, 5. Qwen3.8-27B als Referenz. Getestet wird in umgekehrter Reihenfolge – erst das billige Referenzmodell, zuletzt die großen.

**Warum:** Der Zielserver hat 2 Karten. Messungen mit 4 Karten sagen über ihn nichts aus.

**Was GLM-5.3 Q3 auf 2 Karten bedeutet:**
- Q3 (Unsloth `UD-Q3_K_XL`) ist ≈ 343 GB groß und passt nicht in 192 GB VRAM; ein Teil der Experten läuft auf der CPU. Ein Test auf 2× RTX PRO 6000 Max-Q mit 128 GB RAM schloss Q3 deshalb aus und nutzte 2-Bit (`UD-IQ2_M`, 238,6 GB): llama.cpp, 11–12 tok/s Ausgabe, ≈ 83 tok/s Einlesen, 64k Kontext.
- Daraus folgt für den Zielserver **≥ 384 GB RAM** in 12 Kanälen (abgeleitet: Gewichte minus VRAM plus Reserve, und DeepSeek V4.1 Flash braucht ≈ 250 GB).
- **500k Kontext ist mit llama.cpp nicht realistisch** (≈ 83 tok/s Einlesen → über eine Stunde für 500k). KTransformers/SGLang rechnet das Einlesen auf der GPU und ist für GLM-5 dokumentiert; für GLM-5.3 auf 2 Karten gibt es noch keine Messung. Die Runtime wird in Phase 8 entschieden.
- Zum Vergleich: Die EXL3-3-Bit-Fassung (273 GiB) läuft nur auf 4 Karten (ca. 55–60 tok/s) – für uns nicht anwendbar.

**Quellen:** [XDA: GLM 5.3 auf 2× RTX PRO 6000 Max-Q (12.10.2026)](https://www.xda-developers.com/you-can-run-a-744b-model-on-your-own-hardware/), [AlphaSignal: GLM-5.3 EXL3 3.0bpw, 273 GiB, 4 Karten](https://alphasignal.ai/news/infatoshi-squeezes-glm-5-3-s-753b-parameters-into-273-gib-for-multi-gpu), [KTransformers: GLM-5-Tutorial](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/kt-kernel/GLM-5-Tutorial.md)

## 2026-11-16 – Keine Budgetgrenze im Skript; Ausgabenlimit im RunPod-Konto

**Entscheidung:** `runpod/rp.py` bricht nicht mehr wegen eines Budgets ab; `RUNPOD_BUDGET_USD` entfällt. Das Skript zeigt vor dem Start weiter die geschätzten Kosten, fragt nach Bestätigung und verbucht jeden Pod in `results/kosten.csv` (`rp.py kosten` zeigt die Summe). Die Ausgabengrenze setzt ihr als Limit der hinterlegten Firmenkarte im RunPod-Konto.

**Warum:** Ein Limit beim Anbieter gilt für alles, was über das Konto läuft – auch für Pods, die per Weboberfläche oder auf einem anderen Rechner gestartet werden. Eine Grenze im Skript würde nur Läufe vom selben Rechner sehen und doppelt pflegen, was das Konto ohnehin kann.

## 2026-11-16 – pin.py holt Image-Digests direkt von der Registry

**Entscheidung:** `profiles/pin.py` fragt Docker Hub bzw. ghcr.io direkt über die Registry-API (anonymes Lese-Token, Header `Docker-Content-Digest`); Docker ist nur noch Ersatzweg. Neu: `--trocken` zeigt an, was eingetragen würde, ohne das Profil zu ändern.

**Warum:** Der Steuerrechner (Laptop) hat nicht unbedingt Docker. Angefragt wird der Multi-Arch-Index, damit derselbe Digest herauskommt wie bei `docker buildx imagetools inspect`.

## 2026-11-16 – Kein fester Mediaserver mehr: beliebiger Steuerrechner, Chat-Stack optional

**Entscheidung:**
- Gesteuert wird von einem **beliebigen Rechner** mit Python 3.11 (zunächst ein Laptop). Alle eigenen Werte stehen in `benchmark.conf` (Vorlage `benchmark.conf.example`); `.env.example` entfällt, `.env` wird nur noch als Fallback gelesen.
- Der Docker-Swarm-Stack mit LiteLLM ist **optional** und heißt jetzt `chat-stack/` statt `local/`. Er läuft auf jedem Linux-Rechner mit Docker.
- Messungen gehen **direkt an vLLM**, nicht über LiteLLM.

**Warum:**
- Es gibt keinen Rechner mehr, der dauerhaft als Mediaserver bereitsteht. Die Testsuite braucht keine GPU und keinen Docker-Stack – nur Python und Netz zum GPU-Server.
- Ziel des Projekts sind die Modelle und ihr Tempo. Der Chat-Stack hilft beim Ausprobieren und ist die Vorlage für den späteren Betrieb, beeinflusst aber keine Messung. Ein Gateway dazwischen könnte die Zahlen durch Caching sogar verfälschen.

**Folgen:** Der RunPod-Watchdog läuft auf dem Steuerrechner – während eines Laufs darf ein Laptop nicht in den Ruhezustand. Bei Cloud-VMs übernimmt die maximale Laufzeit mit automatischem Löschen diese Rolle.

## 2026-11-16 – Zielhardware bestätigt: EPYC 9745 und 2× RTX PRO 6000 Max-Q

**Befund (Angabe des Nutzers):** Zielserver (Lenovo ThinkSystem) mit
- 1× AMD EPYC 9745: 128 Kerne, 400 W, 2,4 GHz – Generation Zen 5c („Turin Dense“), 12 Speicherkanäle DDR5, laut Händlerangabe bis 576 GB/s
- 2× RTX PRO 6000 Blackwell **Max-Q Workstation Edition**, je 96 GB, 300 W, PCIe Gen5

Damit ist der Hinweis des Kollegen „EPYC 8004“ überholt: Der Zielserver hat einen EPYC 9005, keinen 8004. Die Richtung stimmt trotzdem – DDR5 und viele Speicherkanäle sind für DeepSeek V4.1 Flash mit CPU-Experten entscheidend.

**Folgen:**
- **RAM-Ausbau:** Für DeepSeek V4.1 Flash ≈ 250 GB nötig. Damit die volle Bandbreite ankommt, sollten **alle 12 Kanäle bestückt** sein (z. B. 12 × 32 GB = 384 GB). Mit weniger Modulen sinkt die Bandbreite – und damit das Tempo bei CPU-Auslagerung – fast proportional.
- **Cloud-Ersatz:** Vast.ai bietet 2× RTX PRO 6000 **Max-Q** an (Screenshot des Nutzers, 16.11.2026: 2,80–5,47 $/h für beide Karten), aber nur mit älteren CPUs (EPYC 7742/7453/7B13 mit DDR4 und PCIe 4, oder Xeon). Für Qwen und GLM (komplett im VRAM) passt das: Die Karten sind dieselben. Für DeepSeek V4.1 Flash mit CPU-Experten ist keiner davon repräsentativ.
- Der Host-Check misst die **RAM-Bandbreite**, damit Cloud-Ergebnisse auf den Zielserver umgerechnet werden können.

**Quellen:** Angaben des Nutzers; [EPYC 9745: 12 Kanäle DDR5, 576 GB/s (Händlerangabe)](https://aio.lv/en/product--amd-100-000001460--11379842.md), [AMD-Produktseite EPYC 9745](https://www.amd.com/en/products/processors/server/epyc/9005-series/amd-epyc-9745.html)

## 2026-11-16 – Zielhardware ist Max-Q (300 W); Skripte anbieterunabhängig

**Befund:** Der eigene Server zeigt bei `nvidia-smi` ein Power-Limit von **300 W** – das spricht für die RTX PRO 6000 **Max-Q** Workstation Edition (Bestätigung mit `nvidia-smi --query-gpu=name,power.limit --format=csv` steht aus). Server- und Workstation-Edition in der Cloud laufen mit 600 W. Treiber 615.71.09 – derselbe, mit dem das DeepSeek-V4.1-Rezept getestet wurde.

**Entscheidung:**
- Das Startskript im Container ist für RunPod, Vast.ai und den eigenen Server gleich; RunPod ist nur eine Automatisierung obendrauf.
- Modelle, die komplett im VRAM liegen (Qwen, GLM), dürfen in der Cloud gemessen werden. DeepSeek V4.1 Flash mit CPU-Auslagerung wird auf dem eigenen Server oder auf einem Host mit bekannter, ähnlicher CPU gemessen (Kollege: EPYC 8004 mit DDR5, ≈ 250 GB RAM).
- Jeder Host-Check speichert Power-Limit und CPU-Modell.

**Warum:**
- Prefill ist Rechenarbeit und leidet unter 300 W; Cloud-Karten mit 600 W wären dort zu optimistisch. Decode hängt vor allem an der Speicherbandbreite, die bei allen Varianten gleich ist.
- Bei CPU-Auslagerung bestimmen CPU, RAM-Bandbreite und NVMe das Tempo. RunPod lässt das CPU-Modell nicht auswählen; Vast.ai zeigt es pro Angebot (Stand 16.11.2026 pro Karte: WS ab 1,00 $/h, Median 1,49 $; S ab 1,33 $/h, Median 1,73 $ – laut Screenshot des Nutzers).

## 2026-11-16 – DeepSeek V4.1 Flash ist das wichtigste Modell, Weg noch offen

**Entscheidung:** DeepSeek V4.1 Flash (763B, Bilder, 1M Kontext) wird getestet. Offen ist, auf welchem Weg:

| Weg | Hardware | Vorteil | Nachteil |
|---|---|---|---|
| A: Rezept theogravity | 2× RTX PRO 6000 (Zielhardware) | 512k Kontext, ≈ 250 tok/s bei einem Nutzer, 41,6 s bis zum ersten Token bei 505k (Angaben des Autors) | ein Autor, eine Maschine; gepatchtes vLLM, eigene Images müssen gebaut werden; Tempo hängt an CPU, RAM (≥ 128 GiB empfohlen) und NVMe des Hosts – bei RunPod-Community-Hosts nicht planbar |
| B: Karmic Kraken `ds41-flash` | 4× RTX PRO 6000 | fertiges Image, Bilder verifiziert, ≈ 249 tok/s bei einem Nutzer (rtx6kpro-Wiki) | misst nicht die Zielhardware; ≈ 6,56 $/h |

**Warum nicht einfach quantisieren:** Selbst mit 3 Bit sind es ≈ 322 GiB Gewichte, also deutlich mehr als 192 GB VRAM.

**Quellen:** [theogravity/deepseek-flash-v4.1-dual-rtx-6000](https://github.com/theogravity/deepseek-flash-v4.1-dual-rtx-6000), [rtx6kpro: DeepSeek V4.1 Flash](https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md)

## 2026-11-16 – Geldschonend: Community Cloud ohne Network Volume

**Entscheidung:** GPU-Pods laufen standardmäßig in der **Community Cloud**. Es gibt **kein Network Volume**; die Gewichte lädt jeder Pod beim Start auf seine Container-Disk. Alle Testblöcke eines Modells laufen in **einem** Pod am Stück. Ein Budget in `.env` (`RUNPOD_BUDGET_USD`) begrenzt die Summe aller Läufe.

**Warum:**
- Preis pro Karte und Stunde (on-demand, Stand 15.11.2026): Community 1,64 $, Secure 2,69 $. Für 2 Karten 3,28 $/h gegen 5,38 $/h.
- Network Volumes gibt es bei RunPod **nur in der Secure Cloud** und kosten 0,07 $/GB/Monat, auch ohne laufenden Pod. 600 GB für alle Modelle wären ca. 42 $/Monat.
- Ein Download von ca. 30–190 GB beim Start kostet in der Community Cloud nur wenige Minuten GPU-Zeit. Bei geschätzt 6–8 Pod-Starts ist das günstiger als Volume plus Secure-Aufpreis.
- Jeder Kaltstart (Laden, JIT, Autotuning) kostet 10–20 Minuten. Deshalb ein Pod pro Modell, nicht pro Block.

**Folgen:** Phase 3 (Network Volume vorbefüllen) entfällt. Die Secure Cloud mit Volume bleibt als Option im Skript, falls Community-Hosts kein P2P bieten.

**Risiko:** Community-Hosts sind unterschiedlich gut, P2P zwischen den Karten klappt nicht überall. Der Pod-Check verwirft solche Hosts nach wenigen Minuten.

**Quellen:** [computeprices.com, RunPod RTX PRO 6000](https://computeprices.com/providers/runpod/gpus/rtx-pro-6000), [RunPod-Doku Network Volumes](https://docs.runpod.io/storage/network-volumes)

## 2026-11-16 – RunPod REST-API v2

**Entscheidung:** Die Skripte nutzen `https://api.runpod.io/v2`.

**Warum:** Die v1-API (`rest.runpod.io/v1`) ist laut RunPod zum 15.11.2026 abgeschaltet. In v2 heißen Felder anders (`gpu: {id, count}` statt `gpuTypeIds`, `cloud` statt `cloudType`, Standard ist `SECURE`), und es gibt kein Feld für eine maximale Laufzeit – der Watchdog bleibt also unsere Aufgabe.

**Quelle:** [RunPod: Migrate from v1](https://docs.runpod.io/api-reference-v2/migrate-from-v1), [Create a Pod](https://docs.runpod.io/api-reference-v2/pods/create-a-pod)

## 2026-11-16 – Neue Modellauswahl: Bilder, Agenten, Kosten

**Entscheidung:** Testreihenfolge (siehe [README](../README.md#modell-kandidaten)):

0. **Qwen3.8-27B** als Referenz und für den ersten GPU-Test
1. **Qwen3.8-Flash-Next** (FP8, N-gram-Tabelle im Host-RAM)
2. **GLM-5.3-Flash** als `nvidia/GLM-5.3-Flash-FP4-Local`
3. DeepSeek V4 Flash und GLM über die Purtell-Runtime nur bei Restbudget

**Warum:**
- **Bilder und Agenten sind neue Anforderungen.** DeepSeek V4 Flash kann nur Text. Die Bild-Variante DeepSeek-V4-Flash-Vision-Exp braucht laut vLLM-Recipe ca. 202 GB VRAM und gilt auf 2 Karten als nicht unterstützt.
- **Qwen3.8-27B zuerst:** offizielles vLLM-Recipe für die RTX Pro 6000, nur ca. 29 GB Download, läuft auf einer Karte. Damit lässt sich die ganze Kette (Pod, Check, Testsuite) für wenig Geld prüfen, bevor ein großes Modell Stunden kostet. Danach dient es als Referenz: Ist ein großes Modell schlecht, zeigt der Vergleich, ob es am Modell oder an der Umgebung liegt.
- **Qwen3.8-Flash-Next:** unabhängig gemessen auf 2× RTX PRO 6000 ca. 146 tok/s mit MTP bei 512k Kontext (stondo), läuft mit Upstream-vLLM ohne Spezial-Runtime.
- **GLM-5.3-Flash FP4-Local:** NVIDIA hat genau diese Hardware validiert (ca. 166 GiB, 1,8 Mio. Token FP8-KV-Cache). Laut Z.ai die besten Agenten-Werte unter den Kandidaten (Herstellerangaben). Ein Community-Test meldete auf SM120 Endlosschleifen in der Ausgabe – deshalb gibt es jetzt den Qualitäts-Wächter in der Testsuite.
- **Purtell-EXL3 wird nicht gestrichen**, aber nachrangig: Das Ziel ist ausdrücklich vLLM, und der NVIDIA-Checkpoint läuft in einem vLLM-Container.

**Herstellerangaben vs. Messung:** Die Agenten-Benchmarks (Terminal-Bench, SWE-bench, Toolathlon) stammen fast alle von den Herstellern. Entschieden wird nach unseren eigenen Messungen.

**Quellen:** [vLLM Recipes](https://recipes.vllm.ai/browse), [nvidia/GLM-5.3-Flash-FP4-Local](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local), [stondo: Qwen3.8-Flash-Next auf 2× RTX PRO 6000](https://stondo.github.io/posts/qwen38-flash-next-512k-two-rtx-pro-6000/), [Qwen3.8-27B Recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B), [DeepSeek-V4-Flash-Vision-Exp Recipe](https://recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp)

## 2026-11-16 – Testsuite misst gegen Ziele (SLOs), nicht nur Durchsatz

**Entscheidung:** Der Lastmix steigt bis 30 Nutzer und wird gegen feste Zielwerte bewertet: Zeit bis zum ersten Token im Chat (p90) und Ausgabetempo pro Nutzer. Ergebnis ist die größte Nutzerzahl, bei der die Ziele noch eingehalten werden. Neu dazu kommen die Blöcke Bilder, Agentenschleife und Qualitäts-Wächter.

**Warum:** Die eigentliche Frage ist „Wie viele Nutzer schafft das Modell, bevor es zu langsam wird?“. Reine Durchsatzzahlen beantworten das nicht. Spekulatives Decoding wird mit natürlichen Texten gemessen, nicht mit Zufallstokens, sonst sind die Akzeptanzraten unrealistisch.

## 2026-11-04 – Mediaserver: docker-ce statt Snap-Docker

**Entscheidung:** Der Mediaserver wechselt vom Snap-Docker auf das offizielle Paket `docker-ce` (bereits installiert, 29.9.0). Anleitung: [`betrieb/docker-snap-zu-docker-ce.md`](betrieb/docker-snap-zu-docker-ce.md).

**Warum:** Der AppArmor-Käfig des Snaps blockiert Netzwerkzugriffe des Daemons. Kein `docker pull` ist möglich, damit auch keine Updates und kein Phase-1-Deploy. Eine Reparatur ist nicht bekannt ([canonical/docker-snap#350](https://github.com/canonical/docker-snap/issues/350)).

**Abwägung:** Der Snap war bewusst gewählt, damit die Terminal-Container zusätzlich eingesperrt sind. Diese äußere Schicht fällt weg. Der Nutzer hat entschieden, zuerst umzuziehen und die Terminals danach gezielt zu härten (gVisor, eigenes Netz, Limits).

**Offen:** Härtung der Terminal-Container als eigener Schritt nach dem Umzug.

## 2026-11-01 – Testsuite nach V-Modell, ABAP als automatisch geprüfter Eval

**Entscheidung:** Die Tests werden in vier Ebenen gegliedert (Unit, Integration, System, Abnahme) und über eine Kommandozeile blockweise gestartet. Die Modellqualität bei ABAP wird als eigener Eval-Block gemessen: Codeblöcke werden mit abaplint geprüft, dazu kommt eine feste Kriterienliste je Aufgabe.

**Warum:**
- Jeder Block muss einzeln wiederholbar sein, damit nach einer Änderung nicht der ganze, teure GPU-Lauf neu nötig ist.
- Im B300-Test wurde ABAP nur durch Lesen bewertet und nicht kompiliert. Ein SAP-System steht privat nicht zur Verfügung; abaplint prüft die Syntax ohne SAP-System.

**Offen:** Wie weit abaplint CDS, Behavior Definitions (RAP) und SQLScript in AMDP abdeckt. Was nicht abgedeckt ist, bewertet die Kriterienliste.

## 2026-11-01 – Schlanke CI statt vollem Toolset

**Entscheidung:** GitHub Actions mit Secret-Scan (gitleaks), Pin-Prüfung und Linter (ruff, shellcheck). Actions und gitleaks sind per Commit-SHA bzw. Prüfsumme gepinnt. Kein Dependabot.

**Warum:**
- Ein geleakter RunPod-Key kostet echtes Geld; der Secret-Scan läuft deshalb über die gesamte Historie, mit einer eigenen Regel für die Variablen aus `.env.example`.
- Regel 4 (Alles gepinnt) wird technisch erzwungen statt nur dokumentiert.
- Dependabot würde ständig Updates für bewusst gepinnte Versionen vorschlagen. Updates testen wir gezielt.
- Die CI braucht keine Zugangsdaten, also auch keine GitHub Secrets.

**Offen:** Branch-Schutz für `main` (Merge nur per Pull Request mit grüner CI) muss der Repo-Inhaber in den GitHub-Einstellungen setzen. Bei privaten Repos setzt GitHub das nur mit einem Pro-Konto durch.

## 2026-11-01 – Lange Prompts nicht über den RunPod-HTTP-Proxy

**Entscheidung:** LiteLLM und die Benchmark-Skripte erreichen vLLM per SSH-Tunnel oder über einen direkt freigegebenen TCP-Port. Der HTTP-Proxy (`<pod-id>-8000.proxy.runpod.net`) dient höchstens für kurze Funktionstests.

**Warum:** Im B300-Test vom 01.10.2026 trennte der Proxy stille Verbindungen nach ca. 2 Minuten. Ein kalter 1M-Prompt braucht auf 2× RTX PRO 6000 bei GLM-5.3-Flash ca. 4,5–5 Minuten bis zum ersten Token, ein 500k-Prompt etwa 2 Minuten.

**Offen:** Ob der direkte TCP-Port auf dem gewählten RunPod-Host eine öffentliche IP bekommt – wird in Phase 4 geprüft.

**Quelle:** [Erfahrungen](erfahrungen.md)

## 2026-11-01 – Lokaler Stack als Docker Swarm statt Docker Compose

**Entscheidung:** LiteLLM und der Mock-Server laufen als Swarm-Stack (`docker stack deploy`) auf dem Mediaserver (Linux), zunächst auf einem einzigen Node. Die bestehende OpenWebUI dort (Port 8081, Compose) wird weiter genutzt und nur um LiteLLM als Verbindung ergänzt. Der PC mit WSL dient zum Entwickeln und Reviewen; die zweite OpenWebUI dort (Port 3000) bleibt unberührt.

**Warum:** Native Docker Secrets für Zugangsdaten, Healthchecks mit automatischem Neustart, und das Stack-File kann später auf weitere Nodes wachsen. Der Mediaserver läuft dauerhaft und hostet die OpenWebUI, die tatsächlich genutzt wird; aus WSL heraus wäre LiteLLM für andere Rechner wegen des WSL2-NAT nur mit Zusatzaufwand erreichbar.

**Folgen:**
- Swarm und die bestehenden Compose-Container laufen auf demselben Docker-Daemon nebeneinander. `docker swarm init` ändert an den Compose-Containern nichts.
- `docker stack deploy` liest keine `.env`-Datei automatisch. Zugangsdaten des Stacks kommen als Docker Secrets, die `.env` bleibt für die Skripte (RunPod, Hugging Face).
- Compose-Felder wie `build`, `container_name` und `depends_on` werden von Swarm ignoriert. Es werden nur fertige, gepinnte Images verwendet.
- Swarm umfasst nur den Mediaserver. Der RunPod-Pod kann kein Swarm-Node werden: kein Docker im Pod, und Swarm braucht UDP, das RunPod nicht unterstützt.

## 2026-10-31 – GLM-5.3-Flash über die Runtime von T.J. Purtell, Profil `k3`

**Entscheidung:** GLM-5.3-Flash wird mit `tpurtell/glm-5.3-flash-ext3-2x-rtx` getestet, nicht mit Karmic.

**Warum:**
- Einziges gefundenes Rezept mit nachgewiesenen 1M Tokens Kontext auf 2× RTX PRO 6000 (Nadeltest mit sechs Fakten bestanden).
- EXL3-Checkpoint mit ca. 127 GiB statt 166–175 GiB bei NVFP4 – dadurch 16 parallele Slots und ein KV-Pool von rund 2,8–2,9 Mio. Tokens.
- Komplett über Umgebungsvariablen steuerbar, passt zu RunPod.
- Profil `k3` statt Standard `k325`: bei 16 parallelen Anfragen deutlich mehr Durchsatz (laut Upstream 1.119 statt 832 tok/s), einzeln praktisch gleich.

**Bekannte Schwächen:** Prefill nur ca. 4.200–4.600 tok/s (128k ≈ 30 s bis zum ersten Token). DFlash2-Drafter nur für Forschung/Evaluation lizenziert.

**Quellen:** `tpurtell/glm-5.3-flash-ext3-2x-rtx`, `samuelcardillo/glm-5.3-flash-2x-rtx-pro-6000-blackwell`

## 2026-10-31 – P2P zwischen den Karten ist Pflicht

**Entscheidung:** Ein RunPod-Host, auf dem CUDA-P2P zwischen beiden Karten nicht funktioniert, wird nicht genutzt.

**Warum:** Karmic (PCIe-All-Reduce) und das Purtell-Rezept (prüft P2P vor dem Start) bauen darauf auf. Der verbreitete Workaround `NCCL_P2P_DISABLE=1` aus 2025 verhindert Hänger, kostet aber Leistung. BIOS/IOMMU lassen sich auf RunPod nicht ändern.

## 2026-10-30 – Karmic Kraken für DeepSeek V4 Flash

**Entscheidung:** DeepSeek V4 Flash läuft mit dem Karmic-Kraken-Image von Local Inference Lab, gepinnt per Digest.

**Warum:**
- Upstream-vLLM hat für die Sparse-Attention von DeepSeek V4 auf SM120 (RTX PRO 6000) keinen fertigen Kernel. Karmic bringt ihn mit (B12X), dazu PCIe-optimiertes All-Reduce, KV-Offloading und schnelles Laden (InstantTensor).
- Bekannte Referenz: Community-Rezepte für DeepSeek V4 Flash auf RTX PRO 6000 (u. a. das rtx6kpro-Wiki) setzen auf genau diese Image-Linie.

**Risiken:** Pre-Release, sehr hohes Release-Tempo, wenige Maintainer. Deshalb nie den `-beta`-Tag, immer Digest.

**Quelle:** `local-inference-lab/blackwell-llm-docker`

## 2026-10-30 – RunPod als Anbieter, LiteLLM und OpenWebUI lokal

**Entscheidung:** GPU-Instanzen bei RunPod, Gateway und Frontend auf dem eigenen Rechner.

**Warum:**
- Minutengenaue Abrechnung, Network Volumes für Gewichte und Caches, API für Automatisierung.
- In RunPod-Pods ist kein Docker und kein Docker Compose möglich – das vLLM-Image wird direkt das Pod-Image, alles andere läuft lokal.

**Offen:** Ob RunPod genug System-RAM und `/dev/shm` für KV-Offloading bereitstellt – wird in Phase 4 geprüft.

## 2026-10-30 – Eigenes privates Repo, strikt isoliert

**Entscheidung:** Neues privates Repo im persönlichen GitHub-Account. Kein Code, keine Configs und keine Zugangsdaten aus anderen Stack-Projekten.

**Warum:** Ein eigenständiges Repo ohne fremde Abhängigkeiten (Actions-Runner, MCPs, MCPOs) bleibt überschaubar und lässt sich jederzeit vollständig nachvollziehen.
