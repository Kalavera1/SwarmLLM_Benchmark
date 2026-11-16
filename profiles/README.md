# Modellprofile

Ein Ordner pro Modell mit `profile.env`. Das Profil ist die einzige Stelle, an der ein Modell beschrieben wird: Die Testsuite liest Fähigkeiten und Kontext, die Startskripte Image, Revision und Startparameter.

| Profil | Modell | Status |
|---|---|---|
| `mock` | Mock-Server, keine GPU | Selbsttest der Testsuite |
| `qwen38-27b` | Qwen3.8-27B, NVFP4, Data-Parallel 2 | bereit (nach Pinnen) |
| `qwen38-flash-next-fp8` | Qwen3.8-Flash-Next, FP8, N-gram-Tabelle im RAM | bereit (nach Pinnen) |
| `glm53-flash-fp4` | GLM-5.3-Flash, NVIDIA FP4-Local | bereit (nach Pinnen) |
| `deepseek-v41-flash` | DeepSeek V4.1 Flash | **Entwurf** – Weg offen |

## Pinnen (Regel 4)

Profile nennen nur die Quelle (`MODEL_QUELLE`, `VLLM_IMAGE_QUELLE`). Gestartet wird erst nach dem Pinnen – auf dem Steuerrechner, braucht nur Internet (den Image-Digest holt `pin.py` direkt von der Registry, Docker ist nicht nötig):

```bash
python3 profiles/pin.py qwen38-27b --trocken   # zeigt nur an, was eingetragen würde
python3 profiles/pin.py qwen38-27b        # trägt MODEL_ID, MODEL_REVISION, MODELL_GROESSE_GB, VLLM_IMAGE ein
git diff profiles/                        # prüfen, dann committen und als Pull Request einreichen
```

Die CI erzwingt, dass `MODEL_ID` nie ohne vollen 40-stelligen `MODEL_REVISION` im Repo steht.

## Felder

| Feld | Bedeutung |
|---|---|
| `PROFIL_STATUS` | `bereit` oder `entwurf` (Entwürfe starten nicht) |
| `MODEL_QUELLE`, `VLLM_IMAGE_QUELLE` | Hugging-Face-Repo und Image-Tag vor dem Pinnen |
| `MODEL_ID`, `MODEL_REVISION`, `VLLM_IMAGE` | gepinnt, von `pin.py` gesetzt |
| `SERVED_NAME`, `MAX_MODEL_LEN` | Name und Kontext am Server |
| `SERVE_ARGS` | vLLM-Argumente, durch Leerzeichen getrennt, **ohne JSON** |
| `SPEC_CONFIG` | JSON für `--speculative-config` (MTP); leer = aus |
| `SERVE_ENV` | Umgebungsvariablen `NAME=WERT`, durch Leerzeichen getrennt |
| `KV_CPU_OFFLOAD_GB` | Prefix-/KV-Cache zusätzlich im RAM (`--kv-offloading-size`); leer = aus. Flag-Name in Phase 4 gegen das gepinnte Image prüfen |
| `VISION`, `DENKSTUFEN`, `SLO_*` | für die Testsuite (siehe `bench/README.md`) |
| `GPU_ANZAHL`, `DISK_GB`, `HOST_RAM_MIN_GB`, `HOST_CPU_MUSTER`, `P2P_PFLICHT` | Anforderungen an den Host; der Pod-Check prüft sie |

Prefix-Caching ist in allen Profilen an (setzt das Startskript immer).

**Varianten** (z. B. MTP aus, KV-Cache FP8, Expert-Parallel) als eigener Ordner anlegen, z. B. `glm53-flash-fp4-ohne-mtp/`, damit jede Messung eindeutig einem Profil zugeordnet ist.
