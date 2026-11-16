# Modellwahl: welches GLM auf wie vielen Karten

Stand 01.10.2026. Eine B300 hat 288 GB Grafikspeicher (≈ 268 GiB nutzbar, `nvidia-smi` zeigt 275.040 MiB).
Entscheidend ist, ob die Gewichte plus der Kontextspeicher (KV-Cache) hineinpassen.

## Übersicht

| Modell | Parameter | Gewichte | Karten | Status |
|---|---|---|---|---|
| **GLM-5.3-Flash NVFP4** (`nvidia/GLM-5.3-Flash-NVFP4`) | 321 Mrd., 18 Mrd. aktiv | ~183 GB | **1× B300** | **getestet**, 1M Kontext passt (9,35 Mio. Token KV) |
| GLM-5.3-Flash FP8 (`zai-org/GLM-5.3-Flash`, offiziell) | 321 Mrd., 18 Mrd. aktiv | ~306 GiB | 2× B300 | nicht getestet; hat MTP für spekulatives Decoding |
| GLM-5.3 FP8 (`zai-org/GLM-5.3`, offiziell) | 743 Mrd., 39 Mrd. aktiv | ~750 GB | 4× B300 | nicht getestet |
| GLM-5.3 NVFP4 (`Inferact/GLM-5.3-NVFP4`, Community) | 743 Mrd. | ~465 GB | 2× B300 | nicht getestet, sehr knapp (~60 GiB KV) |

Getestet ist nur die erste Zeile. Ihre Einstellungen stehen in [`../runpod/template.md`](../runpod/template.md).
Die Startbefehle für die übrigen Varianten stehen unten unter „Nicht getestete Startbefehle“.

## Warum NVFP4 auf einer Karte

- **NVFP4** ist das 4-Bit-Format, das Blackwell-Karten (B200/B300) in Hardware rechnen. Nur die
  Experten-Gewichte (97 % der Parameter) sind 4-Bit, der Rest bleibt BF16. Laut den Herausgebern geht dabei kaum
  Qualität verloren. Einen Qualitätsvergleich mit FP8 haben wir nicht gemacht.
- Den Beleg, dass es auf eine Karte passt, liefert das Rezept
  [J-M-Recipes/gb300-glm-flash-recipe](https://github.com/J-M-Recipes/gb300-glm-flash-recipe)
  (DGX Station GB300, gleicher Chip sm103). **Nicht** übertragbar sind dessen Grace-spezifische Teile
  (CDMM, Offload über NVLink-C2C, ARM64-Image) und die DFlash2-Spekulation (SGLang statt vLLM).
- GLM-5.3-Flash nutzt hybride Linear-/Sparse-Attention. Der Kontextspeicher pro Token ist dadurch sehr klein: In
  58 GiB passen 9,35 Mio. Token.

## Hinweise zu den offiziellen Rezepten

- Das vLLM-Rezept (<https://recipes.vllm.ai/zai-org/GLM-5.3-Flash>, `?hardware=b300`) zeigt **8 Karten** mit TP8.
  Das ist auf Durchsatz für viele Nutzer ausgelegt, nicht die Untergrenze.
- `--kv-transfer-config … LMCacheMPConnector` aus dem Rezept haben wir **weggelassen**: Dafür muss ein eigener
  LMCache-Server auf Port 5555 laufen, sonst startet vLLM nicht. Für wenige Nutzer bringt er nichts.
- `--privileged --ipc=host` aus dem `docker run`-Beispiel lassen sich auf RunPod nicht setzen und sind dort
  auch nicht nötig.
- vLLM muss neu genug sein (≥ 0.29, getestet 0.30.1rc1 nightly). Ältere Versionen kennen
  `Glm5NextForConditionalGeneration` nicht.

## Wie man auf 800 Token/s kommt

Gemessen: 143 tok/s für einen Nutzer, ~425 tok/s gesamt. Die Grenze kam von `--max-num-seqs 4`, nicht von der Karte.

- **Gesamtdurchsatz ≥ 800 tok/s ist plausibel:** `--max-num-seqs 16` und 8+ gleichzeitige Nutzer.
  Das GB300-Rezept erreicht auf demselben Chip 825 tok/s bei 8 Nutzern, allerdings mit SGLang und
  spekulativem Decoding. Mit vLLM **noch nicht gemessen**.
- **Für einen einzelnen Nutzer nicht realistisch:** Mit spekulativem Decoding (MTP beim FP8-Modell, DFlash
  bei SGLang) sind vielleicht 230–250 tok/s drin.

## Nicht getestete Startbefehle

> **Keiner dieser Befehle ist ausprobiert.** Sie sind aus den offiziellen Rezepten und der Speicherrechnung
> abgeleitet. Vor dem Einsatz mit `scripts/test-endpunkt.sh` prüfen. Pod-Einstellungen sonst wie in
> [`../runpod/template.md`](../runpod/template.md), nur mit mehr GPUs und mehr Container Disk.

**1× B300, wie getestet, aber 16 statt 4 gleichzeitige Anfragen.** Gegen die Warteschlange, der Speicher reicht
rechnerisch:
```
nvidia/GLM-5.3-Flash-NVFP4 --served-model-name glm-5.3-flash --host 0.0.0.0 --port 8000 --tensor-parallel-size 1 --kv-cache-dtype fp8 --max-model-len 1048576 --max-num-seqs 16 --gpu-memory-utilization 0.92 --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm47
```

**2× B300, offizielles FP8 mit MTP** (Container Disk ≥ 400 GB):
```
zai-org/GLM-5.3-Flash --served-model-name glm-5.3-flash --host 0.0.0.0 --port 8000 --tensor-parallel-size 2 --kv-cache-dtype fp8 --max-model-len 1048576 --max-num-seqs 16 --gpu-memory-utilization 0.92 --speculative-config.method mtp --speculative-config.num_speculative_tokens 5 --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm47
```

**Volles GLM-5.3, 4× B300, FP8** (Container Disk ≥ 900 GB; Test mit `MODELL=glm-5.3 ./scripts/test-endpunkt.sh`):
```
zai-org/GLM-5.3 --served-model-name glm-5.3 --host 0.0.0.0 --port 8000 --tensor-parallel-size 4 --kv-cache-dtype fp8 --max-model-len 131072 --max-num-seqs 16 --gpu-memory-utilization 0.92 --speculative-config.method mtp --speculative-config.num_speculative_tokens 5 --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm47
```

**Network Volume** gegen den erneuten Download der 191 GB bei jedem neuen Pod: in RunPod unter Storage anlegen,
beim Deploy auswählen, Umgebungsvariable `HF_HOME=/workspace/hf` setzen. Ebenfalls nicht getestet.
