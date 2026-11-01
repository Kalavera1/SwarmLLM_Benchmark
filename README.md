# SwarmLLM_Benchmark

Privates Testprojekt: große Open-Weight-Modelle mit vLLM auf **gemieteten 2× NVIDIA RTX PRO 6000 Blackwell** (je 96 GB, SM120, kein NVLink) betreiben, vergleichen und vermessen – mit **LiteLLM** als Gateway und **OpenWebUI** als Frontend.

## Ziel

- **Kontext:** mindestens 500.000, möglichst 1.000.000 Tokens pro Anfrage
- **Realistische Last:** ca. 30 Nutzer, davon ca. 4 mit Vibe Coding (lange, wachsende Kontexte), der Rest Chat über OpenWebUI
- **Kosten minimal:** GPU-Instanz läuft nur für Messläufe und wird danach sofort gelöscht

## Regeln

1. **Strikt getrennt vom beruflichen Stack.** Kein Code, keine Configs, keine Zugangsdaten, keine Actions-Runner von dort. Nur der private GitHub-Account.
2. **Keine Secrets im Repo.** Zugangsdaten für Skripte nur in `.env` (steht in `.gitignore`, Vorlage: `.env.example`). Zugangsdaten für den lokalen Stack als Docker Secrets.
3. **Keine Gewichte, Caches oder Container-Layer im Repo.**
4. **Alles gepinnt.** Container-Images per Digest (`@sha256:…`), Checkpoints per Revision (Commit-Hash). Nie wandernde Tags wie `latest` oder `-beta`.
5. **Kein GPU-Lauf ohne Auto-Stopp.** Jeder Pod bekommt einen Watchdog, damit keiner vergessen wird.
6. **Ergebnisse sind nachvollziehbar.** Jede Messung speichert Datum, Image-Digest, Checkpoint-Revision, Startparameter und Hardware.
7. **Schrittweise.** Jede Phase endet mit einem Review, bevor die nächste beginnt (siehe [Roadmap](docs/roadmap.md)).
8. **Nie ein offener Endpunkt.** vLLM läuft immer mit `VLLM_API_KEY`. Jeder Pod-Check prüft, dass eine Anfrage ohne Key abgewiesen wird.

## Architektur

```
 Lokal (WSL, Docker Swarm)               RunPod (nur während Messläufen)
┌──────────────────────────┐            ┌──────────────────────────────────┐
│ OpenWebUI                │            │ Pod: 2× RTX PRO 6000             │
│     │                    │ SSH-Tunnel │                                  │
│     ▼                    │ / TCP-Port │  vLLM-Image direkt als Pod-Image │
│ LiteLLM (Gateway, Keys) ─┼───────────►│  (OpenAI-API, mit API-Key)       │
│                          │            │                                  │
│ Benchmark-Skripte ───────┼───────────►│  Gewichte + Caches auf           │
└──────────────────────────┘            │  Network Volume                  │
                                        └──────────────────────────────────┘
```

- **Warum das vLLM-Image direkt als Pod-Image?** In RunPod-Pods ist kein eigenes Docker und kein Docker Compose möglich. Konfiguration läuft über Umgebungsvariablen und das Startkommando.
- **Warum LiteLLM und OpenWebUI lokal?** Sie brauchen keine GPU, und die vLLM-API ist ohne Authentifizierung – LiteLLM kommt als abgesichertes Gateway davor.
- **Warum nicht über den RunPod-HTTP-Proxy?** Er trennt stille Verbindungen nach ca. 2 Minuten. Ein kalter 1M-Prompt dauert auf dieser Hardware länger (siehe [Erfahrungen](docs/erfahrungen.md)).
- **Warum Docker Swarm?** Native Secrets, Healthchecks mit automatischem Neustart und ein Stack-File, das später auf weitere Nodes wachsen kann. Swarm umfasst nur die lokale Seite: Der RunPod-Pod kann kein Swarm-Node werden (kein Docker im Pod, kein UDP).

## Modell-Kandidaten

| Modell | Runtime | Checkpoint | Status |
|---|---|---|---|
| DeepSeek V4 Flash | Karmic Kraken (`ghcr.io/local-inference-lab/vllm`), per Digest gepinnt | wird in Phase 4 festgelegt | geplant |
| GLM-5.3-Flash | Runtime von T.J. Purtell (`tpurtell/glm-5.3-flash-ext3-2x-rtx`), Profil `k3` | EXL3 K3, Revision wird in Phase 6 gepinnt | geplant |
| Qwen3.8-Flash-Next | offen | `nvidia/Qwen3.8-Flash-Next-FP4-Local` | später |

Warum diese Auswahl: siehe [Entscheidungslog](docs/entscheidungen.md).

## Lizenzen beachten

- **DFlash2-Drafter** (`incoai/GLM-5.3-Flash-DFlash2`): CC BY-NC-ND 4.0, nur Forschung und Evaluation. Für diese Tests in Ordnung, für produktiven Einsatz nur mit Lizenz von Inco AI. Deshalb wird GLM zusätzlich ohne Drafter bzw. im MTP-Modus gemessen.
- **GLM-EXL3-Checkpoint:** Lizenz auf der Model Card vor dem Download prüfen (Phase 6).
- **Karmic Kraken:** Community-Projekt, als Pre-Release markiert.

## Struktur

Ordner entstehen erst in der Phase, in der sie gebraucht werden.

```
.
├── README.md
├── .env.example        Vorlage für Zugangsdaten (echte Werte nur in .env)
├── docs/
│   ├── roadmap.md      Phasen, Ergebnisse, Review-Kriterien
│   ├── entscheidungen.md
│   └── erfahrungen.md  Lehren aus früheren Tests
├── local/              Phase 1: Swarm-Stack mit LiteLLM + OpenWebUI
├── bench/              Phase 2: Benchmark-Skripte
├── runpod/             Phase 3–4: Pod anlegen, prüfen, löschen
├── profiles/           Phase 4+: ein Ordner pro Modell
└── results/            Messergebnisse (JSON + Zusammenfassung)
```
