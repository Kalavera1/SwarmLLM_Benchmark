# Roadmap

Jede Phase endet mit einem Review. Erst danach beginnt die nächste. Vor jeder Phase die [Erfahrungen](erfahrungen.md) durchsehen.

Kosten-Schätzungen für GPU-Phasen: 2× RTX PRO 6000 in der Community Cloud, 3,28 $/h (Stand 15.11.2026). Budget der ersten Runde: 100 $.

| Phase | Ziel | Kosten (geschätzt) | Status |
|---|---|---|---|
| 0 | Repo-Grundgerüst | 0 € | in Review |
| 0b | CI und Arbeitsregeln | 0 € | in Review |
| 1 | Lokaler Stack | 0 € | in Review, Test auf dem Mediaserver offen |
| 2 | Testsuite | 0 € | in Arbeit |
| 3 | RunPod-Skripte und Modellprofile | 0 € | in Arbeit |
| 4 | Erster GPU-Test mit Qwen3.8-27B | ca. 1 h ≈ 4 $ | offen |
| 5 | Qwen3.8-Flash-Next | 3–5 h ≈ 10–16 $ | offen |
| 6 | GLM-5.3-Flash | 3–5 h ≈ 10–16 $ | offen |
| 7 | DeepSeek V4.1 Flash (wichtigstes Modell) | Weg A: 0 € (eigener Server) bzw. RunPod je nach Host; Weg B: 3–4 h × 6,56 $/h ≈ 20–26 $ | Weg offen |
| 7b | Optional: DeepSeek V4 Flash, GLM über Purtell-Runtime | je 3–5 h | nur bei Restbudget |
| 8 | Auswertung | 0 € | offen |

---

## Phase 0 – Repo-Grundgerüst

**Ergebnis:** README mit Ziel und Regeln, `.gitignore`, `.env.example`, Roadmap, Entscheidungslog.

**Fertig, wenn:** reviewt und gepusht.

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

## Phase 3 – RunPod-Skripte und Modellprofile

**Ergebnis:**
- `runpod/` für die REST-API v2: GPU-Typen anzeigen, Pod anlegen, prüfen, Status, löschen. Ohne Network Volume: Der Pod lädt die gepinnte Revision beim Start selbst.
- Budgetgrenze: Vor jedem Start Kostenschätzung und Abbruch, wenn das Restbudget nicht reicht. Jeder Pod wird mit tatsächlichen Kosten in `results/kosten.csv` verbucht.
- Watchdog auf dem Steuerrechner, der den Pod nach `POD_MAX_MINUTES` terminiert.
- `profiles/` mit einem Ordner pro Modell: Startparameter, Fähigkeiten (Bilder, Tool-Parser, Denkstufen), Pin-Skript für Image-Digest und Modell-Revision.

**Fertig, wenn:** Skripte und Profile reviewt sind und ein Trockenlauf (`--trocken`) den API-Aufruf korrekt zeigt, ohne einen Pod anzulegen.

## Phase 4 – Erster GPU-Test mit Qwen3.8-27B

**Ergebnis:** Pod-Check und Startprotokoll:
- `nvidia-smi topo -m` und P2P-Test zwischen beiden Karten
- System-RAM und `/dev/shm`
- Richtiges Modell geladen (nicht das vLLM-Standardmodell) und Anfrage ohne API-Key wird abgewiesen
- Verbindung über direkten TCP-Port statt HTTP-Proxy; eine Anfrage mit über 2 Min. Prefill kommt vollständig an
- Kaltstartzeit inklusive Download gemessen
- Watchdog löscht den Pod zuverlässig (terminieren, nicht nur stoppen)
- Testsuite in Stufe `schnell` einmal komplett durchgelaufen

**Wichtig:** Funktioniert P2P auf dem Host nicht, wird der Pod gelöscht und ein anderer Host gewählt. `NCCL_P2P_DISABLE=1` ist nur Notausgang, weil es Leistung kostet.

**Fertig, wenn:** Check-Ergebnis, Startprotokoll und Ergebnisse liegen in `results/`.

## Phase 5 – Qwen3.8-Flash-Next

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`. Varianten:
- MTP an/aus
- KV-Cache BF16 gegen FP8 (FP8 lief auf SM120 laut Community nicht mit dem QSA-Pfad)

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 6 – GLM-5.3-Flash

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`. Varianten:
- MTP an/aus
- TP2 gegen TP2 mit Expert-Parallel (Community meldet ca. +50 % bei einem Nutzer)

**Wichtig:** Der Wächter-Block muss bestehen, bevor Durchsatzwerte zählen.

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 7 – DeepSeek V4.1 Flash

**Ergebnis:** Stufe `schnell`, bei Erfolg `voll`, mit 500k Kontext als Pflichtpunkt. Weg A (2 Karten, CPU-Experten) oder Weg B (4 Karten, Karmic Kraken) – siehe [Entscheidungslog](entscheidungen.md). Bei Weg A zusätzlich festhalten: CPU, RAM und NVMe des Hosts, weil das Tempo davon abhängt.

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 7b – Optional: DeepSeek V4 Flash, GLM über Purtell-Runtime

Nur wenn nach Phase 7 noch Budget übrig ist. DeepSeek V4 Flash kann keine Bilder; die Purtell-Runtime ist kein Upstream-vLLM.

## Phase 8 – Auswertung

**Ergebnis:** Vergleichstabelle (`python3 -m bench auswertung`), Kosten pro Lauf, Empfehlung, ob und welches Modell für den produktiven Einsatz taugt. Als Referenz dient der B300-Test vom 01.10.2026 (1 Karte, ca. 8 $/h, deutlich schnellerer Prefill).
