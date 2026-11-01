# Roadmap

Jede Phase endet mit einem Review. Erst danach beginnt die nächste. Vor jeder Phase die [Erfahrungen](erfahrungen.md) durchsehen.

| Phase | Ziel | Kosten | Status |
|---|---|---|---|
| 0 | Repo-Grundgerüst | 0 € | in Review |
| 1 | Lokaler Stack | 0 € | offen |
| 2 | Benchmark-Skripte | 0 € | offen |
| 3 | RunPod vorbereiten | wenige € (Volume, CPU-Pod) | offen |
| 4 | Erster GPU-Test | ca. 1 h GPU | offen |
| 5 | DeepSeek V4 Flash | mehrere h GPU | offen |
| 6 | GLM-5.3-Flash | mehrere h GPU | offen |
| 7 | Auswertung | 0 € | offen |

---

## Phase 0 – Repo-Grundgerüst

**Ergebnis:** README mit Ziel und Regeln, `.gitignore`, `.env.example`, Roadmap, Entscheidungslog.

**Fertig, wenn:** reviewt und ins private Repo gepusht.

## Phase 1 – Lokaler Stack

**Ergebnis:** `local/` mit einem Docker-Swarm-Stack (Single-Node auf dem Mediaserver) für LiteLLM und einen Mock-Server, der die OpenAI-API nachahmt – noch keine GPU. Der LiteLLM-Master-Key liegt als Docker Secret vor, nicht in einer Datei im Repo. Die bestehende OpenWebUI (Port 8081, Compose) bleibt unverändert und bekommt LiteLLM nur als zusätzliche OpenAI-Verbindung.

**Wichtig:** Aus dem OpenWebUI-Container heißt `localhost` der Container selbst, nicht der Mediaserver. Die Verbindung geht deshalb über die LAN-IP des Mediaservers oder `host.docker.internal`.

**Fertig, wenn:** `docker stack deploy` läuft durch, alle Services sind gesund, und ein Chat in der bestehenden OpenWebUI geht über LiteLLM zum Mock und zurück.

## Phase 2 – Benchmark-Skripte

**Ergebnis:** `bench/` mit Skripten für:
- Prefill und Zeit bis zum ersten Token (8k, 32k, 128k, 500k, 1M)
- Decode bei 1, 4, 8, 16 (und 32) parallelen Anfragen
- Nadeltest (versteckte Fakten bei 128k, 500k, 1M)
- Lastmix: 4 Coding-Agenten mit wachsendem Kontext plus 8–10 Chat-Nutzer
- Prefix-Caching: Folgeanfrage warm gegen kalt

Jedes Skript schreibt ein JSON mit Messwerten und Metadaten. Aus dem B300-Test:
- eigener User-Agent (der RunPod-Proxy blockt `Python-urllib`)
- Aufwärmrunde vor jeder Messung, nicht mitgezählt
- `max_tokens` ≥ 32k, Denk-Tokens getrennt erfasst, Denktiefe als Parameter

**Fertig, wenn:** Alle Skripte laufen gegen den Mock und erzeugen gültiges JSON.

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

**Ergebnis:** Komplette Testmatrix aus Phase 2, dazu Varianten:
- KV-Cache FP8 gegen NVFP4
- KV-Offloading in den RAM an/aus

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 6 – GLM-5.3-Flash

**Ergebnis:** Gleiche Testmatrix, dazu Varianten:
- Speculative Decoding: DFlash2 gegen MTP gegen aus
- KV-Cache FP8 gegen NVFP4

**Fertig, wenn:** Ergebnisse und Zusammenfassung in `results/`.

## Phase 7 – Auswertung

**Ergebnis:** Vergleichstabelle, Kosten pro Lauf, Empfehlung, ob und welches Modell für den produktiven Einsatz taugt. Als Referenz dient der B300-Test vom 01.10.2026 (1 Karte, ca. 8 $/h, deutlich schnellerer Prefill). Optional: Qwen3.8-Flash-Next nachziehen.
