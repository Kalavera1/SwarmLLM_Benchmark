# Erkenntnisse aus dem Test am 01.10.2026

Messwerte und Plots: [`../bericht/bericht-glm-b300-20261001.pdf`](../bericht/bericht-glm-b300-20261001.pdf).
Hier stehen die Lehren, die man beim nächsten Mal wissen muss.

## Ergebnisse in Kürze

| Bereich | Ergebnis |
|---|---|
| Tempo, 1 Nutzer | 143 tok/s, erstes Wort nach 0,3–0,5 s |
| Last | 4 Nutzer: 419 tok/s gesamt, >110 tok/s je Nutzer. Ab 8 Nutzern Warteschlange (Grenze `--max-num-seqs 4`) |
| Kontext | 950k Token: versteckte Zahl gefunden, 37,5 s Einlesen, linear ~3,9 s je 100k Token |
| Kontext unter Last | 4 × 120k gleichzeitig: alle Treffer, 11,7 s. Ein 500k-Prompt drückt parallele Chats auf ~30 % Tempo |
| ABAP | 5 von 7 gut bis sehr gut (ALV, Modernisierung, SQL, CDS, Fehlersuche). RAP lückenhaft, AMDP mangelhaft |
| Tool-Calls | 10/10 |

## Betrieb: Was schiefgehen kann

| Befund | Wirkung | Abhilfe |
|---|---|---|
| **Denktiefe-Voreinstellung** denkt bei Code sehr lange | ABAP 11–23k Token, 2–4 Min. pro Antwort. Bei 8k Token Limit gar keine Antwort | In OpenWebUI `reasoning_effort=high`, Max Tokens ≥ 32k. Achtung: `high` ist schneller, aber weniger sorgfältig |
| **RunPod-Proxy kappt stille Verbindungen** nach ~2 Min. | Anfragen in der Warteschlange kommen leer zurück (2 von 7) | höheres `--max-num-seqs`, z. B. 16 (nicht getestet) |
| Großer Prompt bremst andere | Tempo paralleler Chats fällt beim Einlesen auf ~30 % | Für Familiengebrauch akzeptabel |
| JIT-Kompilierung im Betrieb | erste Anfragen gelegentlich langsamer (einmal 48 statt 142 tok/s) | nach dem Start eine Aufwärmrunde schicken |
| Proxy blockt User-Agent `Python-urllib` (403) | eigene Python-Skripte scheitern, OpenWebUI nicht betroffen | eigenen User-Agent senden (in `scripts/bench.py` umgesetzt) |

## Einrichtung: Stolpersteine vom ersten Versuch

1. **PyTorch-Template statt vLLM-Image.** vLLM von Hand zu installieren scheiterte an den Versionen von
   CUDA und PyTorch. Richtig ist `vllm/vllm-openai:nightly`.
2. **Leerzeichen im Image-Namen.** RunPod meldet dann nur „invalid repo“.
3. **Port 8000 nicht freigegeben.** Von außen kam dann nur `404`.
4. **Start Command nicht gespeichert.** vLLM startete still mit seinem Standardmodell `Qwen/Qwen3-0.6B`, und
   ohne `VLLM_API_KEY` war der Endpunkt offen. Aufgefallen ist das erst durch `scripts/test-endpunkt.sh`.
5. **Edit Pod setzt den Pod zurück.** Die Container Disk wird gelöscht, die 191 GB werden neu geladen.
   Deshalb vorher alles im Template richtig setzen.
6. **Lange Stille im Log ist normal.** Download, JIT-Kompilierung (145 s) und Autotuning schreiben kaum etwas.
   Den Fortschritt zeigen `du -sh /root/.cache/huggingface` und `nvidia-smi`.
7. `HF_HUB_ENABLE_HF_TRANSFER=1` ist veraltet und erzeugt nur eine Warnung. Es kann weg.

## ABAP im Detail

Alle Antworten mit vollständigem Denkprozess liegen in
[`../ergebnisse/ergebnisse-20261001-185839/`](../ergebnisse/ergebnisse-20261001-185839/). Bewertet durch Lesen,
**nicht kompiliert**.

| Aufgabe | Urteil | Hauptpunkt |
|---|---|---|
| ALV-Report (SALV) | sehr gut | JOIN, Summenzeile, Referenzfelder, Fehlerbehandlung |
| Modernisierung | sehr gut | VALUE/FOR, String-Templates, `ASSIGN lt[ 1 ]`, Verhalten begründet gleich |
| ABAP-SQL | gut | fügt einen nicht verlangten Filter `auart = 'TA'` aktiv ein |
| CDS View Entity | gut | berechneter Betrag als `abap.dec` statt `abap.curr` |
| Fehlersuche | gut, unvollständig | Analyse stark, die verlangte korrigierte Fassung fehlt |
| RAP mit Draft | Skizze | Draft-Actions fehlen (Pflicht unter `strict(2)`), `numbering` falsch platziert |
| AMDP | mangelhaft | Voreinstellung: über 32k Token festgedacht. `high`: `"`-Kommentar in SQLScript, kein Mandantenfilter |

Empfehlung: ABAP-Code von GLM vor dem Einsatz über den Syntax-Check in ADT laufen lassen.

Hinweis zu `ergebnisse/ergebnisse-20261001-185340/abap-*.md`: Das ist der erste Lauf mit 8000-Token-Limit.
Die Antworten sind **absichtlich leer**, weil das ganze Budget fürs Denken draufging. Sie sind der Beleg für das
Problem mit der Denktiefe.
