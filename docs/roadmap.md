# Roadmap

Jede Phase endet mit einem Review. Erst danach beginnt die nächste. Vor jeder Phase die [Erfahrungen](erfahrungen.md) durchsehen.

Kosten-Schätzungen für GPU-Phasen: Google Cloud G4 (`g4-standard-96`, Flex-Start), gerechnet mit 4,95 $/h (Stand 18.11.2026, Herleitung im [Entscheidungslog](entscheidungen.md)). Stunden einschließlich Start und Download. Die harte Ausgabengrenze ist das Limit der Firmenkarte; das Google-Budget warnt nur.

| Phase | Ziel | Kosten (geschätzt) | Status |
|---|---|---|---|
| 0 | Repo-Grundgerüst | 0 € | erledigt |
| 0b | CI und Arbeitsregeln | 0 € | erledigt |
| 1 | Optional: Chat-Stack (LiteLLM, OpenWebUI) | 0 € | optional, für Messungen nicht nötig; Test offen |
| 2 | Testsuite | 0 € | in Review |
| 3 | Startskripte, RunPod-Steuerung, Modellprofile, `benchmark.conf` | 0 € | in Review |
| 4 | Erster GPU-Test mit Qwen3.8-27B | 1–2 h ≈ 5–10 $ | offen |
| 5 | Qwen3.8-Flash-Next | 3–5 h ≈ 15–25 $ | offen |
| 5b | Qwen4 (offene Modelle, z. B. Qwen4-27B, Qwen4-Flash) | je 1–5 h ≈ 5–25 $ | wartet auf Veröffentlichung; die Modell-Wache meldet sie |
| 6 | GLM-5.3-Flash | 3–5 h ≈ 15–25 $ | offen |
| 7 | DeepSeek V4.1 Flash (Rang 2) | 6–10 h ≈ 30–50 $; eigener Server 0 € | Profil offen |
| 8 | GLM-5.3 Q3 (Rang 1, wichtigstes Modell), ohne Bilder | 6–10 h ≈ 30–50 $; eigener Server 0 € | Runtime offen |
| 9 | Optional: DeepSeek V4 Flash, GLM-5.3-Flash über Purtell-Runtime | je 3–5 h | optional |
| 10 | Auswertung | 0 € | offen |

---

## Phase 0 – Repo-Grundgerüst

**Ergebnis:** README mit Ziel und Regeln, `.gitignore`, Vorlage für Zugangsdaten (heute `benchmark.conf.example`), Roadmap, Entscheidungslog.

**Fertig, wenn:** reviewt und gepusht.

## Phase 0b – CI und Arbeitsregeln

**Ergebnis:**
- GitHub Actions mit drei Prüfungen bei jedem Pull Request und Push auf `main`:
  - Secret-Scan mit gitleaks über die gesamte Historie, plus eigene Regel für die Zugangsdaten-Variablen dieses Projekts (Regel 2)
  - Pin-Prüfung für Images, Actions und Modell-Revisionen, mit eigenen Unit-Tests (Regel 4)
  - Linter: ruff für Python, shellcheck für Bash
- `CLAUDE.md` mit den Arbeitsregeln für jede Claude-Sitzung

**Fertig, wenn:** Die CI läuft im Pull Request grün, und ein absichtlich eingebauter Verstoß wird erkannt (lokal nachgewiesen).

## Phase 1 – Optional: Chat-Stack

**Für die Messungen nicht nötig.** Die Testsuite misst direkt gegen vLLM und startet den Mock selbst. Der Stack ist für zwei Dinge gedacht: ein Modell während eines Laufs im Chat ausprobieren, und als Vorlage für den späteren Betrieb mit OpenWebUI auf dem Zielserver.

**Ergebnis:** `chat-stack/` mit einem Docker-Swarm-Stack (Single-Node, beliebiger Linux-Rechner mit Docker) für LiteLLM und einen Mock-Server, der die OpenAI-API nachahmt. Der LiteLLM-Master-Key liegt als Docker Secret vor, nicht in einer Datei im Repo. Eine vorhandene OpenWebUI bekommt LiteLLM nur als zusätzliche OpenAI-Verbindung.

**Wichtig:** Aus dem OpenWebUI-Container heißt `localhost` der Container selbst, nicht der Host. Die Verbindung geht deshalb über die LAN-IP des Docker-Rechners oder `host.docker.internal`.

**Fertig, wenn:** `docker stack deploy` läuft durch, alle Services sind gesund, und ein Chat in OpenWebUI geht über LiteLLM zum Mock und zurück.

## Phase 2 – Testsuite

**Ergebnis:** `bench/` als Testsuite mit vier Ebenen nach dem V-Modell, nur Python-Standardbibliothek:

| Ebene | Frage | Testblöcke |
|---|---|---|
| Unit | Rechnen unsere eigenen Skripte richtig? | Statistik, Text- und Bildgeneratoren, Auswertung, Wächter |
| Integration | Funktioniert die Kette? | Modellname, Key-Schutz, Streaming, Tool-Call-Format, Kontext ≥ 64k für Agenten |
| System | Wie verhält sich der Server? | **Wächter** (kaputte Ausgaben, Endlosschleifen), **Prefill** (8k–1M, kalt und warm; 500k ist Pflicht schon in der Schnellstufe), **Decode** (1–64 parallele Anfragen), **Nadeltest** (32k–1M, 500k Pflicht), **Lastmix** (4 Coding-Agenten plus Chat-Nutzer bis 30 gesamt, gegen Zielwerte), **Bilder** (Zeit bis zum ersten Token mit 0/1/4 Bildern) |
| Abnahme (Eval) | Wie gut ist das Modell fachlich? | **Agentenschleife** mit Tools, **Bilder** mit bekannter Antwort, **Rechenaufgabe** bei verschiedenen Denktiefen, **ABAP** mit abaplint und Kriterienliste |

**Bedienung:** `python3 -m bench run <block …|alle> --profil <name> --stufe schnell|voll`. Die Stufe `schnell` misst nur die wichtigsten Punkte (ca. 45 Min. für alle Blöcke), `voll` alle. Ergebnisse landen pro Profil und Block mit Zeitstempel unter `results/`. Nach einer Änderung läuft nur der betroffene Block neu.

**Messregeln:**
- eigener User-Agent (der RunPod-Proxy blockt `Python-urllib`)
- Aufwärmrunde vor jedem Block, nicht mitgezählt
- `max_tokens` großzügig, Denk-Tokens getrennt erfasst, Denktiefe als Parameter
- vLLM-Zähler (`/metrics`) vor und nach jedem Block: Prefix-Cache-Treffer, Akzeptanz beim spekulativen Decoding, Verdrängungen
- spekulatives Decoding nur mit natürlichen Texten bewerten, nicht mit Zufallstokens
- jedes Ergebnis enthält Dauer und Kosten des Blocks

**Fertig, wenn:** Alle Blöcke laufen einzeln gegen den Mock, die Unit-Tests sind grün, und jedes Ergebnis ist ein gültiges JSON mit Metadaten.

## Phase 3 – Startskripte, RunPod-Steuerung, Modellprofile

**Ergebnis:**
- `server/start-im-container.sh`: ein Startskript für alle GPU-Server (RunPod, Cloud-VM, Vast.ai, eigener Server) mit Host-Check (P2P, CPU, RAM-Bandbreite, Power-Limit); `server/lokal-starten.sh` für Rechner mit Docker.
- `benchmark.conf` für alle eigenen Werte und `ANLEITUNG.md` für den Ablauf von einem beliebigen Steuerrechner aus; Starten und Abbauen des GPU-Servers je Anbieter in `anleitung/` (RunPod, Google Cloud, Vast.ai, eigener Server).
- `server/im-container-starten.sh` für Anbieter mit SSH in den Container (Vast.ai) und `server/vast-watchdog.sh`: Die Vast-Instanz löscht sich nach Ablauf selbst (Regel 5).
- Neue Modelle aufnehmen: `profiles/neu.py` legt ein Profil als Entwurf an und prüft vorab, ob das Modell auf 2 Karten passt. Die Modell-Wache (`profiles/wache.py`, täglich als GitHub Action) meldet Modelle aus `profiles/beobachten.txt` als Issue, sobald sie auf Hugging Face erscheinen.
- `runpod/` für die REST-API v2: GPU-Typen anzeigen, Pod anlegen, prüfen, Status, löschen. Ohne Network Volume: Der Pod lädt die gepinnte Revision beim Start selbst.
- Vor jedem Start Kostenschätzung und Bestätigung. Jeder Pod wird mit tatsächlichen Kosten in `results/kosten.csv` verbucht. Die Ausgabengrenze steht im RunPod-Konto (Kartenlimit).
- Watchdog auf dem Steuerrechner, der den Pod nach `POD_MAX_MINUTES` terminiert.
- `profiles/` mit einem Ordner pro Modell: Startparameter, Fähigkeiten (Bilder, Tool-Parser, Denkstufen), Pin-Skript für Image-Digest und Modell-Revision.

**Fertig, wenn:** Skripte und Profile reviewt sind und ein Trockenlauf (`--trocken`) den API-Aufruf korrekt zeigt, ohne einen Pod anzulegen.

## Phase 4 – Erster GPU-Test mit Qwen3.8-27B

Auf Google Cloud G4 ([anleitung/google-cloud.md](../anleitung/google-cloud.md)); die Punkte zu Pod, Proxy und Watchdog gelten nur beim Ausweichweg RunPod.

**Ergebnis:** Host-Check und Startprotokoll:
- `nvidia-smi topo -m` und P2P-Test zwischen beiden Karten
- System-RAM und `/dev/shm`
- Richtiges Modell geladen (nicht das vLLM-Standardmodell) und Anfrage ohne API-Key wird abgewiesen
- Verbindung über direkten TCP-Port statt HTTP-Proxy; eine Anfrage mit über 2 Min. Prefill kommt vollständig an
- Kaltstartzeit inklusive Download gemessen
- Auto-Stopp greift: die G4-VM wird nach `--max-run-duration` gelöscht (bei RunPod: Watchdog terminiert den Pod)
- Testsuite in Stufe `schnell` einmal komplett durchgelaufen

**Wichtig:** Funktioniert P2P auf dem Host nicht, wird die VM gelöscht und neu angelegt (anderer Host bzw. andere Zone). `NCCL_P2P_DISABLE=1` ist nur Notausgang, weil es Leistung kostet.

**Fertig, wenn:** Check-Ergebnis, Startprotokoll und Ergebnisse liegen in `results/`.

## Phase 5 – Qwen3.8-Flash-Next

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`. Varianten:
- MTP an/aus
- KV-Cache BF16 gegen FP8 (FP8 lief auf SM120 laut Community nicht mit dem QSA-Pfad)

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 5b – Qwen4 (sobald offene Gewichte erscheinen)

**Auslöser:** Issue der Modell-Wache. Stand 17.11.2026 gibt es nur Qwen4-Max als API-Vorschau ohne Gewichte; offene kleinere Modelle sind ohne Datum angekündigt.

**Weg:** je nach Größe wie ein Vorgänger – Einschätzung im [Entscheidungslog](entscheidungen.md):
- **Qwen4-27B:** passt laut Rechnung locker (≈ 54 GB in BF16); Profil mit `python3 profiles/neu.py qwen4-27b --quelle <repo> --wie qwen38-27b`.
- **Qwen4-Flash:** Größe offen; Vorläufer ist Qwen3.8-Flash-Next (Architektur „Qwen4Exp“), also `--wie qwen38-flash-next-fp8`. Erst die Vorprüfung von `neu.py` zeigt, ob es in den VRAM passt.
- **Qwen4-Max:** nicht auf 2 Karten (2,4 Billionen Parameter, Gewichte geschlossen).

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`, wie Phase 5. Danach in die Rangfolge der README einordnen.

## Phase 6 – GLM-5.3-Flash

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`. Varianten:
- MTP an/aus
- TP2 gegen TP2 mit Expert-Parallel (Community meldet ca. +50 % bei einem Nutzer)

**Wichtig:** Der Wächter-Block muss bestehen, bevor Durchsatzwerte zählen.

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 7 – DeepSeek V4.1 Flash

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`, mit 500k Kontext als Pflichtpunkt. Nur 2 Karten, Experten teils auf der CPU (Rezept theogravity). Zusätzlich festhalten: CPU, RAM-Bandbreite und NVMe des Hosts, weil das Tempo davon abhängt. Host: Google Cloud G4 (EPYC Turin), später der eigene Server.

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 8 – GLM-5.3 Q3 (wichtigstes Modell)

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`. GLM-5.3 in Q3 (≈ 343 GB) passt nicht in 2× 96 GB; ein Teil der Experten läuft auf der CPU.

**Vorher zu klären:**
- **Runtime:** llama.cpp (erprobt, aber langsames Einlesen: ≈ 83 tok/s mit 2-Bit auf 2× RTX PRO 6000) oder KTransformers/SGLang (liest auf der GPU ein, für GLM-5 dokumentiert, für GLM-5.3 auf 2 Karten noch ohne Messung). Beide sind kein vLLM – das Startskript braucht dafür einen eigenen Startweg.
- ~~Bildfähigkeit~~ geklärt: GLM-5.3 nimmt nur Text an (Z.ai-Doku), der Block `bilder` entfällt.
- **Denken** lässt sich bei GLM-5.3 laut Unsloth nicht abschalten, nur abstufen (`reasoning_effort` low/high/max). Tempo-Messungen laufen dann mit `low`; `DENKSTUFEN` im Profil entsprechend setzen.
- **Host** mit ≥ 384 GB RAM: Google Cloud G4 (360 GB) ist dafür knapp; eigener Server mit voll bestückten 12 Kanälen.

**Wichtig:** 500k Kontext ist hier das größte Risiko. Mit llama.cpp-Tempo dauert ein 500k-Prompt über eine Stunde.

## Phase 9 – Optional: DeepSeek V4 Flash, GLM-5.3-Flash über Purtell-Runtime

Optional, nach Phase 8. DeepSeek V4 Flash kann keine Bilder; die Purtell-Runtime ist kein Upstream-vLLM.

## Phase 10 – Auswertung

**Ergebnis:** Vergleichstabelle (`python3 -m bench auswertung`), Kosten pro Lauf, Empfehlung, ob und welches Modell für den produktiven Einsatz taugt. Als Referenz dient der B300-Test vom 01.10.2026 (1 Karte, ca. 8 $/h, deutlich schnellerer Prefill).
