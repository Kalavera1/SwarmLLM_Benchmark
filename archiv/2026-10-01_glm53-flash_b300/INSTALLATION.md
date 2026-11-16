# Installation: GLM-5.3-Flash auf RunPod bis in OpenWebUI

Schritt für Schritt nachgebaut nach dem erfolgreichen Lauf vom 01.10.2026. Beschrieben ist **genau der Weg, der
funktioniert hat**. Was dabei schiefging, steht jeweils als Warnung dabei, damit man es sich spart.

Alle Befehle laufen auf dem **Heimserver mit OpenWebUI** im Ordner dieses Repos, außer es steht
„**im Pod**“ dabei.

| | |
|---|---|
| Kosten | 7,96 $/h für 1× B300, sekundengenau. Die Uhr läuft ab dem Start des Pods, auch während des Ladens |
| Zeit | ~15 Min. Einrichtung + ~15 Min., bis der Pod antwortet |
| Ergebnis | OpenAI-kompatible API mit GLM-5.3-Flash (1M Kontext), in OpenWebUI nur für Admins sichtbar |

Die getesteten Werte auf einen Blick: [`runpod/template.md`](runpod/template.md).

---

## Schritt 1: RunPod-Konto und Guthaben

1. Konto auf **runpod.io** anlegen.
2. **Billing** → Guthaben aufladen. Rechnung für einen Testabend: ~15 Min. Anlauf (~2 $) plus 8 $ je Teststunde.
   30–40 $ reichen für ein paar Stunden.

## Schritt 2: API-Key erzeugen

Der Key schützt den Server: Nur wer ihn kennt, darf das Modell benutzen. Ohne Key ist der Endpunkt offen im Internet.

```bash
umask 077 && openssl rand -hex 24 > api-key.txt     # erzeugt 48 zufällige Zeichen, Datei nur für dich lesbar
cat api-key.txt                                     # anzeigen und für Schritt 4 kopieren
```

> **Der Key gehört nie ins Git, in Doku, Chats oder Screenshots.** `api-key.txt` steht in `.gitignore`. Ist er
> doch irgendwo gelandet: neuen erzeugen und im Pod austauschen. Der alte ist danach wertlos.

Statt der Datei geht auch eine Umgebungsvariable für die laufende Sitzung: `export VLLM_API_KEY=…`. Die Skripte
nehmen dann diese.

## Schritt 3: Pod starten

1. RunPod → **Pods** → **+ Deploy**.
2. Als GPU **B300** wählen, Anzahl **1**.
3. Die vorgeschlagene Vorlage stehen lassen. Bei uns war es **RunPod PyTorch**
   (`runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`). Sie wird in Schritt 4 ohnehin ersetzt.
4. **Deploy** klicken. Der Pod erscheint in der Liste, mit Preis (bei uns **7,96 $/h**) und einer **ID**
   (z. B. `abc123xyz456`). Die ID notieren, die Skripte brauchen sie.

> Die Vorlage **nicht** so lassen und vLLM von Hand im Terminal installieren. Das ist bei uns an den Versionen
> von CUDA und PyTorch gescheitert. Schritt 4 tauscht das Image gegen das fertige vLLM-Image.

## Schritt 4: Pod umstellen (Edit Pod)

Im Pod oben links auf **⋮** (die drei Punkte neben „Stop“) → **Edit Pod**.

> Oben steht die Warnung „Editing a running Pod will cause it to reset. All Pod data will be lost!“. Das ist hier
> gewollt. Aber: **Jedes weitere Speichern setzt den Pod wieder zurück**, und die 191 GB Modelldateien werden neu
> geladen. Deshalb alles in einem Durchgang eintragen und **vor dem Speichern** prüfen.

Die Felder von oben nach unten:

### Container image
```
vllm/vllm-openai:nightly
```
> Kein Leerzeichen davor oder dahinter. Sonst meldet RunPod nur „invalid repo“, und man sucht ewig.

### Container start command
Eine einzige Zeile, genau so:
```
nvidia/GLM-5.3-Flash-NVFP4 --served-model-name glm-5.3-flash --host 0.0.0.0 --port 8000 --tensor-parallel-size 1 --kv-cache-dtype fp8 --max-model-len 1048576 --max-num-seqs 4 --gpu-memory-utilization 0.92 --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm47
```
Es sind nur die Argumente, `vllm serve` steckt schon im Image. Was jedes Argument bedeutet:
[`runpod/template.md`](runpod/template.md#container-start-command).

> **Bleibt das Feld leer, startet vLLM ohne Fehlermeldung mit einem Mini-Modell (`Qwen/Qwen3-0.6B`).** Genau das
> ist uns passiert, weil die Eingabe nicht gespeichert war.

### Container disk
`500` GB. Die Modelldateien belegen 191 GB.

### Expose HTTP ports
`8000` ergänzen. Bei uns stand dort `8888` aus der Vorlage. Daraus wurde `8888,8000`. Die 8888 stört nicht.

> **Ohne Port 8000 ist der Server von außen nicht erreichbar.** Man bekommt dann nur `404`, obwohl vLLM läuft.

### Expose TCP ports
Unverändert lassen (`22`).

### Environment variables
Den Abschnitt **Environment variables** aufklappen. Bei uns standen dort schon `PUBLIC_KEY` und
`JUPYTER_PASSWORD` aus der Vorlage. Die bleiben einfach stehen.

Dann für jede der drei Variablen auf **+ Add Environment variable** klicken und links den Namen (Key), rechts den
Wert (Value) eintragen:

| Key | Value |
|---|---|
| `VLLM_API_KEY` | der Key aus Schritt 2 (Inhalt von `api-key.txt`) |
| `VLLM_ENGINE_READY_TIMEOUT_S` | `3600` |
| `HF_HUB_ENABLE_HF_TRANSFER` | `1` |

Danach sieht die Liste so aus:

```
PUBLIC_KEY                   ssh-ed25519 AAAA…          (aus der Vorlage)
JUPYTER_PASSWORD             …                          (aus der Vorlage)
HF_HUB_ENABLE_HF_TRANSFER    1
VLLM_ENGINE_READY_TIMEOUT_S  3600
VLLM_API_KEY                 <dein Key aus api-key.txt>
```

> RunPod zeigt dort den Hinweis „Environment variables are not encrypted“. Wer den Key dort im Klartext stehen
> hat, sollte ihn nach dem Test wegwerfen und beim nächsten Mal einen neuen erzeugen. Für solche Werte bietet
> RunPod über das Schlüsselsymbol auch **Secrets** an. Das haben wir **nicht getestet**.
>
> `HF_HUB_ENABLE_HF_TRANSFER` ist veraltet (vLLM warnt im Log), schadet aber nicht und kann auch weg.
> `VLLM_ENGINE_READY_TIMEOUT_S` dagegen ist wichtig: Laden und Kompilieren dauern länger, als vLLM
> standardmäßig wartet.

### Prüfen und speichern
Noch einmal alle Felder ansehen: Image, Start Command, 500 GB, Port 8000, drei Variablen. Dann **Save**.

Falls der Pod danach als gestoppt angezeigt wird („Not running“): auf **Start** klicken.

## Schritt 5: Warten, bis der Pod bereit ist (~15 Min.)

**Connect**-Tab: Zuerst lädt RunPod das Image („Downloading your container…“, Fortschrittsbalken). Danach
erscheint unter „HTTP services“ **Port 8000** mit „Initializing…“. Die gelbe Meldung „This is taking longer than
expected“ ist in dieser Phase normal.

**Logs**-Tab: oben rechts auf **Container** umschalten. Unter **System** sieht man nur Docker-Meldungen.
Die wichtigen Zeilen in dieser Reihenfolge:

| Log-Zeile | Bedeutung |
|---|---|
| `version 0.30.1rc1 … model nvidia/GLM-5.3-Flash-NVFP4` | vLLM startet mit dem richtigen Modell |
| `Resolved architecture: Glm5NextForConditionalGeneration` | Modell erkannt |
| `Loading model from scratch...` | **Download läuft**. Jetzt kommen 5–10 Min. lang keine neuen Zeilen, das ist normal |
| `GPU KV cache size: 9,352,372 tokens` | Modell liegt auf der Karte, 1M Kontext passt |
| `JIT kernel warmup finished in 145.23s` | Rechenkerne für die B300 kompiliert |
| `[AutoTuner] …` | letzter Schritt |
| `Application startup complete.` | **fertig**, Port 8000 springt auf „Ready“ |

Wer während der Stille nachsehen will, dass etwas passiert: **Connect** → **Enable web terminal** einschalten
und **im Pod** eingeben:

```bash
du -sh /root/.cache/huggingface      # Download: wächst bis ~191 GB
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv   # ~183 GB = Modell geladen
```

Auch die Pod-Übersicht hilft. Während des Autotunings standen GPU-Auslastung und Grafikspeicher bei ~78 % bzw. 90 %.

**Fehlerbilder aus unserem Lauf:**

| Was man sieht | Ursache | Lösung |
|---|---|---|
| Log zeigt `Qwen/Qwen3-0.6B` | Start Command leer | Schritt 4, Start Command eintragen |
| System-Log: Container startet immer wieder neu | Fehler beim Start | Container-Log lesen, meist Tippfehler im Start Command |
| `404` von außen, obwohl vLLM läuft | Port 8000 nicht freigegeben | Schritt 4, Expose HTTP ports |
| „invalid repo“ beim Image | Leerzeichen im Feld | Feld leeren, neu eintippen |

## Schritt 6: Funktionstest

```bash
./scripts/test-endpunkt.sh <POD-ID>
```

So sah es bei uns aus, wenn alles stimmt:

```
== 1. Modellliste
   glm-5.3-flash max_len 1048576
== 2. Ohne Key muss abgelehnt werden
   ok (401)
== 3. Chat + Tempo
   Reasoning vorhanden: True
== 4. Tool-Call (für OpenWebUI-Agenten nötig)
   ok: wetter {"ort": "Berlin"}
```

> Steht bei 2. **`WARNUNG: HTTP 200`**, ist der Endpunkt **ohne Schutz** offen: `VLLM_API_KEY` fehlt.
> Sofort in Schritt 4 nachtragen oder den Pod beenden.
>
> Bei 3. kann die Antwort leer sein. Dann hat das Modell die 400 Test-Token komplett zum Nachdenken verbraucht.
> Das ist kein Fehler.

## Schritt 7: In OpenWebUI einbinden

```bash
./scripts/openwebui-verbinden.sh <POD-ID>
```

Das Skript
1. sichert die OpenWebUI-Datenbank (`webui.db` + `-wal`/`-shm` als `.bak-<Zeitstempel>`),
2. trägt `https://<POD-ID>-8000.proxy.runpod.net/v1` mit dem Key als OpenAI-Verbindung ein,
3. startet OpenWebUI neu (~30 s für alle nicht erreichbar).

Danach steht `glm-5.3-flash` in der Modellauswahl, **nur für Admins**. Normale Nutzer sehen es nicht, solange man
es nicht ausdrücklich freigibt.

Empfohlene Einstellungen in OpenWebUI unter **Workspace → Modelle → glm-5.3-flash**. Abgeleitet aus den
Messungen, in der Oberfläche selbst nicht durchgetestet:

- **Function Calling: Native**, sonst funktioniert das Terminal nicht.
- Parameter **`reasoning_effort` = `high`**. Ohne die Einstellung denkt GLM bei Code 2–4 Minuten.
- **Max Tokens** mindestens 32.000. Sonst bleibt die Antwort leer, weil das ganze Budget fürs Denken draufgeht.

Andere OpenWebUI-Installation (anderer Container-Name, Port, Ordner): siehe [`docs/skripte.md`](docs/skripte.md).

## Schritt 8: Messen (optional)

```bash
./scripts/bench.py <POD-ID> --kontext 1048576      # Tempo, 2/4 Nutzer, Tool-Calls, Kontext bis 1M   (~5 Min.)
./scripts/bench2.py <POD-ID>                       # Laststufen, Kontext unter Last, ABAP, Denktiefe  (~15–20 Min.)
```

Ergebnisse landen in `ergebnisse/`. PDF-Bericht daraus bauen: siehe [`docs/skripte.md`](docs/skripte.md#pdf-berichtpy).

## Schritt 9: Abbauen, sonst läuft die Rechnung weiter

```bash
./scripts/openwebui-verbinden.sh --aus
```

Das entfernt die Verbindung wieder. Sonst wartet OpenWebUI bei jedem Laden der Modellliste auf die tote Adresse.
**Achtung:** `--aus` leert *alle* OpenAI-Verbindungen in OpenWebUI. Bei uns gab es außer RunPod keine.

Dann in RunPod: Pod → **⋮** → **Terminate**.

> **Terminieren, nicht nur stoppen.** Ein gestoppter Pod kostet für seine Disk weiter. Zum Schluss unter
> **Billing** kontrollieren, dass nichts mehr läuft. Den Key aus Schritt 2 danach am besten wegwerfen.
