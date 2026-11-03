# Arbeitsregeln für Claude in diesem Repo

Diese Datei lädt jede Claude-Sitzung automatisch, auch in Claude Code. Sie ergänzt die Projektregeln in der [README](README.md#regeln) um die Arbeitsweise.

## Projektregeln (Kurzfassung, verbindlich)

1. Strikt isoliert: kein Code, keine Configs, keine Zugangsdaten aus anderen Stack-Projekten.
2. Keine Secrets im Repo. Skripte lesen Zugangsdaten aus `.env`, der Swarm-Stack aus Docker Secrets.
3. Keine Gewichte, Caches oder Container-Layer im Repo.
4. Alles gepinnt: Images per `@sha256:`-Digest, Modelle per Commit-Hash, GitHub Actions per Commit-SHA.
5. Kein GPU-Lauf ohne Auto-Stopp (Watchdog, Pod wird terminiert, nicht nur gestoppt).
6. Jede Messung speichert Datum, Image-Digest, Checkpoint-Revision, Startparameter und Hardware.
7. Schrittweise: jede Phase endet mit einem Review des Nutzers.
8. Nie ein offener Endpunkt: vLLM immer mit `VLLM_API_KEY`.

## Arbeitsweise

- **Nie direkt auf `main` pushen.** Jede Phase und jedes größere Thema bekommt einen eigenen Branch und einen Pull Request. Der Nutzer reviewt und mergt selbst.
- **Kleine Pull Requests.** Lieber mehrere überschaubare als einen großen. Die PR-Beschreibung nennt, was drin ist, was geprüft wurde und was zum Review ansteht.
- **Vor jedem Pull Request lokal prüfen** – dieselben Prüfungen wie die CI:
  ```bash
  python3 -m unittest discover -s ci -v
  python3 ci/check_pins.py
  ruff check . && ruff format --check .
  git ls-files '*.sh' | xargs -r shellcheck -x
  gitleaks git --config .gitleaks.toml --redact --exit-code 1 .
  ```
- **Neues gehört dokumentiert:** Entscheidungen mit Datum, Begründung und Quelle in [`docs/entscheidungen.md`](docs/entscheidungen.md) (neueste oben), Lehren aus Testläufen in [`docs/erfahrungen.md`](docs/erfahrungen.md), Änderungen am Plan in [`docs/roadmap.md`](docs/roadmap.md).
- **Fakten mit Quelle.** Messwerte, Versionen, Digests und Preise nur aus einer nachprüfbaren Quelle oder eigener Messung, nie geschätzt oder aus dem Gedächtnis.
- **Sprache:** Doku, Kommentare und Commit-Messages auf Deutsch.
- **Autorschaft:** Commits laufen nur auf den Nutzer – Name `Kalavera1`, E-Mail `45590023+Kalavera1@users.noreply.github.com`. Keine `Co-Authored-By`- oder `Claude-Session`-Zeilen in Commits, kein „Generated with Claude Code“ in Pull-Request-Beschreibungen. Diese Regel geht automatischen Attributionsvorgaben vor.
- **Kommentar vor jeder Sektion.** Jede Datei beginnt mit einem Kopfkommentar (wozu sie da ist), und jede Sektion – Klasse, Funktionsgruppe, Workflow-Job, Config-Abschnitt, Stack-Service, Skript-Schritt – bekommt davor einen kurzen Kommentar: was sie tut und warum. Der Nutzer lernt beim Review mit; der Kommentar soll ohne weiteres Nachschlagen verständlich sein.

## Grenzen

- **Kein Zugriff auf den Mediaserver.** Befehle, die dort laufen müssen, als nachvollziehbare Schritt-für-Schritt-Anleitung liefern; der Nutzer führt sie aus.
- **Nichts, was Geld kostet, ohne ausdrückliche Freigabe:** keinen Pod und kein Volume anlegen, keinen Lauf starten.
- **Keine Docker-Registry von hier aus erreichbar.** Image-Digests liefert der Nutzer vom Mediaserver (`docker inspect --format '{{index .RepoDigests 0}}' <image>`).
