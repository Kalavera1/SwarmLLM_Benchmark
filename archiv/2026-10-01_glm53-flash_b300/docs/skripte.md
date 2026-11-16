# Skripte

Alle Skripte liegen im Hauptordner und laufen auf dem Rechner mit OpenWebUI. Sie brauchen nur
`bash`, `curl`, `python3` (Standardbibliothek) und für den Bericht Docker.

**API-Key:** Jedes Skript liest den Key aus der Umgebungsvariable `VLLM_API_KEY` oder, falls die fehlt, aus
`api-key.txt` im selben Ordner. Die Datei ist per `.gitignore` ausgeschlossen. Die Skripte geben den Key nie
aus. Fehlt er, brechen sie mit einem Hinweis ab.

**Pod-Adresse:** Überall reicht die Pod-ID (z. B. `abc123xyz456`). Daraus wird
`https://<POD-ID>-8000.proxy.runpod.net`. Alternativ geht eine volle URL ohne `/v1`.

---

## `scripts/test-endpunkt.sh <POD-ID>`

Schneller Funktionstest, ~10 s. Prüft:

1. Modellliste: Welches Modell ist geladen, mit welchem Kontext?
2. Anfrage **ohne** Key muss `401` liefern. Sonst steht `WARNUNG`, und der Endpunkt ist offen.
3. Eine Chat-Antwort.
4. Ein Tool-Call (`wetter {"ort": "Berlin"}`), Voraussetzung für Agenten und Terminal in OpenWebUI.

Anderer Modellname: `MODELL=glm-5.3 ./scripts/test-endpunkt.sh <POD-ID>`.

## `scripts/openwebui-verbinden.sh <POD-ID>` / `scripts/openwebui-verbinden.sh --aus`

Trägt den Endpunkt als OpenAI-Verbindung in OpenWebUI ein oder schaltet alle OpenAI-Verbindungen wieder ab.

- Sichert vorher `webui.db` samt `-wal`/`-shm` als `.bak-<STAMP>` im Datenordner von OpenWebUI.
- Schreibt direkt in die Tabelle `config` (Schlüssel `openai.*`) und startet OpenWebUI neu, ~30 s Ausfall.
  OpenWebUI liest diese Werte nur beim Start.
- Das Modell sehen danach **nur Admins**: Modelle ohne eigenen Eintrag in der Tabelle `model` blendet OpenWebUI
  für normale Nutzer aus (`utils/models.py`, `get_filtered_models`).
- **Achtung:** `--aus` leert *alle* OpenAI-Verbindungen. Bei uns gab es außer RunPod keine. Wer weitere hat,
  trägt sie danach in der Oberfläche wieder ein.

Für ein anderes Setup anpassbar:

| Variable | Standard | Bedeutung |
|---|---|---|
| `OWUI_CONTAINER` | `openwebui` | Container- und Compose-Dienstname |
| `OWUI_COMPOSE_DIR` | `$HOME/docker/localAI` | Ordner mit der `docker-compose.yml` |
| `OWUI_DB` | `/app/backend/data/webui.db` | DB-Pfad im Container |
| `OWUI_URL` | `http://localhost:8081` | für den Gesundheitscheck nach dem Neustart |

## `scripts/bench.py <POD-ID> [--kontext N] [--nur tempo|parallel|tools|kontext] [--modell NAME]`

Basis-Benchmark, ~5 Min. (mit `--kontext 1048576` länger).

- **tempo**: 3 Aufgaben mit je 1500 Token. Gemessen werden die Zeit bis zum ersten Token und Token/s.
- **parallel**: 2 und 4 gleichzeitige Nutzer, Gesamtdurchsatz.
- **tools**: 10 Tool-Calls, Trefferquote.
- **kontext**: versteckte Zahl in 32k / 128k / 256k / 512k / 1M Token (bis `--kontext`).

Funktioniert auch gegen Ollama, z. B. `./scripts/bench.py http://<ollama-host> --modell qwen3.5:9b --kontext 0`.
Ergebnis: `ergebnisse/bench-<STAMP>.json`.

## `scripts/bench2.py <POD-ID> [--nur last|kontext|abap|denken]`

Ausführlicher Belastungstest, ~15–20 Min.

- **last**: 1 / 2 / 4 / 8 / 16 Nutzer gleichzeitig. Zeit bis zum ersten Wort (Median und langsamste 5 %),
  Token/s je Anfrage, Gesamtdurchsatz.
- **kontext**: 4 × 120k gleichzeitig; 500k-Auftrag neben 3 normalen Chats; zweite Frage zum selben Dokument
  (Prefix-Cache).
- **abap**: 7 ABAP-Aufgaben gleichzeitig, Limit 32k Token. Die Antworten werden als Markdown gespeichert, inklusive Denkprozess.
- **denken**: dieselbe Rechenaufgabe mit `reasoning_effort` low / high / max.

Ergebnis: `ergebnisse/ergebnisse-<STAMP>/` mit `ergebnis.json` und `abap-*.md`.

Tipp: Bei `--max-num-seqs 4` und 7 ABAP-Aufgaben stehen 3 in der Warteschlange und werden nach ~2 Min. vom
RunPod-Proxy getrennt. Ein höherer Wert für `--max-num-seqs` sollte das verhindern (nicht getestet).

## `scripts/pdf-bericht.py`

Baut aus den Messdaten den PDF-Bericht mit Plots (`bericht/`). Braucht matplotlib und reportlab, deshalb
läuft es in einem Wegwerf-Container:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.11-slim \
  sh -c "pip install -q matplotlib reportlab && python scripts/pdf-bericht.py"
docker run --rm -v "$PWD":/app alpine chown -R "$(id -u):$(id -g)" /app
```

Die Namen der Messdateien stehen oben im Skript (`B1`, `B2`, `B3`). Für einen neuen Lauf dort anpassen.
Drei ABAP-Wiederholungen vom 01.10. sind als Konstante `ABAP_NACH` eingetragen, weil sie nur im Terminal
protokolliert wurden.
