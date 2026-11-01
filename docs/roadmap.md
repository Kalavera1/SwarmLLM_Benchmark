# Roadmap

Jede Phase endet mit einem Review. Erst danach beginnt die nächste. Vor jeder Phase die [Erfahrungen](erfahrungen.md) durchsehen.

| Phase | Ziel | Kosten | Status |
|---|---|---|---|
| 0 | Repo-Grundgerüst | 0 € | in Review |
| 0b | CI und Arbeitsregeln | 0 € | in Review |
| 1 | Lokaler Stack | 0 € | offen |
| 2 | Testsuite (V-Modell) | 0 € | offen |
| 3 | RunPod vorbereiten | wenige € (Volume, CPU-Pod) | offen |
| 4 | Erster GPU-Test | ca. 1 h GPU | offen |
| 5 | DeepSeek V4 Flash | mehrere h GPU | offen |
| 6 | GLM-5.3-Flash | mehrere h GPU | offen |
| 7 | Auswertung | 0 € | offen |

---

## Phase 0 – Repo-Grundgerüst

**Ergebnis:** README mit Ziel und Regeln, `.gitignore`, `.env.example`, Roadmap, Entscheidungslog.

**Fertig, wenn:** reviewt und ins private Repo gepusht.

## Phase 0b – CI und Arbeitsregeln

**Ergebnis:**
- GitHub Actions mit drei Prüfungen bei jedem Pull Request und Push auf `main`:
  - Secret-Scan mit gitleaks über die gesamte Historie, plus eigene Regel für die Zugangsdaten-Variablen dieses Projekts (Regel 2)
  - Pin-Prüfung für Images, Actions und Modell-Revisionen, mit eigenen Unit-Tests (Regel 4)
  - Linter: ruff für Python, shellcheck für Bash
- `CLAUDE.md` mit den Arbeitsregeln für jede Claude-Sitzung

**Fertig, wenn:** Die CI läuft im Pull Request grün, und ein absichtlich eingebauter Verstoß wird erkannt (lokal nachgewiesen).

## Phase 1 – Lokaler Stack

**Ergebnis:** `local/` mit einem Docker-Swarm-Stack (Single-Node auf dem Mediaserver) für LiteLLM und einen Mock-Server, der die OpenAI-API nachahmt – noch keine GPU. Der LiteLLM-Master-Key liegt als Docker Secret vor, nicht in einer Datei im Repo. Die bestehende OpenWebUI (Port 8081, Compose) bleibt unverändert und bekommt LiteLLM nur als zusätzliche OpenAI-Verbindung.

**Wichtig:** Aus dem OpenWebUI-Container heißt `localhost` der Container selbst, nicht der Mediaserver. Die Verbindung geht deshalb über die LAN-IP des Mediaservers oder `host.docker.internal`.

**Fertig, wenn:** `docker stack deploy` läuft durch, alle Services sind gesund, und ein Chat in der bestehenden OpenWebUI geht über LiteLLM zum Mock und zurück.

## Phase 2 – Testsuite (V-Modell)

**Ergebnis:** `bench/` als Testsuite mit vier Ebenen nach dem V-Modell:

| Ebene | Frage | Testblöcke |
|---|---|---|
| Unit | Rechnen unsere eigenen Skripte richtig? | Auswertung, Parser, Prüfskripte |
| Integration | Funktioniert die Kette? | OpenWebUI → LiteLLM → Ziel, Key-Schutz, Streaming, Tool-Call-Format |
| System | Wie verhält sich der Server? | Prefill und Zeit bis zum ersten Token (8k–1M), Decode bei 1–32 parallelen Anfragen, Nadeltest (128k, 500k, 1M), Lastmix (4 Coding-Agenten plus 8–10 Chat-Nutzer), Prefix-Caching warm gegen kalt |
| Abnahme (Eval) | Wie gut ist das Modell fachlich? | ABAP, Coding, Tool-Calls, Rechenaufgabe mit bekannter Lösung bei verschiedenen Denktiefen |

**Bedienung:** Eine Kommandozeile, die jeden Block einzeln startet, z. B. `bench run abap --profil glm53-flash`. Ergebnisse landen pro Profil und Block mit Zeitstempel unter `results/`. Nach einer Änderung läuft nur der betroffene Block neu.

**ABAP-Eval:** Grundlage sind die 7 Aufgaben aus dem B300-Test (ALV-Report, ABAP-SQL, CDS View, RAP, Fehlersuche, Modernisierung, AMDP). Damals wurde nur durch Lesen bewertet. Neu:
- Codeblöcke werden aus der Antwort gezogen und automatisch mit **abaplint** geprüft (Syntaxcheck ohne SAP-System).
- Jede Aufgabe bekommt eine feste Kriterienliste, z. B. für die Fehlersuche die erwarteten Funde. Damit ist der Vergleich zwischen Modellen fair.
- Was abaplint nicht abdeckt, wird über die Kriterienliste bewertet. Welche Teile das genau sind, etwa SQLScript in AMDP oder Behavior Definitions, klären wir beim Bau.

**Aus dem B300-Test:**
- eigener User-Agent (der RunPod-Proxy blockt `Python-urllib`)
- Aufwärmrunde vor jeder Messung, nicht mitgezählt
- `max_tokens` ≥ 32k, Denk-Tokens getrennt erfasst, Denktiefe als Parameter

**Fertig, wenn:** Alle Blöcke laufen einzeln gegen den Mock, die Unit-Tests sind grün, und jedes Ergebnis ist ein gültiges JSON mit Metadaten.

## Phase 3 – RunPod vorbereiten

**Ergebnis:** `runpod/` mit Skripten für Network Volume und einen günstigen CPU-Pod, der die gepinnten Gewichte aufs Volume lädt und Prüfsummen schreibt.

**Fertig, wenn:** Gewichte vollständig und geprüft auf dem Volume, im selben Rechenzentrum, in dem 2× RTX PRO 6000 verfügbar sind.

## Phase 4 – Erster GPU-Test

**Ergebnis:** Pod-Check und Startprotokoll:
- `nvidia-smi topo -m` und P2P-Test zwischen beiden Karten
- System-RAM und `/dev/shm`
- DeepSeek V4 Flash startet, eine Testanfrage läuft
- Richtiges Modell geladen (nicht das vLLM-Standardmodell) und Anfrage ohne API-Key wird abgewiesen
- Verbindung per SSH-Tunnel oder direktem TCP-Port statt HTTP-Proxy; eine Anfrage mit über 2 Min. Prefill kommt vollständig an
- Kaltstartzeit gemessen
- Watchdog löscht den Pod zuverlässig (terminieren, nicht nur stoppen)

**Wichtig:** Funktioniert P2P auf dem Host nicht, wird der Pod gelöscht und ein anderer Host gewählt. `NCCL_P2P_DISABLE=1` ist nur Notausgang, weil es Leistung kostet.

**Fertig, wenn:** Check-Ergebnis und Startprotokoll liegen in `results/`.

## Phase 5 – DeepSeek V4 Flash

**Ergebnis:** Alle Blöcke der Testsuite aus Phase 2, dazu Varianten:
- KV-Cache FP8 gegen NVFP4
- KV-Offloading in den RAM an/aus

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 6 – GLM-5.3-Flash

**Ergebnis:** Dieselben Blöcke der Testsuite, dazu Varianten:
- Speculative Decoding: DFlash2 gegen MTP gegen aus
- KV-Cache FP8 gegen NVFP4

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 7 – Auswertung

**Ergebnis:** Vergleichstabelle, Kosten pro Lauf, Empfehlung, ob und welches Modell für den produktiven Einsatz taugt. Als Referenz dient der B300-Test vom 01.10.2026 (1 Karte, ca. 8 $/h, deutlich schnellerer Prefill). Optional: Qwen3.8-Flash-Next nachziehen.
