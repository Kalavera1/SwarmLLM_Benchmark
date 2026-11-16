# Steckbrief: Altlauf GLM-5.3-Flash auf 1× B300 (01.10.2026)

**Messreihe v0** – vor diesem Repo, mit eigenen Skripten (`bench.py`, `bench2.py`). Die Zahlen sind als Referenz gedacht, nicht 1:1 mit Messreihe v1 (Testsuite `bench/`, ab Phase 4) vergleichbar: andere Prompts, andere Laststufen, keine Zielwerte, Zugriff über den RunPod-HTTP-Proxy.

## Herkunft

| | |
|---|---|
| Quelle | Repo `Kalavera1/benchmark_GLM53_runpod`, Commit `bc662dce912dc60fb082f790e1682d95ba1713d2` (01.10.2026) |
| Übernommen | Bericht (PDF, HTML, Plots), Rohdaten (`ergebnisse/`), Doku (`README.md`, `INSTALLATION.md`, `docs/`, `runpod/`) – unverändert |
| Nicht übernommen | `scripts/` – Projektregel 1: kein Code aus anderen Projekten. Verweise auf `scripts/` in der Original-Doku zeigen deshalb ins Leere; der Code liegt im Quell-Repo beim genannten Commit |

## Aufbau des Laufs (soweit festgehalten, Regel 6)

| Feld | Wert | Lücke |
|---|---|---|
| Datum | 01.10.2026 | |
| Hardware | 1× NVIDIA B300 (288 GB), 32 vCPU Intel Xeon 6767P, 251 GB RAM, RunPod | Secure/Community und On-Demand/Spot nicht festgehalten |
| Preis | 7,96 $/h laut RunPod | |
| Image | `vllm/vllm-openai:nightly` (vLLM 0.30.1rc1) | **kein Digest** festgehalten |
| Checkpoint | `nvidia/GLM-5.3-Flash-NVFP4` | **keine Revision** festgehalten |
| Startparameter | siehe [`runpod/template.md`](runpod/template.md): FP8-KV-Cache, 1M Kontext, `--max-num-seqs 4` | |
| Zugriff | RunPod-HTTP-Proxy (trennt stille Verbindungen nach ca. 2 Min.) | |

Wegen der fehlenden Pins ist der Lauf **nicht exakt reproduzierbar**.

## Ergebnisse in Kürze

Aus [`docs/erkenntnisse.md`](docs/erkenntnisse.md):

| Bereich | Ergebnis |
|---|---|
| Tempo, 1 Nutzer | 143 tok/s, erstes Token nach 0,3–0,5 s |
| Last | 4 Nutzer: 419 tok/s gesamt; ab 8 Nutzern Warteschlange (Grenze `--max-num-seqs 4`) |
| Kontext | 950k Token: Nadel gefunden, 37,5 s Einlesen (≈ 3,9 s je 100k) |
| Kontext unter Last | 4 × 120k gleichzeitig: alle Treffer, 11,7 s; ein 500k-Prompt drückt parallele Chats auf ≈ 30 % Tempo |
| ABAP | 5 von 7 gut bis sehr gut; RAP lückenhaft, AMDP mangelhaft |
| Tool-Calls | 10/10 |

Bericht mit Plots: [`bericht/bericht-glm-b300-20261001.pdf`](bericht/bericht-glm-b300-20261001.pdf). Alle ABAP-Antworten mit Denkprozess: [`ergebnisse/`](ergebnisse/).

## Was daraus in dieses Projekt eingeflossen ist

Die Lehren stehen in [`../../docs/erfahrungen.md`](../../docs/erfahrungen.md) (eigener User-Agent, Aufwärmrunde, Denk-Tokens getrennt erfassen, kein HTTP-Proxy für lange Prompts, Pod-Check auf Modellname und Key-Schutz).
