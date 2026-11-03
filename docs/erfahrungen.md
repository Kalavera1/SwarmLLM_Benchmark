# Erfahrungen aus früheren Tests

Lehren aus Vorgänger-Projekten und aus dem Bau dieses Projekts, damit wir dieselben Fehler nicht zweimal bezahlen. Aus anderen Repos werden nur Erfahrungen übernommen, kein Code. Neueste Einträge oben.

---

## Bau von Phase 1 am 01.11.2026: LiteLLM v1.106.6 mit Mock

Lokal ohne Docker getestet: LiteLLM aus PyPI (gleiche Version wie das Image), Mock-Server und Smoke-Test.

| Befund | Konsequenz |
|---|---|
| **LiteLLM ohne Datenbank antwortet bei Abweisung nicht mit 401:** ohne Key 500 (Fehler im eigenen Exception-Handler), mit falschem Key 400 „No connected db“ | Abgewiesen wird trotzdem. Tests prüfen „keine 2xx-Antwort“ statt genau 401 |
| Ohne Datenbank gibt es nur den Master-Key, keine eigenen Keys pro Anwendung | Für die Tests ausreichend; eigene Keys erst mit Postgres |
| gitleaks meldet `curl -H "Authorization: Bearer ${VAR}"` als Fund, auch wenn nur eine Variable drinsteht | In Skripten `curl --oauth2-bearer "$VAR"` verwenden |
| shellcheck folgt `source`-Dateien nur mit `-x` | CI und lokale Prüfung laufen mit `shellcheck -x` |
| Swarm-Configs sind unveränderlich | `deploy.sh` hängt einen Inhalts-Hash an den Config-Namen |
| `mode: 0555` in der Stack-Datei wird korrekt als Oktalzahl gelesen (`docker stack config` zeigt 365 dezimal) | – |

---

## Test vom 01.10.2026: GLM-5.3-Flash auf 1× B300 (Repo `benchmark_GLM53_runpod`)

**Aufbau:** 1× NVIDIA B300 (288 GB) bei RunPod, 7,96 $/h. Image `vllm/vllm-openai:nightly` (vLLM 0.30.1rc1), Checkpoint `nvidia/GLM-5.3-Flash-NVFP4`, FP8-KV-Cache, 1M Kontext, `--max-num-seqs 4`. OpenWebUI direkt über den RunPod-HTTP-Proxy angebunden, ohne LiteLLM.

### Messwerte als Referenz

| Bereich | B300 (1 Karte) |
|---|---|
| Decode, 1 Nutzer | 143 tok/s, erstes Token nach 0,3–0,5 s |
| Decode, 4 Nutzer | 419 tok/s gesamt (Grenze war `--max-num-seqs 4`, nicht die Karte) |
| 950k-Prompt | Nadel gefunden, 37,5 s Einlesen (ca. 3,9 s je 100k Tokens) |
| 4 × 120k gleichzeitig | alle Treffer, 11,7 s |
| Tool-Calls | 10/10 |
| Kaltstart inkl. 191 GB Download | ca. 15 Min. |

**Vergleich zu unserem Ziel:** Für GLM-5.3-Flash auf 2× RTX PRO 6000 meldet das Purtell-Rezept 4.200–4.600 tok/s Prefill, also ca. 264–285 s für 1M Tokens. Die B300 liest einen Prompt dieser Größe rund 7× schneller ein, kostet aber etwa doppelt so viel pro Stunde. Diesen Vergleich nehmen wir in die Auswertung (Phase 7) auf.

### Betrieb: was schiefging

| Befund | Wirkung | Konsequenz für dieses Projekt |
|---|---|---|
| **RunPod-HTTP-Proxy trennt stille Verbindungen nach ca. 2 Min.** | Anfragen in der Warteschlange kamen leer zurück (2 von 7) | **Kritisch für lange Kontexte:** Ein kalter 1M-Prompt dauert auf 2× RTX PRO 6000 länger als 2 Min. Lange Prompts laufen deshalb über SSH-Tunnel oder direkt freigegebenen TCP-Port, nicht über den Proxy (Phase 4 prüfen) |
| Proxy blockt User-Agent `Python-urllib` (HTTP 403) | eigene Skripte scheitern | Benchmark-Skripte senden einen eigenen User-Agent (Phase 2) |
| Standard-Denktiefe denkt bei Code sehr lange | 11–23k Denk-Tokens, 2–4 Min. pro Antwort; bei 8k Token-Limit gar keine Antwort | Benchmarks setzen `max_tokens` ≥ 32k und erfassen Denk-Tokens getrennt; Denktiefe ist ein Testparameter |
| JIT-Kompilierung im laufenden Betrieb | erste Anfragen gelegentlich langsamer (einmal 48 statt 142 tok/s) | Nach dem Start eine Aufwärmrunde, die nicht mitgemessen wird |
| Großer Prompt bremst andere | parallele Chats fallen beim Einlesen eines 500k-Prompts auf ca. 30 % Tempo | Gehört in den Lastmix-Test (Phase 2) |

### Einrichtung: Stolpersteine

1. **vLLM nicht von Hand installieren.** In der PyTorch-Vorlage scheiterte es an CUDA-/PyTorch-Versionen. Fertiges Image direkt als Pod-Image nehmen – passt zu unserem Plan.
2. **Start Command nicht gespeichert:** vLLM startete still mit seinem Standardmodell `Qwen/Qwen3-0.6B`, und ohne `VLLM_API_KEY` war der Endpunkt offen im Internet. Der Pod-Check muss Modellname und Key-Schutz prüfen (Anfrage ohne Key → 401).
3. **Port nicht freigegeben:** von außen nur 404, obwohl vLLM lief.
4. **Leerzeichen im Image-Namen:** RunPod meldet nur „invalid repo“.
5. **„Edit Pod“ setzt den Pod zurück** und löscht die Container Disk – die Gewichte werden neu geladen. Alles vorher im Template festlegen; mit Network Volume entschärft sich das.
6. **Lange Stille im Log ist normal** (Download, JIT, Autotuning). Fortschritt zeigen `du -sh` auf den Cache-Ordner und `nvidia-smi`.
7. **`VLLM_ENGINE_READY_TIMEOUT_S=3600` setzen**, sonst bricht vLLM während Laden und Kompilieren ab.
8. **Terminieren, nicht nur stoppen.** Ein gestoppter Pod kostet für seine Disk weiter. Danach unter Billing kontrollieren.
9. `HF_HUB_ENABLE_HF_TRANSFER` ist veraltet und kann weg.

### Was damals offen blieb

- Network Volume gegen erneuten Download: nicht getestet → Phase 3
- `--max-num-seqs 16` gegen die Warteschlange: nicht getestet → Lastmix in Phase 5/6
- RunPod-Secrets für den API-Key: nicht getestet → Phase 4
