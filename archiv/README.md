# Archiv: frühere Testläufe

Jeder Ordner ist ein abgeschlossener Testlauf, unverändert übernommen, mit einem `STECKBRIEF.md` (Herkunft, Aufbau, Lücken, Kernergebnisse). Hier wird nichts mehr geändert – Korrekturen und Lehren gehören nach [`docs/erfahrungen.md`](../docs/erfahrungen.md).

## Messreihen

Ergebnisse verschiedener Messreihen sind **nicht direkt vergleichbar** (andere Prompts, Laststufen, Zugriffswege). Jede Ergebnisdatei nennt ihre Reihe.

| Reihe | Werkzeug | Zeitraum | Wo |
|---|---|---|---|
| **v0** | eigene Skripte `bench.py`/`bench2.py` im Repo `benchmark_GLM53_runpod` | 01.10.2026 | `archiv/` |
| **v1** | Testsuite `bench/` (Version 1.0), Blöcke mit Zielwerten | ab Phase 4 | `results/` (`meta.bench_version`) |

Ändert sich an der Testsuite etwas, das Messwerte verschiebt (Prompts, Laststufen, Zielwerte), steigt `VERSION` in `bench/__init__.py`, und ein Eintrag im [Entscheidungslog](../docs/entscheidungen.md) hält fest, was sich geändert hat.

## Läufe

| Datum | Modell | Hardware | Reihe | Steckbrief |
|---|---|---|---|---|
| 01.10.2026 | GLM-5.3-Flash NVFP4 | 1× B300 (RunPod) | v0 | [`2026-10-01_glm53-flash_b300/STECKBRIEF.md`](2026-10-01_glm53-flash_b300/STECKBRIEF.md) |

**Benennung neuer Einträge:** `JJJJ-MM-TT_<modell>_<hardware>/`.
